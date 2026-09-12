"""Marco 3 completo: controlador amostrado, alocador, atuador e corpo rigido juntos.

Ver vault/06 - Marcos/Experimento 4 - Tolerancia a atraso.md

Dois grupos importam mais que os outros.

O do **alocador com horizonte** verifica que comando nao vira empuxo: o alocador so
pode pedir o que a rampa alcanca em ``Ha``, e a diferenca entre essa caixa e a caixa
fisica e a margem dinamica do ADR-004.

O da **politica de forca** existe por causa de um defeito real. A primeira versao do
controlador pedia a forca que cancela o vetor peso inteiro, que com o tronco inclinado
tem componente lateral; como nesta geometria forca lateral e rolagem sao quase
proporcionais, o controlador de altitude passava a brigar com o de atitude e uma
perturbacao de cinco graus excedia vinte antes de voltar.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, parametric_layout
from hero_atlas.analysis.control_budget import (
    achievable_bandwidth_rad_s,
    moment_budget,
    pure_moment_available_Nm,
)
from hero_atlas.analysis.trim import TrimObjective, solve_trim
from hero_atlas.control.allocator import (
    AllocationStatus,
    allocate,
    characteristic_length_m,
    reachable_box,
)
from hero_atlas.control.attitude import AttitudeGains, HoverController
from hero_atlas.dynamics.quaternion import from_axis_angle
from hero_atlas.dynamics.rigid_body import PlantState, RigidBodyProperties
from hero_atlas.propulsion.actuator import ActuatorEnvelope
from hero_atlas.sim.closed_loop import TerminationMode, simulate
from hero_atlas.units import G0, to_si

pytestmark = pytest.mark.validation

MASSA = 115.0
CG = np.array([0.1575, 0.0, 0.0])
INERCIA = np.diag([32.2, 32.2, 2.3])


def geometria():
    t15 = math.radians(15.0)
    return parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15),
            ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
            ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15),
        ],
        axial=[AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)],
        thrust_max_N=to_si(35.0, "kgf"),
        idle_fraction=0.10,
    )


def envelope(tau_s: float = 0.35, rampa: float = 120.0) -> ActuatorEnvelope:
    return ActuatorEnvelope(
        thrust_min_N=to_si(3.5, "kgf"),
        thrust_max_N=to_si(35.0, "kgf"),
        tau_up_s=tau_s,
        tau_down_s=0.85 * tau_s,
        rate_up_max_N_s=rampa,
        rate_down_max_N_s=1.25 * rampa,
    )


def trim_de_referencia(geo):
    return solve_trim(
        geo, mass_kg=MASSA, center_of_mass_body_m=CG, objective=TrimObjective.MAX_MARGIN
    )


def monta(tau_s: float = 0.35, rampa: float = 120.0, banda: float = 1.05):
    geo = geometria()
    envs = tuple(envelope(tau_s, rampa) for _ in geo.available)
    corpo = RigidBodyProperties(
        mass_kg=MASSA, inertia_about_cg_kg_m2=INERCIA, cg_offset_from_reference_m=CG
    )
    ctrl = HoverController(
        mass_kg=MASSA,
        inertia_kg_m2=INERCIA,
        sample_period_s=0.01,
        center_of_mass_body_m=CG,
        reference_altitude_m=10.0,
        attitude=AttitudeGains(natural_frequency_rad_s=banda, damping_ratio=0.9),
    )
    return geo, envs, corpo, ctrl


def estado(graus: float) -> PlantState:
    return PlantState(
        position_O_I_m=np.array([0.0, 0.0, -10.0]),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=from_axis_angle([1.0, 0.0, 0.0], math.radians(graus)),
        omega_B_rad_s=np.zeros(3),
    )


# ---------------------------------------------------------------------------
# Alocador: comando nao vira empuxo
# ---------------------------------------------------------------------------


def test_caixa_do_horizonte_e_mais_apertada_que_a_fisica() -> None:
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    T0 = trim_de_referencia(geo).thrusts_N
    lo, hi = reachable_box(T0, envs, 0.20)
    assert np.all(lo >= envs[0].thrust_min_N - 1e-9)
    assert np.all(hi <= envs[0].thrust_max_N + 1e-9)
    assert np.all(hi - lo < envs[0].thrust_max_N - envs[0].thrust_min_N)


def test_horizonte_grande_recupera_a_caixa_fisica() -> None:
    """Com horizonte enorme o alocador volta a mentir sobre a velocidade do motor.

    O teste existe para deixar isso explicito, nao para recomendar.
    """
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    T0 = trim_de_referencia(geo).thrusts_N
    lo, hi = reachable_box(T0, envs, 1000.0)
    assert lo == pytest.approx(np.full(len(envs), envs[0].thrust_min_N))
    assert hi == pytest.approx(np.full(len(envs), envs[0].thrust_max_N))


def test_alocador_nunca_comanda_fora_da_caixa_do_horizonte() -> None:
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    T0 = trim_de_referencia(geo).thrusts_N
    lo, hi = reachable_box(T0, envs, 0.20)
    pedido = np.array([0.0, 0.0, -MASSA * G0, 200.0, 0.0, 0.0])
    r = allocate(geo, desired_wrench=pedido, thrust_now_N=T0, envelopes=envs, horizon_s=0.20)
    assert np.all(r.commands_N >= lo - 1e-6)
    assert np.all(r.commands_N <= hi + 1e-6)


def test_pedido_absurdo_e_marcado_inatingivel_e_nao_silenciado() -> None:
    """Com caixa e minimos quadrados quase sempre existe solucao admissivel.

    Ela quase sempre e incapaz de produzir o wrench pedido, e um alocador que so
    devolve o vetor de empuxo esconde exatamente isso.
    """
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    T0 = trim_de_referencia(geo).thrusts_N
    r = allocate(
        geo,
        desired_wrench=np.array([0.0, 0.0, -MASSA * G0, 5000.0, 0.0, 0.0]),
        thrust_now_N=T0,
        envelopes=envs,
        horizon_s=0.20,
    )
    assert r.status is AllocationStatus.WRENCH_UNATTAINABLE
    assert r.normalized_residual > 0.1
    assert r.commands_N.size == len(envs)


def test_comprimento_caracteristico_vem_da_geometria() -> None:
    geo = geometria()
    esperado = max(
        float(np.linalg.norm(n.position_body_m - geo.reference_point_body_m)) for n in geo.available
    )
    assert characteristic_length_m(geo) == pytest.approx(esperado)


def test_encolhimento_do_horizonte_cresce_com_rampa_menor() -> None:
    geo = geometria()
    T0 = trim_de_referencia(geo).thrusts_N
    pedido = np.array([0.0, 0.0, -MASSA * G0, 20.0, 0.0, 0.0])
    encolhimentos = []
    for rampa in (400.0, 120.0, 40.0):
        envs = tuple(envelope(rampa=rampa) for _ in geo.available)
        r = allocate(geo, desired_wrench=pedido, thrust_now_N=T0, envelopes=envs, horizon_s=0.20)
        encolhimentos.append(r.horizon_shrinkage)
    assert encolhimentos == sorted(encolhimentos)


# ---------------------------------------------------------------------------
# Orcamento de momento: as duas margens do ADR-004
# ---------------------------------------------------------------------------


def test_margem_dinamica_e_menor_que_a_estatica() -> None:
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    orc = moment_budget(
        geo, thrust_trim_N=trim_de_referencia(geo).thrusts_N, envelopes=envs, horizon_s=0.20
    )
    assert np.all(orc.horizon_Nm < orc.static_Nm)
    assert np.all(orc.shrinkage > 2.0), "a diferenca entre as duas margens e o achado"


def test_momento_puro_mantem_os_outros_componentes() -> None:
    """Momento puro nao pode vir acompanhado de forca lateral nem de outro momento."""
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    T0 = trim_de_referencia(geo).thrusts_N
    lo = np.array([e.thrust_min_N for e in envs])
    hi = np.array([e.thrust_max_N for e in envs])
    valor = pure_moment_available_Nm(geo, axis=0, thrust_trim_N=T0, lower_N=lo, upper_N=hi)
    assert valor > 0.0


def test_banda_alcancavel_cai_com_erro_maior() -> None:
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    orc = moment_budget(
        geo, thrust_trim_N=trim_de_referencia(geo).thrusts_N, envelopes=envs, horizon_s=0.20
    )
    bandas = [
        achievable_bandwidth_rad_s(orc, inertia_kg_m2=INERCIA, reference_error_rad=math.radians(g))
        for g in (5.0, 10.0, 20.0)
    ]
    assert bandas == sorted(bandas, reverse=True)


def test_banda_do_horizonte_e_menor_que_a_estatica() -> None:
    geo = geometria()
    envs = tuple(envelope() for _ in geo.available)
    orc = moment_budget(
        geo, thrust_trim_N=trim_de_referencia(geo).thrusts_N, envelopes=envs, horizon_s=0.20
    )
    dinamica = achievable_bandwidth_rad_s(
        orc, inertia_kg_m2=INERCIA, reference_error_rad=0.17, use_horizon=True
    )
    estatica = achievable_bandwidth_rad_s(
        orc, inertia_kg_m2=INERCIA, reference_error_rad=0.17, use_horizon=False
    )
    assert dinamica < estatica


# ---------------------------------------------------------------------------
# Laco fechado
# ---------------------------------------------------------------------------


def test_pairado_nivelado_se_mantem() -> None:
    geo, envs, corpo, ctrl = monta()
    r = simulate(
        geo,
        corpo,
        envs,
        ctrl,
        initial_state=estado(0.0),
        initial_thrust_N=trim_de_referencia(geo).thrusts_N,
        t_final_s=6.0,
    )
    assert r.mode is TerminationMode.CAPTURED
    assert r.peak_attitude_error_deg < 0.5
    assert r.max_altitude_loss_m < 0.05


@pytest.mark.parametrize("graus", [5.0, 10.0, 20.0])
def test_recupera_sem_sobressinal_com_forca_so_no_eixo_do_corpo(graus: float) -> None:
    """O pico nao pode passar da perturbacao inicial.

    Este e o teste que prende a correcao da politica de forca. Com o pedido de forca
    cancelando o vetor peso, o pico de uma perturbacao de cinco graus passava de
    vinte, porque forca lateral arrasta momento de rolagem nesta geometria.
    """
    geo, envs, corpo, ctrl = monta()
    r = simulate(
        geo,
        corpo,
        envs,
        ctrl,
        initial_state=estado(graus),
        initial_thrust_N=trim_de_referencia(geo).thrusts_N,
        t_final_s=12.0,
    )
    assert r.mode is TerminationMode.CAPTURED
    assert r.peak_attitude_error_deg <= graus + 0.5


def test_banda_alta_demais_perde_a_atitude() -> None:
    """Pedir banda muito acima da autoridade nao produz voo melhor, produz falha."""
    geo, envs, corpo, ctrl = monta(banda=6.0)
    r = simulate(
        geo,
        corpo,
        envs,
        ctrl,
        initial_state=estado(10.0),
        initial_thrust_N=trim_de_referencia(geo).thrusts_N,
        t_final_s=12.0,
    )
    assert r.mode.is_failure


def test_o_termino_diz_qual_falha_e_nao_apenas_instavel() -> None:
    modos = {m for m in TerminationMode}
    assert TerminationMode.ATTITUDE_LIMIT_EXCEEDED in modos
    assert TerminationMode.ALTITUDE_LOSS_LIMIT in modos
    assert TerminationMode.WRENCH_UNATTAINABLE in modos
    assert not TerminationMode.CAPTURED.is_failure
    assert not TerminationMode.HORIZON_REACHED.is_failure
    assert TerminationMode.NUMERICAL_FAILURE.is_failure


def test_atraso_menor_que_o_passo_e_recusado() -> None:
    geo, envs, corpo, ctrl = monta()
    with pytest.raises(ValueError, match="menor que o passo"):
        simulate(
            geo,
            corpo,
            envs,
            ctrl,
            initial_state=estado(0.0),
            initial_thrust_N=trim_de_referencia(geo).thrusts_N,
            t_final_s=1.0,
            transport_delay_s=0.001,
            max_step_s=0.002,
        )


def test_numero_de_envelopes_precisa_casar() -> None:
    geo, envs, corpo, ctrl = monta()
    with pytest.raises(ValueError, match="envelopes"):
        simulate(
            geo,
            corpo,
            envs[:-1],
            ctrl,
            initial_state=estado(0.0),
            initial_thrust_N=trim_de_referencia(geo).thrusts_N,
            t_final_s=1.0,
        )


def test_atuador_lento_demais_perde_a_captura() -> None:
    """A fronteira existe: com constante de tempo grande e atraso grande, falha."""
    geo, envs, corpo, ctrl = monta(tau_s=1.8)
    r = simulate(
        geo,
        corpo,
        envs,
        ctrl,
        initial_state=estado(10.0),
        initial_thrust_N=trim_de_referencia(geo).thrusts_N,
        t_final_s=12.0,
        transport_delay_s=0.30,
    )
    assert r.mode is not TerminationMode.CAPTURED


def test_empuxo_nunca_sai_da_faixa_fisica() -> None:
    geo, envs, corpo, ctrl = monta()
    r = simulate(
        geo,
        corpo,
        envs,
        ctrl,
        initial_state=estado(20.0),
        initial_thrust_N=trim_de_referencia(geo).thrusts_N,
        t_final_s=8.0,
    )
    assert r.thrusts_N.size
    assert np.all(r.thrusts_N >= envs[0].thrust_min_N - 1e-6)
    assert np.all(r.thrusts_N <= envs[0].thrust_max_N + 1e-6)
