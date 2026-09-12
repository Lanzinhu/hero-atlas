"""Controlador de atitude e altitude, no dominio de tempo **declarado**.

Ver ADR-005 e a regra de tempo do plano.

⚠ **O dominio temporal do integrador do controlador e uma escolha, nao um detalhe.**
Um integrador continuo e uma soma acumulada digital sao os dois validos e tem **fase
diferente**, o que muda a margem de estabilidade. Este controlador e explicitamente
**amostrado**: ele so existe nos instantes do tique, acumula por soma discreta, e o
comando fica retido entre tiques. Nada aqui e avaliado dentro do passo do integrador
continuo.

A estrutura e deliberadamente simples, porque o objeto de estudo nao e o controlador:

    erro de atitude  -> momento desejado    (proporcional e derivativo, sem integral)
    erro de altitude -> forca vertical      (proporcional, derivativo e integral)

⚠ **A forca comandada e so ao longo do eixo vertical do corpo.** Pedir a forca que
cancela o vetor peso inteiro parece mais correto e e pior: com o tronco inclinado esse
pedido tem componente lateral, e nesta arquitetura forca lateral e momento de rolagem
sao quase proporcionais. O pedido de forca arrastaria momento junto e o controlador de
altitude passaria a brigar com o de atitude. A posicao lateral fica livre, como em
qualquer aeronave de decolagem vertical.

⚠ **Sem integral na atitude, e a ausencia e proposital.** Com atuador lento e limite
de rampa, o termo integral carrega durante a saturacao e devolve o acumulo depois, o
que produz sobressinal que se confunde com instabilidade do conjunto. Como a pergunta
do projeto e "quanto atraso a arquitetura tolera", um controlador que adiciona seu
proprio modo de falha contamina a resposta. A integral fica na altitude, onde ela
corrige erro de modelo de massa e onde a saturacao e menos violenta.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..dynamics.quaternion import normalize, quaternion_error, rotation_matrix_ib
from ..dynamics.rigid_body import PlantState
from ..units import G0

__all__ = [
    "AttitudeGains",
    "AltitudeGains",
    "HoverController",
    "ControllerOutput",
]


@dataclass(frozen=True, slots=True)
class AttitudeGains:
    """Ganhos de atitude, em termos de banda e amortecimento, nao de numeros soltos.

    Declarar ``omega_n`` e ``zeta`` em vez de ``kp`` e ``kd`` faz o ganho escalar com
    a inercia automaticamente, e torna a comparacao entre arquiteturas honesta: duas
    geometrias com inercias diferentes recebem o **mesmo objetivo de banda**, nao o
    mesmo numero de ganho.

        M = I ( omega_n^2 * 2 * e_vec  -  2 zeta omega_n * omega )

    O fator dois na parte vetorial vem da linearizacao do quaternion de erro para
    angulos pequenos, onde ``e_vec`` vale metade do erro angular.
    """

    natural_frequency_rad_s: float = 6.0
    damping_ratio: float = 0.9

    def __post_init__(self) -> None:
        if not math.isfinite(self.natural_frequency_rad_s) or self.natural_frequency_rad_s <= 0.0:
            raise ValueError("banda de atitude precisa ser positiva e finita")
        if not 0.0 < self.damping_ratio <= 2.0:
            raise ValueError("amortecimento em (0, 2]")


@dataclass(frozen=True, slots=True)
class AltitudeGains:
    """Ganhos de altitude, tambem em banda e amortecimento."""

    natural_frequency_rad_s: float = 1.2
    damping_ratio: float = 1.0
    integral_time_s: float = 8.0

    def __post_init__(self) -> None:
        if self.natural_frequency_rad_s <= 0.0 or self.damping_ratio <= 0.0:
            raise ValueError("banda e amortecimento de altitude precisam ser positivos")
        if self.integral_time_s <= 0.0:
            raise ValueError("tempo integral precisa ser positivo")


@dataclass(frozen=True, slots=True)
class ControllerOutput:
    """Wrench desejado, no corpo, sobre o ponto de referencia da geometria."""

    wrench: NDArray[np.float64]
    attitude_error_rad: float
    altitude_error_m: float
    integral_state: float

    @property
    def force_N(self) -> NDArray[np.float64]:
        return self.wrench[:3]

    @property
    def moment_Nm(self) -> NDArray[np.float64]:
        return self.wrench[3:]


@dataclass(slots=True)
class HoverController:
    """Mantem atitude de referencia e altitude, com saida amostrada e retida.

    ⚠ O comando so muda em :meth:`tick`. Entre tiques ele fica **retido**, e e essa
    retencao que o laco fechado integra. Chamar o controlador dentro de um subpasso de
    Runge-Kutta seria transformar um controlador discreto em continuo e apagar a fase
    que a amostragem introduz.

    Attributes:
        mass_kg: massa usada para converter aceleracao vertical em forca. E a massa
            **assumida** pelo controlador: divergir da real e um erro de modelo que a
            integral de altitude corrige, e isso e deliberado.
        inertia_kg_m2: inercia assumida, que converte banda em ganho.
        center_of_mass_body_m: usado para transportar o momento do centro para o ponto
            de referencia da geometria, que e onde o alocador trabalha.
    """

    mass_kg: float
    inertia_kg_m2: NDArray[np.float64]
    sample_period_s: float
    center_of_mass_body_m: NDArray[np.float64] = field(default_factory=lambda: np.zeros(3))
    attitude: AttitudeGains = field(default_factory=AttitudeGains)
    altitude: AltitudeGains = field(default_factory=AltitudeGains)
    reference_quaternion_ib: NDArray[np.float64] = field(
        default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0])
    )
    reference_altitude_m: float = 0.0
    integral_altitude: float = 0.0
    integral_limit_m_s: float = 3.0

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            raise ValueError("massa assumida precisa ser positiva")
        if self.sample_period_s <= 0.0:
            raise ValueError("periodo de amostragem precisa ser positivo")
        tensor = np.asarray(self.inertia_kg_m2, dtype=np.float64)
        if tensor.shape != (3, 3):
            raise ValueError("inercia assumida deve ter forma (3, 3)")
        self.inertia_kg_m2 = tensor
        self.center_of_mass_body_m = np.asarray(self.center_of_mass_body_m, dtype=np.float64)
        self.reference_quaternion_ib = normalize(self.reference_quaternion_ib)

    @property
    def sample_rate_hz(self) -> float:
        return 1.0 / self.sample_period_s

    def reset(self) -> None:
        self.integral_altitude = 0.0

    def tick(
        self, state: PlantState, *, reference_altitude_m: float | None = None
    ) -> ControllerOutput:
        """Um disparo do controlador. So deve ser chamado no instante do tique.

        A altura e medida como ``-z`` no inercial, porque o eixo z aponta para baixo.
        """
        alvo = self.reference_altitude_m if reference_altitude_m is None else reference_altitude_m

        # --- atitude: proporcional e derivativo sobre o quaternion de erro ---
        erro_q = quaternion_error(self.reference_quaternion_ib, state.quaternion_ib)
        # O sinal do escalar remove a ambiguidade de dupla cobertura: q e -q sao a
        # mesma rotacao, e sem isto o controlador giraria pelo caminho longo.
        vetorial = erro_q[1:] if erro_q[0] >= 0.0 else -erro_q[1:]
        angulo = 2.0 * float(np.arcsin(np.clip(np.linalg.norm(vetorial), 0.0, 1.0)))

        wn, zeta = self.attitude.natural_frequency_rad_s, self.attitude.damping_ratio
        aceleracao_angular = -(wn**2) * 2.0 * vetorial - 2.0 * zeta * wn * state.omega_B_rad_s
        momento_cg = self.inertia_kg_m2 @ aceleracao_angular

        # --- altitude: proporcional, derivativo e integral, soma discreta ---
        altura = -float(state.position_O_I_m[2])
        velocidade_subida = -float(state.velocity_O_I_m_s[2])
        erro_altura = alvo - altura

        wz, zz = self.altitude.natural_frequency_rad_s, self.altitude.damping_ratio
        self.integral_altitude = float(
            np.clip(
                self.integral_altitude + erro_altura * self.sample_period_s,
                -self.integral_limit_m_s,
                self.integral_limit_m_s,
            )
        )
        aceleracao_vertical = (
            wz**2 * erro_altura
            - 2.0 * zz * wz * velocidade_subida
            + (wz**2 / self.altitude.integral_time_s) * self.integral_altitude
        )

        # --- forca: **so** ao longo do eixo vertical do corpo ---
        #
        # ⚠ Aqui mora um erro que custou caro e que e facil de cometer. A versao
        # anterior pedia a forca que cancela o vetor peso inteiro, ou seja
        # ``-R_bi @ peso``, que com o tronco inclinado tem componente lateral.
        #
        # Nesta geometria forca lateral e momento de rolagem sao quase proporcionais,
        # que e exatamente o acoplamento que o experimento 1 encontrou. Pedir forca
        # lateral **arrasta um momento de rolagem junto**, o controlador de forca
        # passa a brigar com o de atitude, e uma perturbacao de cinco graus chegava a
        # exceder vinte antes de voltar.
        #
        # Aeronave de decolagem vertical real nao faz isso: ela empurra so ao longo do
        # proprio eixo e deixa a posicao lateral derivar, ou inclina de proposito para
        # translada. A politica aqui e a mesma, e esta declarada em vez de implicita.
        inclinacao_cos = float(np.clip(rotation_matrix_ib(state.quaternion_ib)[2, 2], 1e-3, 1.0))
        empuxo_necessario = self.mass_kg * (G0 + aceleracao_vertical) / inclinacao_cos
        forca_corpo = np.array([0.0, 0.0, -empuxo_necessario])

        # Transporte do momento: o controlador pensa no centro, o alocador trabalha
        # sobre o ponto de referencia da geometria.
        deslocamento = self.center_of_mass_body_m
        momento_referencia = momento_cg + np.cross(deslocamento, forca_corpo)

        return ControllerOutput(
            wrench=np.concatenate([forca_corpo, momento_referencia]),
            attitude_error_rad=angulo,
            altitude_error_m=erro_altura,
            integral_state=self.integral_altitude,
        )

    def with_reference_attitude(self, quaternion_ib: ArrayLike) -> None:
        self.reference_quaternion_ib = normalize(quaternion_ib)
