"""Trim: equilibrio vetorial, com o momento do peso sobre o ponto de referencia.

Ver vault/02 - Decisoes/ADR-002 - Trim inclui momento do peso.md

    A gravidade atua NO CENTRO DE MASSA. Sobre um ponto ``O`` diferente do centro,
    ela produz momento. Omitir esse termo faz o trim de qualquer postura assimetrica
    sair errado, parecendo equilibrado.

Aqui o marco 1 deixa de valer como fonte de verdade. O cosseno unico presumia que
toda capacidade instalada contribui para a direcao util; o trim resolve com direcao,
posicao e limite proprios por propulsor, e descobre quanto de fato sobra.

    min   soma_i T_i
    s.a.  soma_i T_i * n_i,B                            = -m * R_BI * g_I
          soma_i (r_i - r_O) x (T_i * n_i,B)
            + (r_C - r_O) x (m * R_BI * g_I)            = 0
          T_i,min <= T_i <= T_i,max

Linear em ``T`` para uma pose e atitude dadas, entao resolve por programacao linear.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy.optimize import linprog

from ..airframe.geometry import PropulsionGeometry, allocation_matrix
from ..model_status import PROPULSAO_INSTALADA_HOJE, ModelStatus
from ..units import G0
from ..verdict import Verdict

__all__ = [
    "TrimTarget",
    "InfeasibilityCause",
    "TrimSolution",
    "CaptureAssessment",
    "solve_trim",
    "assess_capture",
    "gravity_in_body_N",
]

_RESIDUAL_TOL = 1e-6
_RANK_TOL = 1e-9


class InfeasibilityCause(StrEnum):
    """Por que nao ha equilibrio. Duas causas **completamente diferentes**.

    ``GEOMETRICALLY_UNATTAINABLE`` e falha de arquitetura: o wrench exigido esta
    fora do espaco coluna da matriz de alocacao, entao **nenhum** empuxo o produz,
    por maior que seja. Motor mais forte nao resolve; geometria diferente resolve.

    ``BOUNDS_INFEASIBLE`` e falha de capacidade: a direcao e atingivel, mas os
    limites de empuxo bloqueiam. Motor mais forte, ou marcha lenta mais baixa,
    resolve.

    Fundir as duas faz alguem comprar turbina maior para um problema que turbina
    nenhuma resolve.
    """

    NONE = "none"
    GEOMETRICALLY_UNATTAINABLE = "geometrically_unattainable"
    BOUNDS_INFEASIBLE = "bounds_infeasible"
    NO_ACTUATORS = "no_actuators"


class TrimTarget(StrEnum):
    """Os varios problemas que se chamam "trim".

    O marco 2 implementa apenas ``LEVEL_HOVER``, mas o tipo entra no contrato desde
    o inicio, porque cada um fixa coisas diferentes e fundi-los esconde a hipotese.
    """

    LEVEL_HOVER = "level_hover"
    TILTED_HOVER = "tilted_hover"
    UNIFORM_TRANSLATION = "uniform_translation"
    COORDINATED_TURN = "coordinated_turn"
    CONTROLLED_DESCENT = "controlled_descent"
    POST_FAILURE = "post_failure"


def gravity_in_body_N(
    mass_kg: float, rotation_body_from_inertial: ArrayLike | None = None
) -> NDArray[np.float64]:
    """Forca peso expressa no referencial do corpo.

        F_w,B = m * R_BI * g_I,   com g_I = [0, 0, +g] em referencial com z para baixo

    A rotacao importa: **o trim de uma postura inclinada depende da atitude do
    tronco**, e essa e a razao de o argumento existir em vez de a gravidade ser
    constante no corpo.
    """
    if mass_kg <= 0.0:
        raise ValueError("massa precisa ser positiva")
    g_inertial = np.array([0.0, 0.0, G0])
    if rotation_body_from_inertial is None:
        return mass_kg * g_inertial
    R = np.asarray(rotation_body_from_inertial, dtype=np.float64)
    if R.shape != (3, 3):
        raise ValueError(f"rotacao deve ter forma (3, 3), recebeu {R.shape}")
    return mass_kg * (R @ g_inertial)


@dataclass(frozen=True, slots=True)
class TrimSolution:
    """Resultado do trim, com as duas viabilidades separadas.

    Ver vault/03 - Regras/R-02 - Dois niveis de trim.md: existencia matematica nao
    e alcancabilidade.
    """

    status: Verdict
    target: TrimTarget
    thrusts_N: NDArray[np.float64]
    nozzle_names: tuple[str, ...]
    required_wrench: NDArray[np.float64]
    achieved_wrench: NDArray[np.float64]
    active_constraints: tuple[str, ...]
    model_status: ModelStatus
    cause: InfeasibilityCause = InfeasibilityCause.NONE
    unattainable_component: NDArray[np.float64] | None = None
    message: str = ""

    @property
    def feasible(self) -> bool:
        """Viabilidade **estatica**: existe vetor de empuxos dentro dos limites."""
        return self.status is Verdict.SATISFIED

    @property
    def total_thrust_N(self) -> float:
        return float(np.sum(self.thrusts_N)) if self.thrusts_N.size else 0.0

    @property
    def residual_wrench(self) -> NDArray[np.float64]:
        return self.achieved_wrench - self.required_wrench

    @property
    def vertical_efficiency(self) -> float:
        """Quanto da soma escalar de empuxo vira forca util na vertical.

        ⚠ E o numero que o marco 1 nao conseguia ver. O envelope presumia 1,0 menos
        o cosseno; aqui sai da geometria real, com bocais que se cancelam
        parcialmente entre si.
        """
        if not self.feasible or self.total_thrust_N <= 0.0:
            return 0.0
        return abs(self.achieved_wrench[2]) / self.total_thrust_N


def solve_trim(
    geometry: PropulsionGeometry,
    *,
    mass_kg: float,
    center_of_mass_body_m: ArrayLike,
    target: TrimTarget = TrimTarget.LEVEL_HOVER,
    rotation_body_from_inertial: ArrayLike | None = None,
    model_status: ModelStatus = PROPULSAO_INSTALADA_HOJE,
) -> TrimSolution:
    """Resolve o equilibrio de pose e massa **congeladas**.

    Contrato explicito, conforme ADR-002: ``qdot = 0``, ``qddot = 0``, ``mdot_f = 0``
    e cenario atmosferico constante. Um ``solve_dynamic_trim`` para postura
    deliberadamente variavel e problema posterior.

    Args:
        geometry: os propulsores, com o ponto de referencia embutido.
        mass_kg: massa total no instante.
        center_of_mass_body_m: onde esta o centro de massa, no referencial do corpo.
            **Nao** coincide com o ponto de referencia, e a diferenca e exatamente o
            que produz o momento do peso.
        target: qual problema de trim. O marco 2 so implementa pairado nivelado.
        rotation_body_from_inertial: atitude do tronco. Identidade se ausente.
    """
    if target is not TrimTarget.LEVEL_HOVER:
        raise NotImplementedError(
            f"trim {target.value!r} ainda nao implementado; o marco 2 cobre "
            "apenas 'level_hover'. O tipo existe no contrato para a hipotese "
            "ficar visivel, nao para ser silenciosamente tratado como pairado."
        )

    disponiveis = geometry.available
    if not disponiveis:
        return TrimSolution(
            status=Verdict.VIOLATED,
            target=target,
            thrusts_N=np.zeros(0),
            nozzle_names=(),
            required_wrench=np.zeros(6),
            achieved_wrench=np.zeros(6),
            active_constraints=("nenhum propulsor disponivel",),
            model_status=model_status,
            cause=InfeasibilityCause.NO_ACTUATORS,
            message="todos os propulsores indisponiveis",
        )

    W = allocation_matrix(geometry)
    peso_B = gravity_in_body_N(mass_kg, rotation_body_from_inertial)

    centro = np.asarray(center_of_mass_body_m, dtype=np.float64)
    if centro.shape != (3,):
        raise ValueError("centro de massa deve ter forma (3,)")
    braco_cg = centro - geometry.reference_point_body_m

    # O termo que o ADR-002 existe para nao deixar esquecer.
    momento_do_peso = np.cross(braco_cg, peso_B)
    wrench_requerido = np.concatenate([-peso_B, -momento_do_peso])

    limites = [(n.thrust_min_N, n.thrust_max_N) for n in disponiveis]
    resultado = linprog(
        c=np.ones(len(disponiveis)),
        A_eq=W,
        b_eq=wrench_requerido,
        bounds=limites,
        method="highs",
    )

    nomes = tuple(n.name for n in disponiveis)

    if not resultado.success:
        causa, componente = _diagnosticar(W, wrench_requerido)
        return TrimSolution(
            status=Verdict.VIOLATED,
            target=target,
            thrusts_N=np.zeros(len(disponiveis)),
            nozzle_names=nomes,
            required_wrench=wrench_requerido,
            achieved_wrench=np.zeros(6),
            active_constraints=_limites_ativos(np.zeros(len(disponiveis)), disponiveis),
            model_status=model_status,
            cause=causa,
            unattainable_component=componente,
            message=_explicar(causa, componente),
        )

    empuxos = np.asarray(resultado.x, dtype=np.float64)
    alcancado = W @ empuxos
    residuo = float(np.linalg.norm(alcancado - wrench_requerido))

    status = Verdict.SATISFIED if residuo < _RESIDUAL_TOL else Verdict.VIOLATED
    return TrimSolution(
        status=status,
        target=target,
        thrusts_N=empuxos,
        nozzle_names=nomes,
        required_wrench=wrench_requerido,
        achieved_wrench=alcancado,
        active_constraints=_limites_ativos(empuxos, disponiveis),
        model_status=model_status,
        message="" if status is Verdict.SATISFIED else f"residuo {residuo:.3e}",
    )


def _diagnosticar(
    W: NDArray[np.float64], wrench: NDArray[np.float64]
) -> tuple[InfeasibilityCause, NDArray[np.float64] | None]:
    """Separa impossibilidade geometrica de limite de capacidade.

    Resolve sem limites de empuxo. Se nem assim o wrench e reproduzido, ele esta
    fora do espaco coluna e **nenhum** motor o alcanca.
    """
    solucao, *_ = np.linalg.lstsq(W, wrench, rcond=None)
    residuo = W @ solucao - wrench
    if float(np.linalg.norm(residuo)) > 1e-8:
        return InfeasibilityCause.GEOMETRICALLY_UNATTAINABLE, residuo
    return InfeasibilityCause.BOUNDS_INFEASIBLE, None


_ROTULO_WRENCH = ("Fx", "Fy", "Fz", "Mx", "My", "Mz")


def _explicar(causa: InfeasibilityCause, componente: NDArray[np.float64] | None) -> str:
    if causa is InfeasibilityCause.GEOMETRICALLY_UNATTAINABLE and componente is not None:
        dominantes = [
            f"{_ROTULO_WRENCH[i]}={componente[i]:+.3g}"
            for i in np.argsort(-np.abs(componente))[:3]
            if abs(componente[i]) > 1e-8
        ]
        return (
            "wrench fora do espaco coluna da matriz de alocacao: nenhum empuxo o "
            f"produz. Componente irreproduzivel: {', '.join(dominantes)}. "
            "Motor maior nao resolve; geometria diferente resolve."
        )
    if causa is InfeasibilityCause.BOUNDS_INFEASIBLE:
        return (
            "direcao atingivel, mas bloqueada pelos limites de empuxo. "
            "Motor maior ou marcha lenta menor resolve."
        )
    return ""


def _limites_ativos(empuxos: NDArray[np.float64], bocais: tuple) -> tuple[str, ...]:
    """Quais limites estao encostados na solucao, para diagnostico."""
    ativos: list[str] = []
    for valor, bocal in zip(empuxos, bocais, strict=True):
        if abs(valor - bocal.thrust_min_N) < 1e-6:
            ativos.append(f"{bocal.name}_idle")
        elif abs(valor - bocal.thrust_max_N) < 1e-6:
            ativos.append(f"{bocal.name}_max")
    return tuple(ativos)


@dataclass(frozen=True, slots=True)
class CaptureAssessment:
    """Viabilidade **dinamica**: da para chegar ao trim a partir de onde se esta.

    Um trim pos-falha pode existir matematicamente e ser inalcancavel antes de uma
    perda de altitude ou de uma rotacao perigosa.
    """

    reachable_within_horizon: bool
    horizon_s: float
    limiting_actuators: tuple[str, ...]
    required_time_s: float

    @property
    def status(self) -> Verdict:
        return Verdict.SATISFIED if self.reachable_within_horizon else Verdict.VIOLATED


def assess_capture(
    solution: TrimSolution,
    *,
    current_thrusts_N: ArrayLike,
    rate_up_N_s: float,
    rate_down_N_s: float,
    horizon_s: float,
) -> CaptureAssessment:
    """Se o conjunto consegue **alcancar** o trim dentro do horizonte.

    Existencia nao e alcancabilidade. Ver R-02.

    O tempo necessario e ditado pelo propulsor mais lento a chegar, porque o trim so
    existe com todos no lugar: chegar com quatro de cinco nao e equilibrio.
    """
    if not solution.feasible:
        raise ValueError("nao ha trim para alcancar: a solucao e inviavel")
    if rate_up_N_s <= 0.0 or rate_down_N_s <= 0.0 or horizon_s <= 0.0:
        raise ValueError("taxas e horizonte precisam ser positivos")

    atual = np.asarray(current_thrusts_N, dtype=np.float64)
    if atual.shape != solution.thrusts_N.shape:
        raise ValueError(
            f"empuxo atual com {atual.shape} nao casa com o trim {solution.thrusts_N.shape}"
        )

    delta = solution.thrusts_N - atual
    tempos = np.where(delta >= 0.0, delta / rate_up_N_s, -delta / rate_down_N_s)
    necessario = float(np.max(tempos)) if tempos.size else 0.0

    limitantes = tuple(
        nome for nome, t in zip(solution.nozzle_names, tempos, strict=True) if t > horizon_s
    )

    return CaptureAssessment(
        reachable_within_horizon=necessario <= horizon_s,
        horizon_s=horizon_s,
        limiting_actuators=limitantes,
        required_time_s=necessario,
    )
