"""Funil de arquiteturas: os filtros param na hora certa e medem o que dizem medir.

Ver vault/06 - Marcos/Experimento 3 - Funil de arquiteturas.md

O grupo mais importante deste arquivo e o do **torque de reacao**. Ele existe porque
a primeira rodada do funil eliminou quatro familias de rotor com posto 3 de 6, e elas
nao morreram de fisica: morreram de um termo ausente no modelo de alocacao.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from hero_atlas.airframe.geometry import (
    ArmPairSpec,
    AxialNozzleSpec,
    NozzleSpec,
    PropulsionGeometry,
    allocation_matrix,
    parametric_layout,
)
from hero_atlas.analysis.funnel import (
    ArchitectureFamily,
    PropulsionKind,
    ScreeningRequirements,
    ScreeningStage,
    mortality_by_stage,
    run_funnel,
    screen_family,
    survivors,
)
from hero_atlas.units import to_si

pytestmark = pytest.mark.validation

TSFC = to_si(1.54, "kg/(kgf*h)")
LACUNA = ("hipotese de teste, nada medido",)


def geometria_boa() -> PropulsionGeometry:
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


def familia(**mudancas: object) -> ArchitectureFamily:
    base: dict[str, object] = dict(
        code="T",
        name="teste",
        summary="familia de teste",
        geometry=geometria_boa(),
        dry_mass_kg=95.0,
        energy_mass_kg=20.0,
        kind=PropulsionKind.JET,
        tsfc_kg_per_N_s=TSFC,
        unmodelled=LACUNA,
    )
    base.update(mudancas)
    return ArchitectureFamily(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# O funil para na primeira reprovacao
# ---------------------------------------------------------------------------


def test_para_na_primeira_reprovacao() -> None:
    """Massa absurda morre em empuxo, e nenhum filtro caro chega a rodar.

    Parar cedo nao e otimizacao: rodar integracao de missao numa geometria que nem
    levanta produz numero sem significado e custa caro para produzir.
    """
    r = screen_family(familia(dry_mass_kg=4000.0))
    assert r.died_at is ScreeningStage.INSTALLED_THRUST
    assert len(r.outcomes) == 1
    assert not r.survived


def test_familia_boa_passa_por_todos_os_filtros() -> None:
    r = screen_family(familia())
    assert r.survived, r.died_at
    assert len(r.outcomes) == len(ScreeningStage)
    assert r.stages_cleared == len(ScreeningStage)


def test_criterio_mais_duro_mata_onde_deve() -> None:
    """A autonomia exigida e escolha de campanha, e muda-la muda quem sobrevive."""
    folgado = screen_family(familia(), ScreeningRequirements(min_hover_endurance_s=60.0))
    apertado = screen_family(familia(), ScreeningRequirements(min_hover_endurance_s=3600.0))
    assert folgado.survived
    assert apertado.died_at is ScreeningStage.MISSION_ENERGY


def test_exigir_falha_unica_mata_a_geometria_sem_redundancia() -> None:
    r = screen_family(familia(), ScreeningRequirements(tolerate_single_failure=True))
    assert r.died_at is ScreeningStage.SINGLE_FAILURE
    assert r.metric(ScreeningStage.SINGLE_FAILURE) == 0.0


def test_estagios_estao_em_ordem_de_custo() -> None:
    valores = [s.value for s in ScreeningStage]
    assert valores == sorted(valores)
    assert ScreeningStage.INSTALLED_THRUST < ScreeningStage.MISSION_ENERGY


# ---------------------------------------------------------------------------
# Torque de reacao: o termo que faltava, e que eliminava familias por engano
# ---------------------------------------------------------------------------


def anel(quantidade: int, torque_por_empuxo_m: float) -> PropulsionGeometry:
    """Anel plano de rotores, com sentidos de giro alternados."""
    bocais = []
    for i in range(quantidade):
        ang = 2.0 * math.pi * i / quantidade
        inclinacao = math.radians(10.0)
        si, ci = math.sin(inclinacao), math.cos(inclinacao)
        bocais.append(
            NozzleSpec(
                name=f"r{i}",
                position_body_m=np.array([0.85 * math.cos(ang), 0.85 * math.sin(ang), 0.0]),
                direction_body=np.array([si * math.cos(ang), si * math.sin(ang), -ci]),
                thrust_min_N=0.0,
                thrust_max_N=to_si(55.0, "kgf"),
                torque_per_thrust_m=(1.0 if i % 2 == 0 else -1.0) * torque_por_empuxo_m,
            )
        )
    return PropulsionGeometry(nozzles=tuple(bocais), reference_point_body_m=np.zeros(3))


def test_sem_torque_de_reacao_a_linha_de_guinada_some() -> None:
    """Era o defeito: anel plano sem torque de reacao nao tem guinada nenhuma.

    Quatro familias de rotor foram eliminadas do funil por isso, com posto 3 de 6.
    """
    W = allocation_matrix(anel(6, 0.0))
    assert np.allclose(W[5, :], 0.0), "linha Mz deveria ser nula sem torque de reacao"


def test_com_torque_de_reacao_a_guinada_aparece_e_o_posto_sobe() -> None:
    sem = allocation_matrix(anel(6, 0.0))
    com = allocation_matrix(anel(6, 0.059))
    assert not np.allclose(com[5, :], 0.0)
    assert np.linalg.matrix_rank(com, tol=1e-9) > np.linalg.matrix_rank(sem, tol=1e-9)


def test_giro_alternado_separa_guinada_de_sustentacao() -> None:
    """Com todos girando igual, guinada vira multiplo de sustentacao.

    E por isso que todo quadricoptero real alterna o sentido de giro dos rotores.
    """
    mesmo_sentido = tuple(
        NozzleSpec(
            name=n.name,
            position_body_m=n.position_body_m,
            direction_body=n.direction_body,
            thrust_min_N=n.thrust_min_N,
            thrust_max_N=n.thrust_max_N,
            torque_per_thrust_m=abs(n.torque_per_thrust_m),
        )
        for n in anel(6, 0.059).nozzles
    )
    W = allocation_matrix(
        PropulsionGeometry(nozzles=mesmo_sentido, reference_point_body_m=np.zeros(3))
    )
    razoes = W[5, :] / W[2, :]
    assert np.allclose(razoes, razoes[0]), "guinada deveria ser multiplo de sustentacao"


def test_rolagem_pura_do_anel_vem_do_canal_fraco() -> None:
    """A rolagem pura de um anel plano existe **so** pelo torque de reacao.

    Sem ele, momento de rolagem e forca lateral sao proporcionais em toda coluna, e o
    canal de rolagem pura desaparece. Com ele, o canal existe mas e ordens de
    grandeza mais fraco que o principal, e e por isso que a janela lateral de centro
    de massa de um multirrotor plano fica em milimetros.
    """
    com = allocation_matrix(anel(6, 0.059))
    sem = allocation_matrix(anel(6, 0.0))

    # ⚠ Dois dos seis rotores ficam sobre o eixo x e tem forca lateral nula, entao a
    # razao neles e indefinida. Comparar so onde o denominador existe.
    ativos = np.abs(sem[1, :]) > 1e-9
    assert ativos.sum() >= 2

    razoes_sem = sem[3, ativos] / sem[1, ativos]
    assert np.allclose(razoes_sem, razoes_sem[0]), "sem reacao, Mx e Fy sao proporcionais"

    razoes_com = com[3, ativos] / com[1, ativos]
    assert not np.allclose(razoes_com, razoes_com[0]), "com reacao, a proporcao quebra"

    singulares = np.linalg.svd(com, compute_uv=False)
    assert singulares[-1] / singulares[0] < 0.05, "o canal novo e fraco, nao forte"


def test_jato_nao_tem_torque_de_reacao_por_padrao() -> None:
    for bocal in geometria_boa().nozzles:
        assert bocal.torque_per_thrust_m == 0.0


# ---------------------------------------------------------------------------
# Contratos
# ---------------------------------------------------------------------------


def test_familia_sem_lacuna_declarada_e_recusada() -> None:
    with pytest.raises(ValueError, match="fora do modelo"):
        familia(unmodelled=())


def test_rotor_sem_area_de_disco_e_recusado() -> None:
    with pytest.raises(ValueError, match="area de disco"):
        familia(kind=PropulsionKind.ROTOR_BATTERY, disk_area_m2=None)


def test_gerador_sem_rendimento_de_cadeia_e_recusado() -> None:
    with pytest.raises(ValueError, match="rendimento de cadeia"):
        familia(kind=PropulsionKind.ROTOR_GENERATOR, disk_area_m2=1.0, chain_efficiency=None)


def test_codigos_duplicados_sao_recusados() -> None:
    with pytest.raises(ValueError, match="duplicados"):
        run_funnel((familia(), familia()))


def test_funil_vazio_e_recusado() -> None:
    with pytest.raises(ValueError, match="nenhuma familia"):
        run_funnel(())


def test_mortalidade_soma_com_as_mortas() -> None:
    resultados = run_funnel((familia(), familia(code="U", dry_mass_kg=4000.0)))
    assert sum(mortality_by_stage(resultados).values()) == 1
    assert len(survivors(resultados)) == 1
