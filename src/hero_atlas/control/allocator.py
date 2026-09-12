"""Alocador: do wrench desejado para o comando de cada propulsor.

Ver ADR-003 e ADR-004.

⚠ **O alocador nao promete empuxo instantaneo, e essa e a razao de ele existir
assim.** A cadeia real e ``u -> T_ss(u) -> T(t) -> F(t) -> w(t)``, e a turbina lenta e
o motivo do projeto. Um alocador que resolve ``W T = w`` com ``T`` livre dentro de
``[T_min, T_max]`` esta respondendo a pergunta errada: ele diz o que seria atingivel
se os motores fossem instantaneos.

A pergunta certa e **o que da para atingir dentro do horizonte**::

    T_i(t + Ha) em [ max(T_min, T_i - Tdot_desce * Ha) ,
                     min(T_max, T_i + Tdot_sobe  * Ha) ]

e o problema resolvido e minimos quadrados **com essas caixas**, nao com as caixas
fisicas. A diferenca entre as duas e exatamente a margem dinamica do ADR-004, e ela
aparece como :attr:`AllocationResult.horizon_shrinkage`.

Escala entre forca e momento. Somar newton com newton-metro sem escala faz o
resultado depender da unidade escolhida. O alocador usa um comprimento caracteristico
declarado::

    S = diag(1, 1, 1, 1/L, 1/L, 1/L)      residuo = || S (W T - w) ||

com ``L`` vindo da propria geometria: a maior distancia de propulsor ao ponto de
referencia. Nao e arbitrario e nao e magico, e esta declarado.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import lsq_linear

from ..airframe.geometry import PropulsionGeometry, allocation_matrix
from ..io.telemetry import AllocatorEventType
from ..propulsion.actuator import ActuatorEnvelope

__all__ = [
    "AllocationStatus",
    "AllocationResult",
    "characteristic_length_m",
    "reachable_box",
    "allocate",
]

_ATTAINABLE_TOL = 1e-6


class AllocationStatus(StrEnum):
    """Como a alocacao terminou. Quatro modos, nao um booleano.

    ``WRENCH_UNATTAINABLE`` e o modo principal e o mais traicoeiro: com caixas e
    minimos quadrados **quase sempre existe** solucao admissivel, e ela quase sempre e
    incapaz de produzir o wrench pedido. Um alocador que so devolve o vetor de empuxo
    esconde isso.
    """

    OK = "ok"
    WRENCH_UNATTAINABLE = "wrench_unattainable"
    SOLVER_FAILURE = "solver_failure"
    NO_ACTUATORS = "no_actuators"

    def as_telemetry(self) -> AllocatorEventType | None:
        if self is AllocationStatus.OK:
            return None
        if self is AllocationStatus.WRENCH_UNATTAINABLE:
            return AllocatorEventType.WRENCH_UNATTAINABLE
        if self is AllocationStatus.SOLVER_FAILURE:
            return AllocatorEventType.SOLVER_FAILURE
        return AllocatorEventType.ALLOCATOR_INFEASIBLE


@dataclass(frozen=True, slots=True)
class AllocationResult:
    """O que o alocador conseguiu, e o que ele nao conseguiu.

    Attributes:
        commands_N: empuxo comandado por propulsor, ja dentro da caixa alcancavel.
        requested_wrench: o que o controlador pediu.
        achieved_wrench: o que ``W @ commands`` produz.
        normalized_residual: ``|| S (W T - w) || / || S w ||``, adimensional.
        active_constraints: quais limites estao ativos, por nome de propulsor.
        horizon_shrinkage: quanto a caixa do horizonte encolheu em relacao a caixa
            fisica, em fracao. Zero significa que a rampa nao limitou nada neste
            instante; perto de um significa que o atuador mal pode se mover.
    """

    status: AllocationStatus
    commands_N: NDArray[np.float64]
    requested_wrench: NDArray[np.float64]
    achieved_wrench: NDArray[np.float64]
    normalized_residual: float
    active_constraints: tuple[str, ...]
    horizon_shrinkage: float

    @property
    def attainable(self) -> bool:
        return self.status is AllocationStatus.OK

    @property
    def residual_wrench(self) -> NDArray[np.float64]:
        return self.achieved_wrench - self.requested_wrench


def characteristic_length_m(geometry: PropulsionGeometry) -> float:
    """Comprimento que torna forca e momento comparaveis: o maior braco.

    ⚠ E uma **escolha declarada**, nao uma constante da fisica. Ela define o que
    significa "residuo de wrench pequeno", e trocar por outro comprimento muda o peso
    relativo entre errar forca e errar momento. Fica aqui, visivel, em vez de virar
    um peso magico dentro do solver.
    """
    bracos = [
        float(np.linalg.norm(n.position_body_m - geometry.reference_point_body_m))
        for n in geometry.available
    ]
    maior = max(bracos) if bracos else 0.0
    return maior if maior > 1e-6 else 1.0


def reachable_box(
    thrust_now_N: ArrayLike,
    envelopes: tuple[ActuatorEnvelope, ...],
    horizon_s: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Caixa de empuxo alcancavel em ``horizon_s``, dada a rampa de cada atuador.

    E a intersecao entre o que a fisica permite e o que a rampa permite chegar::

        inferior_i = max( T_min , T_i - Tdot_desce * Ha )
        superior_i = min( T_max , T_i + Tdot_sobe  * Ha )

    ⚠ Com ``Ha`` grande a caixa vira a caixa fisica e o alocador volta a mentir sobre
    a velocidade do motor. Com ``Ha`` pequeno demais a caixa fecha em torno do valor
    atual e o alocador nao consegue pedir nada. O horizonte e parametro de projeto e
    entra na varredura de sensibilidade, nunca como constante escondida.
    """
    atual = np.asarray(thrust_now_N, dtype=np.float64)
    if atual.shape != (len(envelopes),):
        raise ValueError(
            f"empuxo atual tem {atual.shape} e ha {len(envelopes)} atuadores declarados"
        )
    if not np.isfinite(horizon_s) or horizon_s <= 0.0:
        raise ValueError(f"horizonte precisa ser positivo e finito, recebeu {horizon_s!r}")

    inferior = np.array(
        [
            max(env.thrust_min_N, t - env.rate_down_max_N_s * horizon_s)
            for t, env in zip(atual, envelopes, strict=True)
        ]
    )
    superior = np.array(
        [
            min(env.thrust_max_N, t + env.rate_up_max_N_s * horizon_s)
            for t, env in zip(atual, envelopes, strict=True)
        ]
    )
    # Excesso numerico do integrador pode deixar o empuxo fora da faixa fisica; nesse
    # caso a caixa degenera e o solver falharia. Projetar e registrar, nunca abortar.
    superior = np.maximum(superior, inferior)
    return inferior, superior


def allocate(
    geometry: PropulsionGeometry,
    *,
    desired_wrench: ArrayLike,
    thrust_now_N: ArrayLike,
    envelopes: tuple[ActuatorEnvelope, ...],
    horizon_s: float,
    characteristic_length_m_override: float | None = None,
) -> AllocationResult:
    """Resolve minimos quadrados com caixa **do horizonte**, nao caixa fisica.

        min_T || S (W T - w) ||^2   s.a.   T em caixa_alcancavel(Ha)

    Args:
        desired_wrench: seis componentes, forca depois momento, no referencial do
            corpo e sobre o **ponto de referencia** da geometria.
        horizon_s: quanto tempo o alocador supoe ter para chegar no comando.
    """
    disponiveis = geometry.available
    w = np.asarray(desired_wrench, dtype=np.float64)
    if w.shape != (6,):
        raise ValueError(f"wrench deve ter forma (6,), recebeu {w.shape}")

    if not disponiveis:
        return AllocationResult(
            status=AllocationStatus.NO_ACTUATORS,
            commands_N=np.zeros(0),
            requested_wrench=w,
            achieved_wrench=np.zeros(6),
            normalized_residual=float("inf"),
            active_constraints=(),
            horizon_shrinkage=1.0,
        )

    W = allocation_matrix(geometry)
    comprimento = (
        characteristic_length_m(geometry)
        if characteristic_length_m_override is None
        else characteristic_length_m_override
    )
    escala = np.array([1.0, 1.0, 1.0, 1.0 / comprimento, 1.0 / comprimento, 1.0 / comprimento])
    S = np.diag(escala)

    inferior, superior = reachable_box(thrust_now_N, envelopes, horizon_s)
    fisica_largura = np.array([e.thrust_max_N - e.thrust_min_N for e in envelopes])
    horizonte_largura = superior - inferior
    encolhimento = float(
        np.mean(1.0 - np.divide(horizonte_largura, np.maximum(fisica_largura, 1e-12)))
    )

    try:
        solucao = lsq_linear(
            S @ W,
            S @ w,
            bounds=(inferior, superior),
            method="bvls",
            tol=1e-10,
            max_iter=200,
        )
    except (ValueError, np.linalg.LinAlgError) as erro:  # pragma: no cover
        return AllocationResult(
            status=AllocationStatus.SOLVER_FAILURE,
            commands_N=np.asarray(thrust_now_N, dtype=np.float64),
            requested_wrench=w,
            achieved_wrench=np.zeros(6),
            normalized_residual=float("inf"),
            active_constraints=(f"solver: {erro}",),
            horizon_shrinkage=encolhimento,
        )

    comandos = np.asarray(solucao.x, dtype=np.float64)
    alcancado = W @ comandos

    escala_pedido = float(np.linalg.norm(S @ w))
    residuo = float(np.linalg.norm(S @ (alcancado - w)))
    normalizado = residuo / escala_pedido if escala_pedido > 1e-12 else residuo

    ativos: list[str] = []
    for bocal, valor, lo, hi in zip(disponiveis, comandos, inferior, superior, strict=True):
        if valor <= lo + 1e-9:
            ativos.append(f"{bocal.name}_inferior")
        elif valor >= hi - 1e-9:
            ativos.append(f"{bocal.name}_superior")

    status = (
        AllocationStatus.OK
        if normalizado <= _ATTAINABLE_TOL
        else AllocationStatus.WRENCH_UNATTAINABLE
    )

    return AllocationResult(
        status=status,
        commands_N=comandos,
        requested_wrench=w,
        achieved_wrench=alcancado,
        normalized_residual=normalizado,
        active_constraints=tuple(ativos),
        horizon_shrinkage=encolhimento,
    )
