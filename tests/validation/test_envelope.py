"""Marco 1: envelope de massa e empuxo, e autonomia.

Ver vault/06 - Marcos/Marco 1 - Envelope.md

O criterio de calibracao do marco esta fixado desde o plano: piloto de 80 kg, traje
de 25 kg e combustivel de 12 kg tem que devolver **142,0 kgf de exigencia fisica de
empuxo efetivo**.

⚠ As comparacoes com trajes reais neste arquivo sao **coerencia de ordem de
grandeza**, nao validacao. Nenhuma fonte esta arquivada com hash, e o consumo
especifico de catalogo e medido perto do maximo, nao em pairado.
Ver vault/08 - Dados/Nivel de evidencia.md
"""

from __future__ import annotations

import math

import pytest

from hero_atlas.analysis.envelope import (
    InstallationLosses,
    MassBudget,
    mass_closure,
    reference_thrust_needed_N,
    solve_envelope,
    thrust_effective_available_N,
    thrust_effective_required_N,
)
from hero_atlas.environment.atmosphere import SCENARIOS, Scenario, isa
from hero_atlas.units import G0, to_si

pytestmark = pytest.mark.validation

TILT_25 = math.radians(25.0)


def orcamento_referencia() -> MassBudget:
    """O caso de calibracao do marco 1."""
    return MassBudget(pilot_kg=80.0, structure_kg=25.0, engines_kg=0.0, consumable_kg=12.0)


# --------------------------------------------------------------------------- #
# Calibracao do marco
# --------------------------------------------------------------------------- #


def test_calibracao_do_marco_1_da_142_kgf():
    """O numero fixado no plano antes da primeira linha de codigo."""
    massa = orcamento_referencia()
    assert massa.gross_kg == pytest.approx(117.0)

    requerido = thrust_effective_required_N(massa.gross_kg, nozzle_tilt_rad=TILT_25)

    assert requerido / G0 == pytest.approx(142.0, abs=0.1)


def test_a_cadeia_de_fatores_confere_passo_a_passo():
    """Peso, cosseno, reserva. Cada etapa verificavel isolada."""
    massa = orcamento_referencia()

    peso_kgf = massa.weight_N / G0
    com_cosseno = peso_kgf / math.cos(TILT_25)
    com_reserva = com_cosseno * 1.10

    assert peso_kgf == pytest.approx(117.0, abs=0.05)
    assert com_cosseno == pytest.approx(129.1, abs=0.1)
    assert com_reserva == pytest.approx(142.0, abs=0.1)


# --------------------------------------------------------------------------- #
# A separacao arquitetural: atmosfera nao muda o requisito
# --------------------------------------------------------------------------- #


def test_requisito_nao_depende_da_atmosfera():
    """⚠ O ponto arquitetural do modulo inteiro.

    A atmosfera **nao** faz o traje precisar de mais forca para equilibrar o peso.
    Se este teste falhar, alguem reintroduziu a divisao pelo fator ambiental no
    lugar errado.
    """
    massa = orcamento_referencia()
    requerido = thrust_effective_required_N(massa.gross_kg, nozzle_tilt_rad=TILT_25)

    # a funcao nem aceita atmosfera como argumento; o teste fixa o valor
    for cenario in Scenario:
        atm = SCENARIOS[cenario]
        disponivel = thrust_effective_available_N(
            requerido, atmosphere=atm, losses=InstallationLosses()
        )
        # o requisito e o mesmo; o que muda e a entrega
        assert thrust_effective_required_N(
            massa.gross_kg, nozzle_tilt_rad=TILT_25
        ) == pytest.approx(requerido)
        if cenario is not Scenario.REFERENCE:
            assert disponivel < requerido


def test_a_entrega_cai_com_a_altitude_e_o_calor():
    requerido = thrust_effective_required_N(117.0, nozzle_tilt_rad=TILT_25)
    sem_perdas = InstallationLosses()

    entregas = [
        thrust_effective_available_N(requerido, atmosphere=SCENARIOS[c], losses=sem_perdas)
        for c in (
            Scenario.REFERENCE,
            Scenario.MISSION_NOMINAL,
            Scenario.HOT_DAY,
            Scenario.ADVERSE,
        )
    ]

    assert entregas == sorted(entregas, reverse=True), "entrega deveria cair monotonicamente"


def test_capacidade_nominal_necessaria_por_cenario():
    """A pergunta de dimensionamento: quanto instalar em referencia."""
    requerido = thrust_effective_required_N(117.0, nozzle_tilt_rad=TILT_25)
    sem_perdas = InstallationLosses()

    nominal = reference_thrust_needed_N(
        requerido, atmosphere=SCENARIOS[Scenario.MISSION_NOMINAL], losses=sem_perdas
    )
    quente = reference_thrust_needed_N(
        requerido, atmosphere=SCENARIOS[Scenario.HOT_DAY], losses=sem_perdas
    )

    assert nominal / G0 == pytest.approx(156.5, abs=0.5)
    assert quente / G0 == pytest.approx(164.8, abs=0.5)
    assert quente > nominal


def test_perda_de_instalacao_multiplica_sem_dupla_contagem():
    """Instalacao e interacao entram na entrega, nunca no requisito."""
    perdas = InstallationLosses(installation=0.95, interaction=0.97, thermal_residual=0.96)

    assert perdas.combined == pytest.approx(0.95 * 0.97 * 0.96)

    entrega = thrust_effective_available_N(1000.0, atmosphere=isa(), losses=perdas)
    assert entrega == pytest.approx(1000.0 * perdas.combined)


# --------------------------------------------------------------------------- #
# Envelope completo e T/W
# --------------------------------------------------------------------------- #


def test_envelope_gravity_reproduz_a_ordem_de_grandeza():
    """Cerca de 144 kgf para cerca de 121 kg: T/W bruto perto de 1,19.

    ⚠ Coerencia, nao validacao. O modelo de turbina da Gravity nunca foi divulgado.
    """
    massa = MassBudget(pilot_kg=80.0, structure_kg=25.0, engines_kg=0.0, consumable_kg=16.0)
    envelope = solve_envelope(
        massa,
        reference_thrust_installed_N=to_si(144.0, "kgf"),
        nozzle_tilt_rad=TILT_25,
    )

    assert envelope.thrust_to_weight_gross == pytest.approx(1.19, abs=0.02)
    assert 1.03 <= envelope.thrust_to_weight_effective <= 1.14


def test_envelope_jetpack_aviation_tem_margem_maior():
    """Cerca de 239 kgf para cerca de 159 kg: T/W perto de 1,50."""
    massa = MassBudget(pilot_kg=80.0, structure_kg=48.0, engines_kg=0.0, consumable_kg=31.0)
    envelope = solve_envelope(
        massa,
        reference_thrust_installed_N=to_si(239.0, "kgf"),
        nozzle_tilt_rad=0.0,
    )

    assert envelope.thrust_to_weight_gross == pytest.approx(1.50, abs=0.03)
    assert envelope.closes


def test_o_cosseno_separa_bruto_de_efetivo():
    """A diferenca entre o numero que a imprensa cita e o que o piloto tem."""
    massa = orcamento_referencia()
    envelope = solve_envelope(
        massa, reference_thrust_installed_N=to_si(150.0, "kgf"), nozzle_tilt_rad=TILT_25
    )

    razao = envelope.thrust_to_weight_effective / envelope.thrust_to_weight_gross
    assert razao == pytest.approx(math.cos(TILT_25))


def test_envelope_carrega_estado_de_modelo_condicional():
    """Resultado derivado de deck nao validado nao pode virar propriedade de hardware."""
    envelope = solve_envelope(
        orcamento_referencia(),
        reference_thrust_installed_N=to_si(150.0, "kgf"),
        nozzle_tilt_rad=TILT_25,
    )

    assert envelope.status.is_conditional is True


# --------------------------------------------------------------------------- #
# Fechamento de massa
# --------------------------------------------------------------------------- #


def test_fechamento_de_massa_converge_em_conceito_viavel():
    resultado = mass_closure(
        pilot_kg=80.0,
        fixed_kg=10.0,
        structure_fraction=0.05,
        engine_kg_per_N=0.0025,
        consumable_kg_per_N=0.008,
        nozzle_tilt_rad=TILT_25,
    )

    assert resultado.converged
    assert resultado.gross_kg > 90.0
    assert resultado.growth_factor > 1.0


def test_fechamento_de_massa_diverge_na_fronteira_de_inviabilidade():
    """Quando cada quilo exige mais empuxo do que ele proprio paga."""
    resultado = mass_closure(
        pilot_kg=80.0,
        fixed_kg=10.0,
        structure_fraction=0.10,
        engine_kg_per_N=0.05,
        consumable_kg_per_N=0.05,
        nozzle_tilt_rad=TILT_25,
    )

    assert not resultado.converged


def test_fator_de_crescimento_marca_conceito_fragil():
    """Acima de 4 o conceito e fragil: cada quilo de piloto arrasta demais."""
    resultado = mass_closure(
        pilot_kg=80.0,
        fixed_kg=10.0,
        structure_fraction=0.05,
        engine_kg_per_N=0.0025,
        consumable_kg_per_N=0.008,
        nozzle_tilt_rad=TILT_25,
    )

    assert resultado.is_fragile == (resultado.growth_factor > 4.0)


def test_cenario_de_referencia_vale_exatamente_um():
    """A razao de densidade na referencia e 1,0 **por construcao**, nao por
    arredondamento. Ver a nota em RHO_SEA_LEVEL_ISA.
    """
    assert SCENARIOS[Scenario.REFERENCE].density_ratio == pytest.approx(1.0, abs=1e-12)


def test_pressao_nao_muda_com_o_desvio_de_temperatura():
    """⚠ A guarda contra dupla contagem.

    Um dia quente nao muda a coluna de ar acima, muda a densidade dela. Se a pressao
    passar a depender do desvio, o efeito termico entra duas vezes.
    """
    frio = isa(1000.0, 0.0)
    quente = isa(1000.0, 15.0)

    assert frio.pressure_Pa == pytest.approx(quente.pressure_Pa)
    assert quente.temperature_K == pytest.approx(frio.temperature_K + 15.0)
    assert quente.density_kg_m3 < frio.density_kg_m3


def test_razoes_de_densidade_dos_cenarios():
    """Os numeros do vault, agora calculados pelo codigo."""
    assert isa(1000.0, 0.0).density_ratio == pytest.approx(0.907, abs=0.002)
    assert isa(1000.0, 15.0).density_ratio == pytest.approx(0.862, abs=0.002)
