"""Marco 1 estendido: energia por missao, eletrico contra combustivel.

Ver vault/04 - Fisica/Autonomia e energia.md

O teste central deste arquivo e
:func:`test_pairado_com_combustivel_reproduz_a_forma_fechada`: a integracao numerica
da missao tem que devolver o mesmo numero que
:func:`hero_atlas.analysis.energy.turbine_endurance_s`, que e solucao analitica da
mesma equacao. Duas rotas independentes chegando ao mesmo valor e o que separa um
integrador correto de um integrador plausivel.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, parametric_layout
from hero_atlas.analysis.energy import turbine_endurance_s
from hero_atlas.analysis.mission_energy import (
    BatteryStorage,
    FuelStorage,
    GeometricThrustDemand,
    MissionPhase,
    MissionProfile,
    ScalarThrustDemand,
    TerminationReason,
    evaluate_mission_energy,
)
from hero_atlas.analysis.trim import TrimObjective
from hero_atlas.units import G0, to_si

pytestmark = pytest.mark.validation

TSFC_SI = to_si(1.54, "kg/(kgf*h)")
"""Consumo especifico plausivel de microturbina pequena. ⚠ Catalogo, sem hash."""

FONTE = "hipotese de trabalho, nao medida"


def missao_pairado(reserva: float = 0.20) -> MissionProfile:
    """Missao de uma fase so: pairar ate a reserva. Comparavel com a forma fechada."""
    return MissionProfile(
        phases=(MissionPhase("pairado", duration_s=None),), reserve_fraction=reserva
    )


def geometria_sobrevivente():
    """A unica das onze variantes com posto 6 e rolagem pura. Ver experimento 1."""
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


# ---------------------------------------------------------------------------
# A verificacao central: numerico contra forma fechada
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("inclinacao_graus", [0.0, 15.0, 25.0, 40.0])
@pytest.mark.parametrize("reserva", [0.0, 0.20, 0.35])
def test_pairado_com_combustivel_reproduz_a_forma_fechada(
    inclinacao_graus: float, reserva: float
) -> None:
    """Integracao de Runge-Kutta contra ``t = ln(m0/(m0-fuel))/k``.

    As duas rotas nao compartilham algebra: uma integra passo a passo, a outra sai da
    solucao da equacao diferencial. Se divergirem, uma esta errada.
    """
    seco, combustivel = 95.0, 22.0
    inclinacao = math.radians(inclinacao_graus)

    resultado = evaluate_mission_energy(
        dry_mass_kg=seco,
        storage=FuelStorage(mass_kg=combustivel, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
        demand=ScalarThrustDemand(projection_ratio=math.cos(inclinacao), nozzle_count=7),
        profile=missao_pairado(reserva),
        step_s=0.25,
    )

    fechada = turbine_endurance_s(
        gross_kg=seco + combustivel,
        usable_fuel_kg=(1.0 - reserva) * combustivel,
        tsfc_kg_per_N_s=TSFC_SI,
        nozzle_tilt_rad=inclinacao,
    )

    assert resultado.termination_reason is TerminationReason.RESERVE_REACHED
    assert resultado.hover_endurance_s == pytest.approx(fechada.endurance_s, rel=2e-3)


def test_convergencia_com_o_passo() -> None:
    """Halving do passo aproxima a forma fechada, como Runge-Kutta deve."""
    seco, combustivel = 95.0, 22.0
    fechada = turbine_endurance_s(
        gross_kg=seco + combustivel,
        usable_fuel_kg=0.8 * combustivel,
        tsfc_kg_per_N_s=TSFC_SI,
    ).endurance_s

    erros = []
    for passo in (4.0, 2.0, 1.0):
        r = evaluate_mission_energy(
            dry_mass_kg=seco,
            storage=FuelStorage(mass_kg=combustivel, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
            demand=ScalarThrustDemand(projection_ratio=1.0),
            profile=missao_pairado(0.20),
            step_s=passo,
        )
        erros.append(abs(r.hover_endurance_s - fechada))
    assert erros[0] >= erros[1] >= erros[2]


def test_potencia_eletrica_constante_tem_solucao_fechada() -> None:
    """Massa constante implica potencia constante, e autonomia vira divisao simples."""
    seco, bateria = 95.0, 22.0
    armazenamento = BatteryStorage(mass_kg=bateria, source=FONTE, auxiliary_power_W=0.0)
    demanda = ScalarThrustDemand(projection_ratio=1.0, nozzle_count=7)

    r = evaluate_mission_energy(
        dry_mass_kg=seco,
        storage=armazenamento,
        demand=demanda,
        profile=missao_pairado(0.0),
        step_s=0.25,
    )
    pedido = demanda(seco + bateria, 0.0)
    potencia = armazenamento.power_W(pedido.thrusts_N, 1.225)
    esperado = armazenamento.usable_energy_J / potencia
    assert r.hover_endurance_s == pytest.approx(esperado, rel=2e-3)


# ---------------------------------------------------------------------------
# As duas assimetrias fisicas
# ---------------------------------------------------------------------------


def test_combustivel_perde_massa_e_eletrico_nao() -> None:
    seco, energia = 95.0, 20.0
    combustivel = evaluate_mission_energy(
        dry_mass_kg=seco,
        storage=FuelStorage(mass_kg=energia, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
        demand=ScalarThrustDemand(projection_ratio=1.0),
        profile=missao_pairado(0.20),
    )
    eletrico = evaluate_mission_energy(
        dry_mass_kg=seco,
        storage=BatteryStorage(mass_kg=energia, source=FONTE),
        demand=ScalarThrustDemand(projection_ratio=1.0, nozzle_count=7),
        profile=missao_pairado(0.20),
    )
    assert combustivel.final_gross_kg < combustivel.initial_gross_kg
    assert eletrico.final_gross_kg == pytest.approx(eletrico.initial_gross_kg)


def test_fluxo_de_combustivel_cai_durante_a_missao() -> None:
    """A realimentacao favoravel: menos massa, menos empuxo, menos fluxo."""
    seco, combustivel = 95.0, 25.0
    armazenamento = FuelStorage(mass_kg=combustivel, source=FONTE, tsfc_kg_per_N_s=TSFC_SI)
    demanda = ScalarThrustDemand(projection_ratio=1.0)

    inicial = armazenamento.mass_flow_kg_s(demanda(seco + combustivel, 0.0).thrusts_N)
    final = armazenamento.mass_flow_kg_s(demanda(seco + 0.2 * combustivel, 0.0).thrusts_N)
    assert final < inicial

    r = evaluate_mission_energy(
        dry_mass_kg=seco,
        storage=armazenamento,
        demand=demanda,
        profile=missao_pairado(0.20),
    )
    assert r.peak_fuel_flow_kg_s == pytest.approx(inicial, rel=1e-9)


def test_mais_bateria_aumenta_energia_e_tambem_a_potencia_exigida() -> None:
    seco = 95.0
    potencias = []
    for massa in (10.0, 40.0, 120.0):
        armazenamento = BatteryStorage(mass_kg=massa, source=FONTE)
        demanda = ScalarThrustDemand(projection_ratio=1.0, nozzle_count=7)
        pedido = demanda(seco + massa, 0.0)
        potencias.append(armazenamento.power_W(pedido.thrusts_N, 1.225))
    assert potencias == sorted(potencias)


# ---------------------------------------------------------------------------
# Trim como porteiro: sem equilibrio nao ha autonomia
# ---------------------------------------------------------------------------


def test_trim_inviavel_encerra_antes_de_integrar_energia() -> None:
    """Massa alem do que a geometria equilibra: autonomia nao existe, nao e zero."""
    geo = geometria_sobrevivente()
    r = evaluate_mission_energy(
        dry_mass_kg=900.0,
        storage=FuelStorage(mass_kg=20.0, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
        demand=GeometricThrustDemand(geo, center_of_mass_body_m=[0.1575, 0.0, 0.0]),
        profile=missao_pairado(0.20),
        geometry=geo,
    )
    assert r.termination_reason is TerminationReason.TRIM_INFEASIBLE
    assert r.hover_endurance_s == 0.0
    assert not r.mission_completed


def test_missao_com_geometria_real_fecha_e_registra_margem() -> None:
    geo = geometria_sobrevivente()
    r = evaluate_mission_energy(
        dry_mass_kg=95.0,
        storage=FuelStorage(mass_kg=22.0, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
        demand=GeometricThrustDemand(
            geo, center_of_mass_body_m=[0.1575, 0.0, 0.0], objective=TrimObjective.MAX_MARGIN
        ),
        profile=missao_pairado(0.20),
        geometry=geo,
        step_s=1.0,
    )
    assert r.termination_reason is TerminationReason.RESERVE_REACHED
    assert r.hover_endurance_s > 60.0
    assert 0.0 < r.minimum_thrust_margin_ratio < 1.0


def test_trim_de_menor_consumo_gasta_toda_a_margem_de_controle() -> None:
    """O conflito que a missao expoe, e que nenhuma das duas analises via sozinha.

    Minimizar empuxo total minimiza consumo, que e o objetivo certo para autonomia.
    Mas a solucao de menor empuxo **encosta um par no teto**, entao a margem de
    controle vai a zero exatamente. Maximizar margem preserva autoridade e gasta mais.

    Autonomia e autoridade puxam para lados opostos, e a escolha entre as duas e de
    projeto, nao de solver. O numero aqui diz **quanto** custa a margem.
    """
    geo = geometria_sobrevivente()
    centro = [0.1575, 0.0, 0.0]

    resultados = {}
    for objetivo in (TrimObjective.MIN_THRUST, TrimObjective.MAX_MARGIN):
        resultados[objetivo] = evaluate_mission_energy(
            dry_mass_kg=95.0,
            storage=FuelStorage(mass_kg=22.0, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
            demand=GeometricThrustDemand(geo, center_of_mass_body_m=centro, objective=objetivo),
            profile=missao_pairado(0.20),
            geometry=geo,
            step_s=1.0,
        )

    menor_consumo = resultados[TrimObjective.MIN_THRUST]
    maior_margem = resultados[TrimObjective.MAX_MARGIN]

    assert menor_consumo.minimum_thrust_margin_ratio == pytest.approx(0.0, abs=1e-9)
    assert maior_margem.minimum_thrust_margin_ratio > 0.10
    assert menor_consumo.hover_endurance_s >= maior_margem.hover_endurance_s


def test_aceleracao_vertical_entra_como_gravidade_efetiva() -> None:
    """Aceleracao escala massa equivalente, preservando o momento do peso."""
    demanda = ScalarThrustDemand(projection_ratio=1.0)
    parado = demanda(117.0, 0.0).total_N
    subindo = demanda(117.0, 0.5).total_N
    assert subindo / parado == pytest.approx((G0 + 0.5) / G0)


def test_velocidade_vertical_constante_nao_cobra_empuxo_extra() -> None:
    """Regime permanente tem aceleracao nula. Empuxo de subida e o de pairado.

    Este teste existe porque tratar subida a velocidade constante como se exigisse
    empuxo proporcional a velocidade e um erro comum e silencioso.
    """
    demanda = ScalarThrustDemand(projection_ratio=1.0)
    parado = demanda(117.0, 0.0).total_N
    fase = MissionPhase("subida", duration_s=10.0, vertical_speed_m_s=3.0)
    assert demanda(117.0, fase.vertical_acceleration_m_s2).total_N == pytest.approx(parado)


# ---------------------------------------------------------------------------
# Custo de sair do chao, separado do custo de ficar no ar
# ---------------------------------------------------------------------------


def test_sair_do_chao_custa_pouco_perto_de_ficar_no_ar() -> None:
    """A separacao que o modulo existe para fazer.

    Tres segundos acelerando custam uma fracao pequena do que custam os minutos de
    pairado. Fundir as duas perguntas produz numero de decolagem inflado.
    """
    perfil = MissionProfile(
        phases=(
            MissionPhase("saida_do_chao", duration_s=3.0, vertical_acceleration_m_s2=0.5),
            MissionPhase("pairado", duration_s=None),
        ),
        reserve_fraction=0.20,
    )
    r = evaluate_mission_energy(
        dry_mass_kg=95.0,
        storage=FuelStorage(mass_kg=22.0, source=FONTE, tsfc_kg_per_N_s=TSFC_SI),
        demand=ScalarThrustDemand(projection_ratio=1.0),
        profile=perfil,
        step_s=0.25,
    )
    total_gasto = 22.0 * 0.8
    assert r.takeoff_storage_used_kg > 0.0
    assert r.takeoff_storage_used_kg / total_gasto < 0.10


# ---------------------------------------------------------------------------
# Contratos e recusas
# ---------------------------------------------------------------------------


def test_armazenamento_sem_procedencia_e_recusado() -> None:
    with pytest.raises(ValueError, match="procedencia"):
        BatteryStorage(mass_kg=20.0, source="   ")
    with pytest.raises(ValueError, match="procedencia"):
        FuelStorage(mass_kg=20.0, source="", tsfc_kg_per_N_s=TSFC_SI)


def test_queda_livre_e_recusada_como_fase() -> None:
    with pytest.raises(ValueError, match="[Qq]ueda livre"):
        MissionPhase("queda", duration_s=1.0, vertical_acceleration_m_s2=-G0)


def test_duas_fases_abertas_sao_recusadas() -> None:
    with pytest.raises(ValueError, match="mais de uma fase aberta"):
        MissionProfile(
            phases=(
                MissionPhase("a", duration_s=None),
                MissionPhase("b", duration_s=None),
            )
        )


def test_potencia_somada_por_rotor_supera_a_forma_agregada() -> None:
    """Potencia induzida e convexa: distribuicao desigual custa mais, nunca menos.

    Usar ``(soma T)^1.5 / sqrt(2 rho A_total)`` subestima sempre que o trim distribui
    desigual, e o trim real distribui desigual.
    """
    armazenamento = BatteryStorage(mass_kg=30.0, source=FONTE, auxiliary_power_W=0.0)
    iguais = np.full(4, 250.0)
    desiguais = np.array([100.0, 150.0, 350.0, 400.0])
    assert desiguais.sum() == pytest.approx(iguais.sum())
    assert armazenamento.power_W(desiguais, 1.225) > armazenamento.power_W(iguais, 1.225)
