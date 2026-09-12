"""Marco 1: autonomia de turbina e de eletrico.

Ver vault/04 - Fisica/Autonomia e energia.md

O resultado mais interessante do estudo esta aqui: as duas tecnologias obedecem leis
diferentes. Turbina depende do consumo especifico e da massa que cai queimando.
Eletrico depende de area de disco **e** de massa de bateria ao mesmo tempo, com
maximo interior em bateria: ver :func:`optimal_battery_mass_kg`.

⚠ Uma versao anterior deste arquivo dizia "depende da area, nao da bateria". Era
falso. O teste :func:`test_otimo_de_bateria_bate_com_maximizacao_numerica` existe
para que a afirmacao correta fique presa a um numero.
"""

from __future__ import annotations

import math

import pytest

from hero_atlas.analysis.energy import (
    disk_area_for_endurance_m2,
    disk_area_from_rotors_m2,
    electric_endurance_s,
    electrical_hover_power_W,
    ideal_hover_power_W,
    induced_velocity_m_s,
    max_electric_endurance_s,
    optimal_battery_mass_kg,
    power_per_newton_W_N,
    turbine_endurance_s,
)
from hero_atlas.units import G0, RHO_SEA_LEVEL_ISA, to_si

pytestmark = pytest.mark.validation

TSFC_JETCAT_SI = to_si(1.54, "kg/(kgf*h)")
"""Consumo especifico da JetCat P400 Pro, derivado do catalogo: 1,04 kg/min p/ 40,5 kgf."""


# --------------------------------------------------------------------------- #
# Teoria do disco atuador, com solucao fechada
# --------------------------------------------------------------------------- #


def test_velocidade_induzida_confere_com_a_formula():
    """v_i = sqrt( T / (2*rho*A) ), verificada com aritmetica independente."""
    area = disk_area_from_rotors_m2(diameter_m=0.90, count=2)
    empuxo = 120.0 * G0

    v = induced_velocity_m_s(empuxo, area)

    esperado = math.sqrt(empuxo / (2.0 * RHO_SEA_LEVEL_ISA * area))
    assert v == pytest.approx(esperado)
    assert v == pytest.approx(19.4, abs=0.2)


def test_area_de_dois_rotores_de_90_cm():
    area = disk_area_from_rotors_m2(diameter_m=0.90, count=2)
    assert area == pytest.approx(2 * math.pi * 0.45**2)
    assert area == pytest.approx(1.272, abs=0.002)


def test_potencia_eletrica_de_mochila_com_dois_rotores():
    """Cerca de 37 kW para sustentar 120 kg com 1,27 m2 de disco."""
    area = disk_area_from_rotors_m2(diameter_m=0.90, count=2)

    potencia = electrical_hover_power_W(120.0 * G0, area)

    assert potencia / 1000.0 == pytest.approx(37.1, abs=0.5)


def test_potencia_ideal_e_menor_que_a_eletrica():
    """As duas ineficiencias, figura de merito e motor, so aumentam a conta."""
    area = disk_area_from_rotors_m2(diameter_m=0.90, count=2)
    empuxo = 120.0 * G0

    ideal = ideal_hover_power_W(empuxo, area)
    eletrica = electrical_hover_power_W(empuxo, area)

    assert eletrica > ideal
    assert eletrica == pytest.approx(ideal / (0.70 * 0.88))


# --------------------------------------------------------------------------- #
# A lei que decide o conceito eletrico
# --------------------------------------------------------------------------- #


def test_potencia_por_newton_depende_so_da_carga_de_disco():
    """O empuxo sai da conta. Sobra a carga de disco sob raiz quadrada.

    E por isso que autonomia eletrica e funcao da envergadura, nao da bateria.
    """
    carga = 800.0
    p_por_n = power_per_newton_W_N(carga)

    # mesma carga de disco, empuxos e areas diferentes: mesma potencia por newton
    for empuxo in (500.0, 5000.0, 50000.0):
        area = empuxo / carga
        assert electrical_hover_power_W(empuxo, area) / empuxo == pytest.approx(p_por_n)


def test_dobrar_a_area_reduz_a_potencia_por_raiz_de_dois():
    """P/T proporcional a sqrt(L). Metade da carga de disco, 1/sqrt(2) da potencia."""
    empuxo = 1200.0
    area = 1.5

    p1 = electrical_hover_power_W(empuxo, area)
    p2 = electrical_hover_power_W(empuxo, 2 * area)

    assert p2 / p1 == pytest.approx(1.0 / math.sqrt(2.0), rel=1e-9)


def test_autonomia_eletrica_cresce_com_a_area_do_disco():
    """A tabela do vault: mesma massa e bateria, area diferente, autonomia diferente.

    Nao existe "mochila eletrica de 30 minutos". Existe "aeronave de 3 m de diametro
    de 30 minutos".
    """
    autonomias = [
        electric_endurance_s(gross_kg=100.0, disk_area_m2=area, battery_kg=30.0) / 60.0
        for area in (0.5, 1.3, 3.0, 6.0, 12.0)
    ]

    assert autonomias == sorted(autonomias), "mais area, mais autonomia"
    assert autonomias[0] == pytest.approx(6.1, abs=0.3)
    assert autonomias[-1] == pytest.approx(30.0, abs=1.0)


def test_retorno_decrescente_brutal_da_bateria():
    """Triplicar a bateria nao triplica a autonomia: cada quilo carrega a si mesmo.

    Do vault: de 15 kg para 50 kg de bateria, a autonomia vai de 3,7 para 8,4 min.
    Pouco mais que o dobro para mais que o triplo de bateria.
    """
    area = disk_area_from_rotors_m2(diameter_m=0.90, count=2)
    seca = 105.0  # piloto mais estrutura

    def autonomia(bateria_kg: float) -> float:
        return (
            electric_endurance_s(
                gross_kg=seca + bateria_kg, disk_area_m2=area, battery_kg=bateria_kg
            )
            / 60.0
        )

    t15, t50 = autonomia(15.0), autonomia(50.0)

    assert t15 == pytest.approx(3.7, abs=0.2)
    assert t50 == pytest.approx(8.4, abs=0.3)
    assert t50 / t15 < 3.0, "o ganho tem que ser sublinear no peso de bateria"


def test_mochila_eletrica_fica_entre_quatro_e_oito_minutos():
    """A conclusao de viabilidade do conceito eletrico vestivel."""
    area = disk_area_from_rotors_m2(diameter_m=0.90, count=2)

    for bateria in (15.0, 25.0, 35.0, 50.0):
        minutos = (
            electric_endurance_s(gross_kg=105.0 + bateria, disk_area_m2=area, battery_kg=bateria)
            / 60.0
        )
        assert 3.5 <= minutos <= 8.6, f"{bateria} kg deu {minutos:.1f} min"


# --------------------------------------------------------------------------- #
# Turbina: integrada, porque a massa cai
# --------------------------------------------------------------------------- #


def test_integrar_da_mais_autonomia_que_taxa_constante():
    """A massa cai enquanto queima, entao o empuxo de pairado cai junto.

    Estimar pela taxa inicial constante **subestima** a autonomia.
    """
    r = turbine_endurance_s(
        gross_kg=121.0,
        usable_fuel_kg=16.0,
        tsfc_kg_per_N_s=TSFC_JETCAT_SI,
        nozzle_tilt_rad=math.radians(25.0),
    )

    assert r.endurance_s > r.endurance_constant_rate_s
    assert r.integration_gain > 1.0
    assert r.final_flow_kg_s < r.initial_flow_kg_s


def test_autonomia_de_turbina_na_ordem_de_grandeza_reportada():
    """⚠ Coerencia, nao validacao.

    O consumo especifico de catalogo e medido perto do maximo, e em pairado a fracao
    de empuxo e outra. A banda real exige a familia de curvas de carga parcial do
    deck, que nao existe.
    """
    r = turbine_endurance_s(
        gross_kg=121.0,
        usable_fuel_kg=16.0,
        tsfc_kg_per_N_s=TSFC_JETCAT_SI,
        nozzle_tilt_rad=math.radians(25.0),
    )

    assert 3.5 <= r.endurance_min <= 5.5


def test_mais_combustivel_da_mais_autonomia_mas_sublinear():
    """Combustivel tambem carrega a si mesmo, so que menos que bateria."""

    def autonomia(fuel_kg: float) -> float:
        return turbine_endurance_s(
            gross_kg=105.0 + fuel_kg,
            usable_fuel_kg=fuel_kg,
            tsfc_kg_per_N_s=TSFC_JETCAT_SI,
            nozzle_tilt_rad=math.radians(25.0),
        ).endurance_min

    t8, t16 = autonomia(8.0), autonomia(16.0)

    assert t16 > t8
    assert t16 / t8 < 2.0


def test_inclinacao_do_bocal_encurta_a_autonomia():
    """Cosseno cobra em empuxo, e empuxo cobra em combustivel."""
    reto = turbine_endurance_s(gross_kg=121.0, usable_fuel_kg=16.0, tsfc_kg_per_N_s=TSFC_JETCAT_SI)
    inclinado = turbine_endurance_s(
        gross_kg=121.0,
        usable_fuel_kg=16.0,
        tsfc_kg_per_N_s=TSFC_JETCAT_SI,
        nozzle_tilt_rad=math.radians(25.0),
    )

    assert inclinado.endurance_s < reto.endurance_s


def test_consumo_especifico_precisa_estar_em_si():
    """⚠ A forma mdot = TSFC * T so fecha com as unidades casadas.

    Passar o valor de catalogo sem converter daria uma autonomia absurda, e este
    teste fixa a ordem de grandeza da conversao.
    """
    assert pytest.approx(1.54 / (G0 * 3600.0)) == TSFC_JETCAT_SI
    assert TSFC_JETCAT_SI < 1e-4


# --------------------------------------------------------------------------- #
# A comparacao que explica o conceito inteiro
# --------------------------------------------------------------------------- #


def test_turbina_gasta_muito_mais_potencia_por_newton_que_rotor():
    """Cerca de 294 W/N no bocal de turbina contra cerca de 12 W/N num rotor grande.

    P/T = v_jato/2 para jato, e v_induzida para rotor.
    """
    velocidade_jato = 589.0  # m/s, catalogo JetCat P400 Pro
    turbina_w_por_n = velocidade_jato / 2.0

    jetson_area = 5.7  # m2, ordem de grandeza de oito rotores grandes
    rotor_w_por_n = power_per_newton_W_N(
        (210.0 * G0) / jetson_area, figure_of_merit=1.0, motor_efficiency=1.0
    )

    assert turbina_w_por_n == pytest.approx(294.5, abs=1.0)
    assert rotor_w_por_n < 20.0
    assert turbina_w_por_n / rotor_w_por_n > 20.0


# ---------------------------------------------------------------------------
# Otimo de bateria: a correcao da afirmacao "area, nao bateria"
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("massa_seca_kg", [40.0, 80.0, 117.0, 250.0])
def test_otimo_de_bateria_bate_com_maximizacao_numerica(massa_seca_kg: float) -> None:
    """A forma fechada ``m_b = 2*m_seco`` e realmente o maximo, nao um chute.

    Varre a massa de bateria e confere que o otimo analitico vence toda a grade.
    """
    area = 0.55
    otimo_analitico = optimal_battery_mass_kg(massa_seca_kg)
    assert otimo_analitico == pytest.approx(2.0 * massa_seca_kg)

    melhor_numerico = max(
        (b for b in [0.05 * massa_seca_kg * k for k in range(1, 120)]),
        key=lambda b: electric_endurance_s(
            gross_kg=massa_seca_kg + b, disk_area_m2=area, battery_kg=b
        ),
    )
    assert melhor_numerico == pytest.approx(otimo_analitico, rel=0.05)

    t_otimo = electric_endurance_s(
        gross_kg=massa_seca_kg + otimo_analitico, disk_area_m2=area, battery_kg=otimo_analitico
    )
    for fator in (0.4, 0.7, 1.4, 2.5, 5.0):
        b = fator * otimo_analitico
        t = electric_endurance_s(gross_kg=massa_seca_kg + b, disk_area_m2=area, battery_kg=b)
        assert t <= t_otimo + 1e-9, f"fator {fator} superou o otimo analitico"


def test_otimo_de_bateria_nao_depende_de_area_nem_de_eficiencia() -> None:
    """Area, densidade e rendimentos mudam **quanto**, nunca **onde** esta o otimo.

    Todos entram na constante multiplicativa da autonomia, que nao move o ponto de
    maximo. E por isso que o resultado pode ser afirmado sem escolher rotor.
    """
    massa_seca = 90.0
    esperado = optimal_battery_mass_kg(massa_seca)
    for area, fm, eta, wh in [(0.2, 0.6, 0.85, 150.0), (4.0, 0.8, 0.95, 300.0)]:
        melhor = max(
            (0.05 * massa_seca * k for k in range(1, 120)),
            key=lambda b: electric_endurance_s(
                gross_kg=massa_seca + b,
                disk_area_m2=area,
                battery_kg=b,
                pack_specific_energy_Wh_kg=wh,
                figure_of_merit=fm,
                motor_efficiency=eta,
            ),
        )
        assert melhor == pytest.approx(esperado, rel=0.05)


def test_no_otimo_a_bateria_e_dois_tercos_da_massa_bruta() -> None:
    otimo = max_electric_endurance_s(dry_mass_kg=100.0, disk_area_m2=1.0)
    assert otimo.battery_kg == pytest.approx(200.0)
    assert otimo.gross_kg == pytest.approx(300.0)
    assert otimo.battery_mass_fraction == pytest.approx(2.0 / 3.0)


def test_area_para_autonomia_inverte_a_autonomia_no_otimo() -> None:
    """A inversa fecha o ciclo: area -> autonomia -> area devolve a mesma area."""
    for area in (0.2, 0.55, 2.0, 8.0):
        otimo = max_electric_endurance_s(dry_mass_kg=85.0, disk_area_m2=area)
        de_volta = disk_area_for_endurance_m2(
            dry_mass_kg=85.0, target_endurance_s=otimo.endurance_s
        )
        assert de_volta == pytest.approx(area, rel=1e-12)


def test_area_cresce_com_o_quadrado_da_autonomia() -> None:
    """Dobrar o tempo de voo exige **quadruplicar** a area, nao dobrar.

    E o numero que mata a mochila eletrica: area e geometria do veiculo, nao um
    componente que se compra maior.
    """
    a1 = disk_area_for_endurance_m2(dry_mass_kg=85.0, target_endurance_s=300.0)
    a2 = disk_area_for_endurance_m2(dry_mass_kg=85.0, target_endurance_s=600.0)
    assert a2 / a1 == pytest.approx(4.0, rel=1e-12)


def test_autonomia_cai_depois_do_otimo() -> None:
    """Passado o otimo, mais bateria **reduz** a autonomia. O maximo e interior."""
    seco = 80.0
    otimo = optimal_battery_mass_kg(seco)
    antes = electric_endurance_s(
        gross_kg=seco + 0.5 * otimo, disk_area_m2=0.6, battery_kg=0.5 * otimo
    )
    pico = electric_endurance_s(gross_kg=seco + otimo, disk_area_m2=0.6, battery_kg=otimo)
    depois = electric_endurance_s(
        gross_kg=seco + 4.0 * otimo, disk_area_m2=0.6, battery_kg=4.0 * otimo
    )
    assert antes < pico
    assert depois < pico


@pytest.mark.parametrize("valor", [0.0, -1.0, float("nan"), float("inf")])
def test_massa_seca_invalida_e_recusada(valor: float) -> None:
    with pytest.raises(ValueError):
        optimal_battery_mass_kg(valor)
