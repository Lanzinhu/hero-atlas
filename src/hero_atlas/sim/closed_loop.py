"""Laco fechado: controlador amostrado, alocador, atuador com atraso e corpo rigido.

E aqui que as pecas do marco 3 se encontram. Cada uma ja existia e era testada
isolada; o que este modulo adiciona e a **ordem correta** entre elas, que e onde o
erro caro mora.

A ordem, por passo::

    1. eventos agendados caem em t, antes de integrar
    2. no tique do controlador: le o estado, calcula wrench, aloca, EMPILHA o comando
    3. integra [estado | empuxo] de t a t+dt, com o comando ATRASADO e RETIDO
    4. projeta o empuxo na faixa fisica, registrando se precisou

⚠ **O comando nunca vira empuxo.** O alocador empilha ``u``; quem decide ``T(t)`` e a
equacao diferencial do atuador, e so ela. Essa separacao e a razao de o projeto
existir, e um laco que a viole produz trajetoria suave e falsa. Ver ADR-003.

⚠ **O controlador nao e chamado dentro do subpasso de Runge-Kutta.** Ele e discreto,
dispara no tique e fica retido. Avalia-lo dentro do subpasso o transformaria num
controlador continuo e apagaria a fase que a amostragem introduz, que e justamente
parte do que se quer medir.

O resultado nao e "estavel" ou "instavel". E **qual falha aconteceu**, porque perder
altitude por falta de empuxo e divergir em atitude por atraso sao coisas diferentes
que exigem correcoes diferentes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..airframe.geometry import PropulsionGeometry, allocation_matrix
from ..control.allocator import AllocationStatus, allocate
from ..control.attitude import HoverController
from ..dynamics.integrators import rk4_step
from ..dynamics.quaternion import quaternion_error
from ..dynamics.rigid_body import BodyWrench, PlantState, RigidBodyProperties, state_derivative
from ..io.telemetry import TelemetryLog
from ..propulsion.actuator import (
    ActuatorEnvelope,
    ActuatorLimit,
    CommandDelayLine,
    project_thrust_N,
    thrust_rate_N_s,
)
from ..sim.events import EventSchedule, PeriodicSource

__all__ = [
    "TerminationMode",
    "ClosedLoopLimits",
    "ClosedLoopResult",
    "simulate",
    "CONTROLLER_EVENT",
    "LIMITES_PADRAO",
]

CONTROLLER_EVENT = "controller_tick"


class TerminationMode(StrEnum):
    """Por que a simulacao terminou. **Nunca** um booleano de estabilidade.

    Perder altitude por falta de empuxo e divergir em atitude por atraso sao falhas
    diferentes, com correcoes diferentes. Fundi-las em "instavel" descarta a unica
    informacao acionavel do experimento.
    """

    CAPTURED = "captured"
    """Chegou na regiao alvo e ficou nela pelo tempo de retencao exigido."""

    HORIZON_REACHED = "horizon_reached"
    """Acabou o tempo sem falhar e sem capturar. **Nao** e sucesso."""

    ATTITUDE_LIMIT_EXCEEDED = "attitude_limit_exceeded"
    ALTITUDE_LOSS_LIMIT = "altitude_loss_limit"
    WRENCH_UNATTAINABLE = "wrench_unattainable"
    ALLOCATOR_INFEASIBLE = "allocator_infeasible"
    NUMERICAL_FAILURE = "numerical_failure"
    """Estado nao finito. **Nao interpretar como fisica.**"""

    @property
    def is_failure(self) -> bool:
        return self not in (TerminationMode.CAPTURED, TerminationMode.HORIZON_REACHED)


@dataclass(frozen=True, slots=True)
class ClosedLoopLimits:
    """Os limites que definem falha, declarados **antes** de rodar.

    ⚠ Sao escolha de campanha, nao fisica. Mudar qualquer um muda a fronteira de
    atraso que o experimento devolve, e por isso eles viajam junto do resultado.
    """

    attitude_limit_rad: float = np.deg2rad(60.0)
    """Excursao angular acima da qual o caso conta como perdido."""

    altitude_loss_limit_m: float = 3.0
    """Perda de altitude em relacao a inicial que conta como perdida."""

    capture_attitude_rad: float = np.deg2rad(3.0)
    """Erro angular que define "chegou"."""

    capture_hold_s: float = 1.0
    """Quanto tempo precisa ficar dentro da regiao para contar como captura.

    ⚠ Sem tempo de retencao, uma trajetoria que **cruza** a regiao alvo a caminho da
    divergencia seria contada como sucesso.
    """

    wrench_residual_limit: float = 0.35
    """Residuo normalizado de wrench acima do qual o pedido conta como inatingivel."""

    wrench_residual_hold_s: float = 0.5
    """Por quanto tempo o residuo precisa ficar alto para encerrar.

    ⚠ Um pico isolado no transitorio inicial e normal e nao e falha. O que importa e
    o alocador ficar **preso** sem conseguir produzir o wrench pedido.
    """


LIMITES_PADRAO = ClosedLoopLimits()
"""Limites da campanha atual. Singleton, para nao construir em default de argumento."""


@dataclass(frozen=True, slots=True)
class ClosedLoopResult:
    """A trajetoria e, principalmente, por que ela terminou."""

    mode: TerminationMode
    t_end_s: float
    times_s: NDArray[np.float64]
    attitude_error_rad: NDArray[np.float64]
    altitude_m: NDArray[np.float64]
    thrusts_N: NDArray[np.float64]
    wrench_residual: NDArray[np.float64]
    horizon_shrinkage: NDArray[np.float64]
    rate_limited_fraction: float
    saturated_fraction: float
    peak_attitude_error_rad: float
    max_altitude_loss_m: float
    capture_time_s: float | None
    telemetry: TelemetryLog = field(default_factory=TelemetryLog)

    @property
    def captured(self) -> bool:
        return self.mode is TerminationMode.CAPTURED

    @property
    def peak_attitude_error_deg(self) -> float:
        return float(np.rad2deg(self.peak_attitude_error_rad))


def _body_wrench(
    geometry: PropulsionGeometry,
    allocation: NDArray[np.float64],
    thrusts_N: NDArray[np.float64],
    cg_offset_from_reference_m: NDArray[np.float64],
) -> BodyWrench:
    """Wrench dos propulsores, com o momento transportado para o **centro de massa**.

        M_C = M_O - (r_C - r_O) x F

    A matriz de alocacao e montada sobre o ponto de referencia, e a equacao de Euler
    da rota reduzida e sobre o centro. Esquecer este transporte produz um momento
    espurio proporcional ao empuxo total, que o controlador compensa sem reclamar: o
    modo de falha mais caro deste projeto.
    """
    total = allocation @ thrusts_N
    forca = total[:3]
    momento_O = total[3:]
    momento_C = momento_O - np.cross(cg_offset_from_reference_m, forca)
    return BodyWrench(force_N=forca, moment_about_cg_Nm=momento_C)


def simulate(
    geometry: PropulsionGeometry,
    body: RigidBodyProperties,
    envelopes: tuple[ActuatorEnvelope, ...],
    controller: HoverController,
    *,
    initial_state: PlantState,
    initial_thrust_N: ArrayLike,
    t_final_s: float,
    transport_delay_s: float = 0.0,
    allocation_horizon_s: float = 0.20,
    max_step_s: float = 0.002,
    limits: ClosedLoopLimits = LIMITES_PADRAO,
    collect_telemetry: bool = True,
) -> ClosedLoopResult:
    """Integra o laco fechado ate capturar, falhar ou acabar o tempo.

    Args:
        transport_delay_s: atraso puro entre comando e o motor ver o comando. Zero
            significa retencao de ordem zero pura, que ja introduz a fase da
            amostragem.
        allocation_horizon_s: horizonte que o alocador supoe ter. Ver ADR-004.
    """
    n = len(geometry.available)
    if len(envelopes) != n:
        raise ValueError(f"ha {n} propulsores disponiveis e {len(envelopes)} envelopes")
    if transport_delay_s > 0.0 and transport_delay_s < max_step_s:
        raise ValueError(
            f"atraso continuo de {transport_delay_s} s menor que o passo maximo de "
            f"{max_step_s} s: o historico nao tem amostras para sustentar a "
            "interpolacao. Reduza o passo ou modele como retencao de ordem zero."
        )

    W = allocation_matrix(geometry)
    d = body.cg_offset_from_reference_m

    empuxo0 = np.asarray(initial_thrust_N, dtype=np.float64)
    if empuxo0.shape != (n,):
        raise ValueError(f"empuxo inicial deve ter {n} componentes")

    linhas = [CommandDelayLine(initial_value=float(t)) for t in empuxo0]
    for linha, valor in zip(linhas, empuxo0, strict=True):
        linha.push(0.0, float(valor))

    agenda = EventSchedule()
    agenda.add_periodic(
        PeriodicSource.at_rate(CONTROLLER_EVENT, controller.sample_rate_hz, phase_s=0.0)
    )

    telemetria = TelemetryLog()
    x = np.concatenate([initial_state.to_vector(), empuxo0])
    t = 0.0
    altura_inicial = -float(initial_state.position_O_I_m[2])

    def derivada(tempo: float, estado: NDArray[np.float64]) -> NDArray[np.float64]:
        planta = PlantState.from_vector(estado[:13])
        empuxos = estado[13:]
        wrench = _body_wrench(geometry, W, empuxos, d)
        dplanta = state_derivative(planta, body, wrench)
        dempuxo = np.empty(n)
        for i, (linha, env) in enumerate(zip(linhas, envelopes, strict=True)):
            comandado = linha.delayed_value(now_s=tempo, delay_s=transport_delay_s)
            dempuxo[i] = thrust_rate_N_s(
                thrust_N=float(empuxos[i]), commanded_N=comandado, envelope=env
            ).rate_N_s
        return np.concatenate([dplanta, dempuxo])

    tempos: list[float] = []
    erros: list[float] = []
    alturas: list[float] = []
    empuxos_hist: list[NDArray[np.float64]] = []
    residuos: list[float] = []
    encolhimentos: list[float] = []
    passos_com_rampa = 0
    passos_com_saturacao = 0
    passos = 0

    modo = TerminationMode.HORIZON_REACHED
    dentro_desde: float | None = None
    residuo_alto_desde: float | None = None
    captura: float | None = None
    residuo_atual = 0.0
    encolhimento_atual = 0.0

    while t < t_final_s - 1e-12:
        plano = agenda.plan_step(t, max_step_s, t_final_s)

        for evento in plano.events_due:
            if evento.kind != CONTROLLER_EVENT:
                continue
            planta = PlantState.from_vector(x[:13])
            saida = controller.tick(planta)
            resultado = allocate(
                geometry,
                desired_wrench=saida.wrench,
                thrust_now_N=x[13:],
                envelopes=envelopes,
                horizon_s=allocation_horizon_s,
                characteristic_length_m_override=None,
            )
            residuo_atual = resultado.normalized_residual
            encolhimento_atual = resultado.horizon_shrinkage

            if resultado.status is AllocationStatus.NO_ACTUATORS:
                modo = TerminationMode.ALLOCATOR_INFEASIBLE
                break
            for linha, comando in zip(linhas, resultado.commands_N, strict=True):
                linha.push(plano.t_s, float(comando))
            if collect_telemetry and resultado.status is not AllocationStatus.OK:
                telemetria.record(
                    plano.t_s,
                    "allocator",
                    resultado.status.value,
                    normalized_residual=resultado.normalized_residual,
                    horizon_shrinkage=resultado.horizon_shrinkage,
                    active_constraints=list(resultado.active_constraints),
                )
        if modo is TerminationMode.ALLOCATOR_INFEASIBLE:
            break

        if plano.dt_s <= 0.0:
            break

        x = rk4_step(derivada, plano.t_s, x, plano.dt_s)
        t = plano.t_next_s

        if not np.all(np.isfinite(x)):
            modo = TerminationMode.NUMERICAL_FAILURE
            break

        # projecao do empuxo, com registro. ADR-005: telemetria, nao guarda.
        saturou = False
        for i, env in enumerate(envelopes):
            valor, limite = project_thrust_N(float(x[13 + i]), env)
            x[13 + i] = valor
            if limite is not ActuatorLimit.NONE:
                saturou = True

        # ⚠ O controlador NAO e chamado aqui. Ele e discreto e so dispara no tique.
        # O que se le neste ponto e o estado, para decidir termino.
        planta = PlantState.from_vector(x[:13])
        erro_angular = _attitude_error_rad(controller, planta)
        altura = -float(planta.position_O_I_m[2])

        limitou_rampa = False
        for i, env in enumerate(envelopes):
            comandado = linhas[i].delayed_value(now_s=t, delay_s=transport_delay_s)
            resposta = thrust_rate_N_s(
                thrust_N=float(x[13 + i]), commanded_N=comandado, envelope=env
            )
            if {ActuatorLimit.RATE_UP, ActuatorLimit.RATE_DOWN} & set(resposta.limits):
                limitou_rampa = True

        passos += 1
        passos_com_rampa += int(limitou_rampa)
        passos_com_saturacao += int(saturou)

        tempos.append(t)
        erros.append(erro_angular)
        alturas.append(altura)
        empuxos_hist.append(x[13:].copy())
        residuos.append(residuo_atual)
        encolhimentos.append(encolhimento_atual)

        if erro_angular > limits.attitude_limit_rad:
            modo = TerminationMode.ATTITUDE_LIMIT_EXCEEDED
            break
        if altura_inicial - altura > limits.altitude_loss_limit_m:
            modo = TerminationMode.ALTITUDE_LOSS_LIMIT
            break

        if residuo_atual > limits.wrench_residual_limit:
            residuo_alto_desde = t if residuo_alto_desde is None else residuo_alto_desde
            if t - residuo_alto_desde >= limits.wrench_residual_hold_s:
                modo = TerminationMode.WRENCH_UNATTAINABLE
                break
        else:
            residuo_alto_desde = None

        if erro_angular <= limits.capture_attitude_rad:
            dentro_desde = t if dentro_desde is None else dentro_desde
            if t - dentro_desde >= limits.capture_hold_s:
                modo = TerminationMode.CAPTURED
                captura = dentro_desde
                break
        else:
            dentro_desde = None

    return ClosedLoopResult(
        mode=modo,
        t_end_s=t,
        times_s=np.asarray(tempos),
        attitude_error_rad=np.asarray(erros),
        altitude_m=np.asarray(alturas),
        thrusts_N=np.asarray(empuxos_hist) if empuxos_hist else np.zeros((0, n)),
        wrench_residual=np.asarray(residuos),
        horizon_shrinkage=np.asarray(encolhimentos),
        rate_limited_fraction=passos_com_rampa / passos if passos else 0.0,
        saturated_fraction=passos_com_saturacao / passos if passos else 0.0,
        peak_attitude_error_rad=max(erros) if erros else 0.0,
        max_altitude_loss_m=(altura_inicial - min(alturas)) if alturas else 0.0,
        capture_time_s=captura,
        telemetry=telemetria,
    )


def _attitude_error_rad(controller: HoverController, state: PlantState) -> float:
    """Erro angular em relacao a referencia do controlador, sem efeito colateral."""
    erro = quaternion_error(controller.reference_quaternion_ib, state.quaternion_ib)
    vetorial = erro[1:] if erro[0] >= 0.0 else -erro[1:]
    return 2.0 * float(np.arcsin(np.clip(float(np.linalg.norm(vetorial)), 0.0, 1.0)))
