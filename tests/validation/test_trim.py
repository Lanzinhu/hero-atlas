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


def test_razao_de_projecao_vertical_e_menor_que_um():
    """Parte do empuxo se cancela entre bocais e nao vira sustentacao.

    Razao de PROJECAO, nao eficiencia: mede perda geometrica, nao perda de
    instalacao nem propulsiva.
    """
    solucao = solve_trim(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert 0.85 < solucao.vertical_thrust_projection_ratio < 1.0


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


# --------------------------------------------------------------------------- #
# Mapa de autoridade: o que a geometria pode, antes de qualquer controlador
# --------------------------------------------------------------------------- #


def test_ha_combinacao_de_empuxo_que_nao_produz_wrench_nenhum():
    """A carga interna: propulsores que brigam entre si e se cancelam.

    ⚠ **Nao e uma causa independente.** Pelo teorema do posto-nulidade, com cinco
    atuadores e posto 4 o nucleo tem dimensao 1 necessariamente. Esta e a mesma
    deficiencia de posto vista do lado dos atuadores, e as duas causas reais estao
    do lado da saida: linha Fx nula e dependencia entre Fy e Mx.

    O que o teste fixa e a consequencia pratica: cinco atuadores, quatro graus
    uteis. Contar propulsores superestima autoridade nessa quantidade.
    """
    from hero_atlas.analysis.authority import analyse_authority, thrust_null_space

    mapa = analyse_authority(layout())
    nucleo = thrust_null_space(layout())
    W = allocation_matrix(layout())

    assert mapa.wasted_actuator_freedoms == 1
    assert nucleo.shape == (5, 1)
    np.testing.assert_allclose(W @ nucleo[:, 0], 0.0, atol=1e-9)


def test_a_linha_de_forca_longitudinal_e_identicamente_nula():
    """Sem componente para frente em nenhum bocal, Fx nao e canal de controle."""
    from hero_atlas.analysis.authority import analyse_authority

    mapa = analyse_authority(layout())

    assert "Fx" in mapa.zero_rows
    assert not mapa.full_rank


def test_quebrar_o_acoplamento_nao_restaura_o_posto():
    """Escalonar altura desacopla lateral de rolagem, mas o posto continua 4 de 6.

    As duas causas de deficiencia sao independentes: ausencia de componente
    longitudinal e razao comum entre os bocais de braco. Corrigir uma nao corrige a
    outra, e por isso o posto nao melhora aqui.
    """
    from hero_atlas.analysis.authority import analyse_authority

    base = layout()
    escalonado = PropulsionGeometry(
        nozzles=tuple(
            NozzleSpec(
                name=n.name,
                position_body_m=(
                    n.position_body_m
                    if n.name == "dorsal"
                    else n.position_body_m + np.array([0.0, 0.0, -0.10 * ("tras" in n.name)])
                ),
                direction_body=n.direction_body,
                thrust_min_N=n.thrust_min_N,
                thrust_max_N=n.thrust_max_N,
            )
            for n in base.nozzles
        ),
        reference_point_body_m=base.reference_point_body_m,
    )

    W_base, W_esc = allocation_matrix(base), allocation_matrix(escalonado)

    def acoplado(W: np.ndarray) -> bool:
        ativos = np.abs(W[1, :]) > 1e-9
        razoes = W[3, ativos] / W[1, ativos]
        return bool(np.allclose(razoes, razoes[0], atol=1e-9))

    assert acoplado(W_base), "a base tem o acoplamento"
    assert not acoplado(W_esc), "escalonar altura desacopla"
    assert analyse_authority(escalonado).rank == 4, "mas o posto nao melhora"


def test_componente_longitudinal_nos_bocais_sobe_o_posto():
    """Inclinar os bocais para frente e para tras recupera Fx como canal.

    ⚠ De 4 para 5, e **nao e controle completo recuperado**. Ainda sobra uma
    direcao de wrench inacessivel, a do acoplamento entre lateral e rolagem. A
    formulacao correta e recuperacao de uma quinta direcao independente, mantendo
    uma deficiencia estrutural.
    """
    from hero_atlas.analysis.authority import analyse_authority

    base = layout()
    com_x = PropulsionGeometry(
        nozzles=tuple(
            NozzleSpec(
                name=n.name,
                position_body_m=n.position_body_m,
                direction_body=(
                    n.direction_body
                    if n.name == "dorsal"
                    else n.direction_body
                    + np.array([0.15 if "frente" in n.name else -0.10, 0.0, 0.0])
                ),
                thrust_min_N=n.thrust_min_N,
                thrust_max_N=n.thrust_max_N,
            )
            for n in base.nozzles
        ),
        reference_point_body_m=base.reference_point_body_m,
    )

    assert analyse_authority(base).rank == 4
    assert analyse_authority(com_x).rank == 5


def test_janela_de_centro_de_massa_lateral_e_vazia():
    """Condicionado a pairado nivelado, geometria nominal e atuadores disponiveis."""
    from hero_atlas.analysis.authority import cg_window

    geo = layout()

    longitudinal = cg_window(geo, mass_kg=117.0, axis=0, span_m=(-0.10, 0.50))
    lateral = cg_window(
        geo, mass_kg=117.0, axis=1, span_m=(-0.10, 0.10), fixed_cg_m=(0.15, 0.0, 0.0)
    )

    assert longitudinal is not None
    assert longitudinal[1] - longitudinal[0] > 0.05
    # so o ponto exatamente centrado sobrevive
    assert lateral == pytest.approx((0.0, 0.0), abs=1e-9)


def test_a_perda_unica_e_concluida_do_solver_nao_do_posto():
    """⚠ Correcao de raciocinio.

    "Posto 4 com cinco atuadores, logo sem folga" **nao** e derivacao valida:
    remover um atuador pode manter o posto e ainda assim preservar ou destruir um
    trim particular. So resolvendo se descobre.
    """
    from hero_atlas.analysis.authority import single_failure_survey

    resultado = single_failure_survey(layout(), mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL)

    assert len(resultado) == 5
    assert all(causa is not InfeasibilityCause.NONE for causa in resultado.values()), (
        "nesta geometria e neste centro de massa, nenhuma perda unica admite trim"
    )


def test_as_duas_relacoes_geram_exatamente_o_nucleo_a_esquerda():
    """⚠ Fecha o diagnostico: **nao ha terceira limitacao estrutural**.

    Verificar que as direcoes inatingiveis "vivem no espaco gerado por Fx, Fy e Mx"
    e mais fraco do que o necessario: um subespaco de dimensao 2 dentro de um de
    dimensao 3 deixaria espaco para causa nao identificada.

    O que fecha e mostrar que as duas relacoes geram **exatamente** o nucleo a
    esquerda de W:

        v1 = Fx                  (nenhum bocal tem componente longitudinal)
        v2 = Mx - k*Fy           (razao comum entre os quatro bocais de braco)

    Comparando os projetores ortogonais dos dois subespacos. Se forem o mesmo
    projetor, os subespacos sao identicos e toda deficiencia esta explicada.
    """
    W = allocation_matrix(layout())
    u, _s, _vt = np.linalg.svd(W)
    posto = np.linalg.matrix_rank(W)
    nucleo_esquerda = u[:, posto:]

    ativos = np.abs(W[1, :]) > 1e-9
    k = (W[3, ativos] / W[1, ativos])[0]

    v1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    v2 = np.array([0.0, -k, 0.0, 1.0, 0.0, 0.0])
    v2 = v2 / np.linalg.norm(v2)

    # as duas relacoes de fato anulam W
    np.testing.assert_allclose(v1 @ W, 0.0, atol=1e-12)
    np.testing.assert_allclose(v2 @ W, 0.0, atol=1e-12)

    # e geram o mesmo subespaco que o nucleo a esquerda
    assert nucleo_esquerda.shape[1] == 2, "6 menos posto 4"
    par = np.column_stack([v1, v2])
    assert np.linalg.matrix_rank(par) == 2, "as duas relacoes sao independentes"

    projetor_nucleo = nucleo_esquerda @ nucleo_esquerda.T
    projetor_par = par @ np.linalg.pinv(par)

    np.testing.assert_allclose(projetor_nucleo, projetor_par, atol=1e-12)


# --------------------------------------------------------------------------- #
# Experimento 1: o filtro que elimina a maior parte das arquiteturas
# --------------------------------------------------------------------------- #


def tres_pares_escalonados(longitudinal: bool = False):
    """Tres pares diferindo em envergadura, altura **e** inclinacao."""
    from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, parametric_layout

    t15 = math.radians(15.0)
    pares = [
        ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15 if longitudinal else 0.0),
        ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
        ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15 if longitudinal else 0.0),
    ]
    return parametric_layout(
        pairs=pares,
        axial=[AxialNozzleSpec("dorsal", -0.15, 0.10)],
        thrust_max_N=to_si(35.0, "kgf"),
        idle_fraction=0.10,
    )


def test_rolagem_pura_e_o_filtro_que_elimina_quase_tudo():
    """⚠ Um centro deslocado lateralmente exige rolagem **sem** forca lateral.

    Numa arquitetura de pares simetricos isso vem dos graus antissimetricos, que
    precisam gerar tres grandezas: forca lateral, rolagem e guinada. Dois pares dao
    dois graus, e dois nao cobrem tres.
    """
    from hero_atlas.analysis.authority import lateral_cg_authority

    assert lateral_cg_authority(layout()) is False
    assert lateral_cg_authority(tres_pares_escalonados()) is True


def test_contagem_de_pares_nao_basta():
    """⚠ Tres pares diferindo **so em altura** ainda falham.

    Achado do experimento 1: as contribuicoes antissimetricas ficam dependentes, e
    "mais propulsores resolve" e falso.

    ⚠ Correcao de uma afirmacao minha anterior: eu havia escrito que os pares
    precisam diferir nos **tres** parametros. Testado, e falso. Diferenca so de
    inclinacao ja basta nesta familia, e altura mais envergadura juntas nao bastam.
    A condicao geral e diversidade de coluna, nao um parametro especifico.
    Ver :func:`test_diferenca_de_inclinacao_sozinha_ja_basta`.
    """
    from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, parametric_layout
    from hero_atlas.analysis.authority import lateral_cg_authority

    t25 = math.radians(25.0)
    so_altura = parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.35, -0.15, t25),
            ArmPairSpec(0.20, 0.35, -0.26, t25),
            ArmPairSpec(0.08, 0.35, -0.37, t25),
        ],
        axial=[AxialNozzleSpec("dorsal", -0.15, 0.10)],
        thrust_max_N=to_si(35.0, "kgf"),
        idle_fraction=0.10,
    )

    assert so_altura.count == 7, "sete bocais, mais que a base"
    assert lateral_cg_authority(so_altura) is False, "e ainda assim nao fecha"


def test_escalonar_tudo_mais_longitudinal_da_posto_completo():
    """A unica variante da varredura que atinge seis graus de wrench."""
    from hero_atlas.analysis.authority import analyse_authority

    completo = analyse_authority(tres_pares_escalonados(longitudinal=True))

    assert completo.rank == 6
    assert completo.full_rank
    assert completo.zero_rows == ()


def test_can_produce_separa_geometria_de_capacidade():
    """Ignora limites de empuxo por construcao: responde so sobre o espaco coluna."""
    from hero_atlas.analysis.authority import can_produce

    base = layout()

    assert can_produce(base, [0.0, 0.0, -1.0, 0.0, 0.0, 0.0]), "sustentacao vertical sempre da"
    assert not can_produce(base, [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]), "forca longitudinal nao"
    assert not can_produce(base, [0.0, 0.0, 0.0, 1.0, 0.0, 0.0]), "rolagem pura nao"


def test_can_produce_recusa_wrench_de_tamanho_errado():
    from hero_atlas.analysis.authority import can_produce

    with pytest.raises(ValueError, match="6 componentes"):
        can_produce(layout(), [0.0, 0.0, -1.0])


def test_diferenca_de_inclinacao_sozinha_ja_basta():
    """⚠ Derruba a minha propria afirmacao de que os tres parametros eram necessarios.

    Tres pares na mesma altura e mesma envergadura, diferindo **so na inclinacao
    lateral**, ja conseguem rolagem pura. E o contrario nao vale: altura mais
    envergadura, sem inclinacao, continua falhando.

    A condicao geral e diversidade das colunas da matriz de alocacao, e a varredura
    so testou uma familia de geometrias.
    """
    from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, parametric_layout
    from hero_atlas.analysis.authority import lateral_cg_authority

    def montar(pares):
        return parametric_layout(
            pairs=pares,
            axial=[AxialNozzleSpec("dorsal", -0.15, 0.10)],
            thrust_max_N=to_si(35.0, "kgf"),
            idle_fraction=0.10,
        )

    so_inclinacao = montar(
        [
            ArmPairSpec(0.32, 0.35, -0.20, math.radians(15.0)),
            ArmPairSpec(0.20, 0.35, -0.20, math.radians(30.0)),
            ArmPairSpec(0.08, 0.35, -0.20, math.radians(45.0)),
        ]
    )
    altura_e_envergadura = montar(
        [
            ArmPairSpec(0.32, 0.25, -0.15, math.radians(25.0)),
            ArmPairSpec(0.20, 0.35, -0.26, math.radians(25.0)),
            ArmPairSpec(0.08, 0.45, -0.37, math.radians(25.0)),
        ]
    )

    assert lateral_cg_authority(so_inclinacao) is True
    assert lateral_cg_authority(altura_e_envergadura) is False


def test_posto_nao_e_margem():
    """⚠ Alcancar uma direcao nao e ter autoridade nela.

    As variantes que conseguem rolagem pura tem menor valor singular varias vezes
    menor que as que nao conseguem. A direcao existe e exige redistribuicao enorme
    de empuxo, o que a torna pouco util na pratica.
    """
    from hero_atlas.airframe.geometry import ArmPairSpec, AxialNozzleSpec, parametric_layout
    from hero_atlas.analysis.authority import analyse_authority, lateral_cg_authority

    def montar(pares):
        return parametric_layout(
            pairs=pares,
            axial=[AxialNozzleSpec("dorsal", -0.15, 0.10)],
            thrust_max_N=to_si(35.0, "kgf"),
            idle_fraction=0.10,
        )

    com_rolagem = montar(
        [
            ArmPairSpec(0.32, 0.35, -0.20, math.radians(15.0)),
            ArmPairSpec(0.20, 0.35, -0.20, math.radians(30.0)),
            ArmPairSpec(0.08, 0.35, -0.20, math.radians(45.0)),
        ]
    )
    sem_rolagem = montar(
        [
            ArmPairSpec(0.32, 0.35, -0.15, math.radians(25.0)),
            ArmPairSpec(0.20, 0.35, -0.26, math.radians(25.0)),
            ArmPairSpec(0.08, 0.35, -0.37, math.radians(25.0)),
        ]
    )

    assert lateral_cg_authority(com_rolagem) is True
    assert lateral_cg_authority(sem_rolagem) is False

    # e no entanto a que consegue tem a direcao mais fraca
    forte = analyse_authority(sem_rolagem).smallest_nonzero_singular
    fraca = analyse_authority(com_rolagem).smallest_nonzero_singular
    assert fraca < forte / 3.0, (
        f"a variante com rolagem pura tem sing. {fraca:.4f} contra {forte:.4f}: "
        "posto diz que da, valor singular diz que mal da"
    )


def test_objetivo_do_trim_muda_o_resultado():
    """⚠ Minimizar empuxo encosta nos limites **por construcao**.

    Medir folga num trim de minimo empuxo reporta zero quase sempre, e isso e
    propriedade do objetivo, nao da arquitetura. Foi um artefato real na primeira
    versao da varredura de geometria.
    """
    from hero_atlas.analysis.trim import TrimObjective

    geo = layout()
    economico = solve_trim(
        geo,
        mass_kg=117.0,
        center_of_mass_body_m=CG_VIAVEL,
        objective=TrimObjective.MIN_THRUST,
    )
    folgado = solve_trim(
        geo,
        mass_kg=117.0,
        center_of_mass_body_m=CG_VIAVEL,
        objective=TrimObjective.MAX_MARGIN,
    )

    assert economico.feasible and folgado.feasible
    assert economico.margin_N == pytest.approx(0.0, abs=1e-6)
    assert folgado.margin_N > 50.0, "o trim folgado tem margem real"
    assert len(economico.active_constraints) > 0, "o economico encosta em limite"
    assert len(folgado.active_constraints) == 0, "o folgado nao encosta"


def test_margem_custa_pouco_empuxo():
    """O trim folgado gasta so um pouco mais que o economico.

    E o que torna a escolha de objetivo uma decisao de diagnostico, nao de projeto:
    a diferenca de empuxo e pequena e a diferenca de informacao e enorme.
    """
    from hero_atlas.analysis.trim import TrimObjective

    geo = layout()
    economico = solve_trim(
        geo, mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL, objective=TrimObjective.MIN_THRUST
    )
    folgado = solve_trim(
        geo, mass_kg=117.0, center_of_mass_body_m=CG_VIAVEL, objective=TrimObjective.MAX_MARGIN
    )

    excesso = folgado.total_thrust_N / economico.total_thrust_N - 1.0
    assert 0.0 < excesso < 0.05, f"excesso de {excesso:.1%}"
