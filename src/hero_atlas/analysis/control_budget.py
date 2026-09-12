"""Orcamento de autoridade: quanta banda de atitude a arquitetura realmente entrega.

Ver ADR-004.

Este modulo existe por causa de um erro concreto. O primeiro laco fechado usou banda
de atitude de 6 rad/s, escolhida a olho, e falhou com ``wrench_unattainable`` a partir
de cinco graus de perturbacao, com o limite de rampa em **zero por cento**. Nao era o
atuador: era o controlador pedindo momento que a geometria nao produz.

Ganho escolhido a olho transforma limite de arquitetura em falha de sintonia, e as
duas exigem correcoes opostas. Aqui a banda e **derivada** da autoridade medida.

As duas margens do ADR-004, lado a lado:

**Margem estatica.** Maior momento puro disponivel com ``T`` livre em
``[T_min, T_max]``, ou seja o que seria atingivel se os motores fossem instantaneos.

**Margem dinamica no horizonte.** O mesmo, com ``T`` preso a caixa que a rampa permite
alcancar em ``Ha`` a partir do empuxo atual.

    T_i(t+Ha) em [ max(T_min, T_i - Tdot_desce*Ha) , min(T_max, T_i + Tdot_sobe*Ha) ]

⚠ **"Momento puro" e a parte que importa.** Nao basta somar momento: e preciso manter
forca e os outros dois momentos iguais aos do trim, senao o "momento disponivel"
inclui contribuicoes que derrubariam o veiculo em outro eixo. O problema e um programa
linear com igualdades nos cinco componentes que nao se quer mexer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import linprog

from ..airframe.geometry import PropulsionGeometry, allocation_matrix
from ..propulsion.actuator import ActuatorEnvelope

__all__ = [
    "MomentBudget",
    "pure_moment_available_Nm",
    "moment_budget",
    "achievable_bandwidth_rad_s",
]

_AXIS_NAMES = ("roll", "pitch", "yaw")


def pure_moment_available_Nm(
    geometry: PropulsionGeometry,
    *,
    axis: int,
    thrust_trim_N: ArrayLike,
    lower_N: ArrayLike,
    upper_N: ArrayLike,
) -> float:
    """Maior acrescimo de momento **puro** no eixo, a partir do trim.

    Puro significa: os outros cinco componentes do wrench ficam exatamente iguais aos
    do trim. Sem essa restricao o numero seria otimista e inutil, porque incluiria
    momento que vem junto de forca lateral ou de momento em outro eixo.

    Devolve zero quando o programa linear nao encontra solucao, o que significa que
    nem o proprio trim cabe na caixa dada.
    """
    if axis not in (0, 1, 2):
        raise ValueError(f"eixo deve ser 0, 1 ou 2, recebeu {axis!r}")

    W = allocation_matrix(geometry)
    T0 = np.asarray(thrust_trim_N, dtype=np.float64)
    lo = np.asarray(lower_N, dtype=np.float64)
    hi = np.asarray(upper_N, dtype=np.float64)
    if not (T0.shape == lo.shape == hi.shape == (W.shape[1],)):
        raise ValueError("empuxo de trim e limites precisam ter uma entrada por propulsor")

    linha = 3 + axis
    w_trim = W @ T0
    outros = [i for i in range(6) if i != linha]

    solucao = linprog(
        -W[linha, :],
        A_eq=W[outros, :],
        b_eq=w_trim[outros],
        bounds=list(zip(lo, hi, strict=True)),
        method="highs",
    )
    if not solucao.success:
        return 0.0
    return float(W[linha, :] @ solucao.x - w_trim[linha])


@dataclass(frozen=True, slots=True)
class MomentBudget:
    """As duas margens do ADR-004, por eixo, mais a razao entre elas."""

    static_Nm: NDArray[np.float64]
    horizon_Nm: NDArray[np.float64]
    horizon_s: float

    @property
    def shrinkage(self) -> NDArray[np.float64]:
        """Quantas vezes a margem dinamica e menor que a estatica, por eixo.

        ⚠ E este numero, e nao o empuxo maximo, que diz se a arquitetura consegue
        reagir. Um conjunto pode ter forca maxima excelente e autoridade de curto
        prazo miseravel, e a razao aqui expoe isso em uma linha.
        """
        return np.divide(
            self.static_Nm,
            np.maximum(self.horizon_Nm, 1e-12),
            out=np.full_like(self.static_Nm, np.inf),
            where=self.horizon_Nm > 1e-12,
        )

    def as_rows(self) -> tuple[tuple[str, float, float, float], ...]:
        return tuple(
            (nome, float(e), float(h), float(r))
            for nome, e, h, r in zip(
                _AXIS_NAMES, self.static_Nm, self.horizon_Nm, self.shrinkage, strict=True
            )
        )


def moment_budget(
    geometry: PropulsionGeometry,
    *,
    thrust_trim_N: ArrayLike,
    envelopes: tuple[ActuatorEnvelope, ...],
    horizon_s: float,
) -> MomentBudget:
    """Mede as duas margens nos tres eixos."""
    T0 = np.asarray(thrust_trim_N, dtype=np.float64)
    if len(envelopes) != T0.size:
        raise ValueError("um envelope por propulsor")
    if horizon_s <= 0.0:
        raise ValueError("horizonte precisa ser positivo")

    fisico_lo = np.array([e.thrust_min_N for e in envelopes])
    fisico_hi = np.array([e.thrust_max_N for e in envelopes])
    horizonte_lo = np.maximum(
        fisico_lo, T0 - np.array([e.rate_down_max_N_s for e in envelopes]) * horizon_s
    )
    horizonte_hi = np.minimum(
        fisico_hi, T0 + np.array([e.rate_up_max_N_s for e in envelopes]) * horizon_s
    )

    estatico = np.array(
        [
            pure_moment_available_Nm(
                geometry, axis=k, thrust_trim_N=T0, lower_N=fisico_lo, upper_N=fisico_hi
            )
            for k in range(3)
        ]
    )
    horizonte = np.array(
        [
            pure_moment_available_Nm(
                geometry, axis=k, thrust_trim_N=T0, lower_N=horizonte_lo, upper_N=horizonte_hi
            )
            for k in range(3)
        ]
    )
    return MomentBudget(static_Nm=estatico, horizon_Nm=horizonte, horizon_s=horizon_s)


def achievable_bandwidth_rad_s(
    budget: MomentBudget,
    *,
    inertia_kg_m2: ArrayLike,
    reference_error_rad: float,
    use_horizon: bool = True,
) -> float:
    """Banda de atitude compativel com a autoridade medida, no eixo mais fraco.

    De ``M = I * wn^2 * theta``, a maior banda que ainda produz o momento pedido para
    um erro de referencia e

        wn_max = sqrt( M_disponivel / (I * theta) )

    O eixo de guinada e **excluido** deste minimo: num traje ele costuma ter uma ordem
    de grandeza menos autoridade que rolagem e arfagem, e amarrar a banda das tres a
    ele produziria um controlador lento demais nos eixos que sustentam o veiculo. A
    guinada recebe banda propria, e a assimetria fica declarada em vez de escondida.

    ⚠ ``reference_error_rad`` e o erro para o qual o controlador foi dimensionado, nao
    um limite. Erros maiores saturam a alocacao, e e exatamente isso que a varredura
    de atraso explora.
    """
    inercia = np.asarray(inertia_kg_m2, dtype=np.float64)
    if inercia.shape == (3, 3):
        inercia = np.diag(inercia)
    if inercia.shape != (3,):
        raise ValueError("inercia deve ser tensor (3,3) ou vetor (3,)")
    if not 0.0 < reference_error_rad < math.pi:
        raise ValueError("erro de referencia em (0, pi)")

    momentos = budget.horizon_Nm if use_horizon else budget.static_Nm
    bandas = [
        math.sqrt(m / (i * reference_error_rad)) if m > 0.0 and i > 0.0 else 0.0
        for m, i in zip(momentos[:2], inercia[:2], strict=True)
    ]
    return min(bandas)
