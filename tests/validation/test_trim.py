"""Marco 2: trim vetorial com o momento do peso, e o que ele revela.

Ver vault/02 - Decisoes/ADR-002 e vault/06 - Marcos/Marco 2 - Trim e autoridade.md

Aqui a suposicao do marco 1 quebra. O envelope escalar presumia que toda capacidade
instalada contribui para a direcao util. O trim resolve com direcao, posicao e limite
proprios por propulsor, e descobre que a arquitetura tem restricoes que nenhum numero
de empuxo resolve.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from hero_atlas.airframe.geometry import (
    NozzleSpec,
    PropulsionGeometry,
    allocation_matrix,
    gravity_like_layout,
)
from hero_atlas.analysis.trim import (
    InfeasibilityCause,
    TrimTarget,
    assess_capture,
    gravity_in_body_N,
    solve_trim,
)
from hero_atlas.units import G0, to_si
from hero_atlas.verdict import Verdict

pytestmark = pytest.mark.validation

CG_VIAVEL = [0.15, 0.0, 0.0]
"""Centro de massa dentro da janela de equilibrio desta geometria."""


def layout() -> PropulsionGeometry:
    return gravity_like_layout(thrust_max_N=to_si(35.0, "kgf"))


# --------------------------------------------------------------------------- #
# O termo que o ADR-002 existe para nao deixar esquecer
# --------------------------------------------------------------------------- #


def test_o_momento_do_peso_entra_no_wrench_requerido():
    """Com o centro deslocado do ponto de referencia, o peso produz momento.

    Se este termo sumir, qualquer postura assimetrica **parece** equilibrada.
    """
    geo = layout()
    massa = 117.0

    centrado = solve_trim(geo, mass_kg=massa, center_of_mass_body_m=[0.0, 0.0, 0.0])
    deslocado = solve_trim(geo, mass_kg=massa, center_of_mass_body_m=CG_VIAVEL)

    # a parte de forca e identica; so o momento muda
    np.testing.assert_allclose(
        centrado.required_wrench[:3], deslocado.required_wrench[:3], atol=1e-12
    )
    assert not np.allclose(centrado.required_wrench[3:], deslocado.required_wrench[3:])


def test_momento_do_peso_confere_com_o_produto_vetorial():
    """M_peso = (r_C - r_O) x (m * R_BI * g_I), calculado a mao."""
    geo = layout()
    massa, dx = 117.0, 0.15

    solucao = solve_trim(geo, mass_kg=massa, center_of_mass_body_m=[dx, 0.0, 0.0])

    peso_B = np.array([0.0, 0.0, massa * G0])
    esperado = -np.cross(np.array([dx, 0.0, 0.0]), peso_B)
    np.testing.assert_allclose(solucao.required_wrench[3:], esperado, atol=1e-9)


def test_atitude_do_tronco_muda_a_gravidade_no_corpo():
    """O trim de uma postura inclinada depende da atitude. Nao e formalismo."""
    nivelado = gravity_in_body_N(117.0)

    inclinacao = math.radians(20.0)
    c, s = math.cos(inclinacao), math.sin(inclinacao)
    R = np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])
    inclinado = gravity_in_body_N(117.0, R)

    assert nivelado[0] == pytest.approx(0.0, abs=1e-9)
    assert abs(inclinado[0]) > 1.0, "inclinado, o peso ganha componente longitudinal"
    assert np.linalg.norm(nivelado) == pytest.approx(np.linalg.norm(inclinado))


# --------------------------------------------------------------------------- #
# O que a matriz de alocacao revela sobre a arquitetura
# --------------------------------------------------------------------------- #


def test_esta_geometria_nao_produz_forca_longitudinal():
    """Nenhum bocal tem componente para frente: translacao exige inclinar o corpo.

    E a mesma situacao do quadrirrotor. Subatuado **nao** e incontrolavel, mas a
    rota de translacao passa obrigatoriamente pela atitude.
    """
    W = allocation_matrix(layout())

    np.testing.assert_allclose(W[0, :], 0.0, atol=1e-12)


def test_forca_lateral_e_rolagem_sao_o_mesmo_canal():
    """⚠ O achado mais forte do marco 2.

    Com todos os bocais de braco na mesma altura e mesma envergadura, a linha de
    forca lateral e a linha de momento de rolagem ficam **proporcionais**. Nao da
    para comandar um sem o outro: sao um canal, nao dois.
    """
    W = allocation_matrix(layout())
    linha_fy, linha_mx = W[1, :], W[3, :]

    ativos = np.abs(linha_fy) > 1e-9
    razoes = linha_mx[ativos] / linha_fy[ativos]

    assert np.allclose(razoes, razoes[0], atol=1e-9), (
        "se as razoes divergirem, a geometria ganhou canais independentes"
    )
    assert np.linalg.matrix_rank(W) == 4, "posto 4 de 6, com 5 atuadores"


def test_o_acoplamento_impede_equilibrar_desvio_lateral_de_centro():
    """⚠ Consequencia direta: **um milimetro** de desvio lateral ja nao fecha.

    E geometrico, nao de capacidade. Motor maior nao resolve, porque o wrench
    exigido esta fora do espaco coluna da matriz de alocacao.
    """
    geo = layout()

    centrado = solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=[0.15, 0.0, 0.0])
    desviado = solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=[0.15, 0.001, 0.0])

    assert centrado.feasible
    assert not desviado.feasible
    assert desviado.cause is InfeasibilityCause.GEOMETRICALLY_UNATTAINABLE
    assert "Mx" in desviado.message


# --------------------------------------------------------------------------- #
# As duas causas de inviabilidade, que nao se confundem
# --------------------------------------------------------------------------- #


def test_diagnostico_separa_geometria_de_capacidade():
    """Motor maior resolve uma e nao resolve a outra.

    Fundir as duas faz alguem comprar turbina maior para um problema que turbina
    nenhuma resolve.
    """
    geo = layout()

    # fora da janela longitudinal: a direcao e atingivel, faltam limites
    capacidade = solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=[0.40, 0.0, 0.0])
    # desvio lateral: nenhum empuxo produz
    geometria = solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=[0.15, 0.05, 0.0])

    assert capacidade.cause is InfeasibilityCause.BOUNDS_INFEASIBLE
    assert geometria.cause is InfeasibilityCause.GEOMETRICALLY_UNATTAINABLE
    assert "Motor maior nao resolve" in geometria.message


def test_solucao_viavel_nao_tem_causa_de_inviabilidade():
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert solucao.status is Verdict.SATISFIED
    assert solucao.cause is InfeasibilityCause.NONE
    assert solucao.unattainable_component is None


# --------------------------------------------------------------------------- #
# A janela de centro de massa
# --------------------------------------------------------------------------- #


def test_existe_uma_janela_estreita_de_centro_de_massa():
    """O centro tem que ficar sob o centroide de empuxo, e a folga e pequena."""
    geo = layout()
    viaveis = [
        dx
        for dx in np.arange(-0.10, 0.50, 0.005)
        if solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=[float(dx), 0.0, 0.0]).feasible
    ]

    assert viaveis, "deveria existir alguma posicao viavel"
    largura = max(viaveis) - min(viaveis)
    assert 0.05 < largura < 0.30, f"janela de {largura:.3f} m fora do esperado"


def test_o_trim_equilibra_de_fato_o_wrench_exigido():
    """Residuo nulo: a solucao nao e aproximada, e equilibrio."""
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    np.testing.assert_allclose(solucao.residual_wrench, 0.0, atol=1e-6)


def test_eficiencia_vertical_e_menor_que_um():
    """Parte do empuxo se cancela entre bocais e nao vira sustentacao."""
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert 0.85 < solucao.vertical_efficiency < 1.0


def test_soma_do_trim_e_menor_que_a_capacidade_instalada():
    geo = layout()
    solucao = solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert solucao.total_thrust_N < geo.total_thrust_max_N


# --------------------------------------------------------------------------- #
# Falha: perder um propulsor
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("falho", ["dorsal", "braco_esq_frente", "braco_dir_tras"])
def test_perder_qualquer_propulsor_quebra_o_equilibrio(falho: str):
    """⚠ Nesta geometria **nenhuma** perda unica e tolerada no mesmo centro de massa.

    Com cinco propulsores e posto 4, nao ha redundancia: cada um esta no equilibrio.
    """
    geo = layout()
    intacto = solve_trim(geo, mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)
    com_falha = solve_trim(geo.fail(falho), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert intacto.feasible
    assert not com_falha.feasible


def test_falhar_bocal_inexistente_e_erro():
    with pytest.raises(ValueError, match="inexistentes"):
        layout().fail("turbina_imaginaria")


def test_sem_nenhum_propulsor_a_causa_e_declarada():
    geo = layout()
    todos = geo.fail(*[n.name for n in geo.nozzles])

    solucao = solve_trim(todos, mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert solucao.cause is InfeasibilityCause.NO_ACTUATORS


# --------------------------------------------------------------------------- #
# Existencia nao e alcancabilidade
# --------------------------------------------------------------------------- #


def test_trim_existente_pode_ser_inalcancavel_no_horizonte():
    """R-02: as duas viabilidades sao perguntas diferentes."""
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)
    parado = np.zeros_like(solucao.thrusts_N)

    rapido = assess_capture(
        solucao, current_thrusts_N=parado, rate_up_N_s=2000.0, rate_down_N_s=2000.0, horizon_s=0.5
    )
    lento = assess_capture(
        solucao, current_thrusts_N=parado, rate_up_N_s=50.0, rate_down_N_s=50.0, horizon_s=0.5
    )

    assert solucao.feasible, "o equilibrio existe nos dois casos"
    assert rapido.reachable_within_horizon
    assert not lento.reachable_within_horizon
    assert lento.limiting_actuators, "tem que dizer qual propulsor nao chega"


def test_capture_devolve_o_tempo_necessario():
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)
    parado = np.zeros_like(solucao.thrusts_N)

    avaliacao = assess_capture(
        solucao, current_thrusts_N=parado, rate_up_N_s=500.0, rate_down_N_s=500.0, horizon_s=10.0
    )

    esperado = float(np.max(solucao.thrusts_N)) / 500.0
    assert avaliacao.required_time_s == pytest.approx(esperado)


def test_nao_da_para_avaliar_captura_de_trim_inviavel():
    inviavel = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=[0.15, 0.05, 0.0])

    with pytest.raises(ValueError, match="inviavel"):
        assess_capture(
            inviavel,
            current_thrusts_N=np.zeros(5),
            rate_up_N_s=500.0,
            rate_down_N_s=500.0,
            horizon_s=1.0,
        )


# --------------------------------------------------------------------------- #
# Contrato
# --------------------------------------------------------------------------- #


def test_so_pairado_nivelado_esta_implementado():
    """O tipo existe no contrato para a hipotese ficar visivel, nao para ser
    silenciosamente tratado como pairado.
    """
    with pytest.raises(NotImplementedError, match="level_hover"):
        solve_trim(
            layout(),
            mass_kg=117.0,
            center_of_mass_body_m=CG_VIAVEL,
            target=TrimTarget.COORDINATED_TURN,
        )


def test_solucao_carrega_estado_de_modelo_condicional():
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert solucao.model_status.is_conditional is True


def test_bocal_sem_direcao_e_recusado():
    with pytest.raises(ValueError, match="norma nula"):
        NozzleSpec(
            name="ruim",
            position_body_m=np.zeros(3),
            direction_body=np.zeros(3),
            thrust_min_N=0.0,
            thrust_max_N=1.0,
        )


def test_limites_invertidos_sao_recusados():
    with pytest.raises(ValueError, match="limites invalidos"):
        NozzleSpec(
            name="ruim",
            position_body_m=np.zeros(3),
            direction_body=np.array([0.0, 0.0, -1.0]),
            thrust_min_N=100.0,
            thrust_max_N=10.0,
        )
