"""Ramos de propulsao: a recusa estrutural de escolher tecnologia cedo demais.

Estes testes nao verificam fisica. Verificam que o **vocabulario** do projeto nao
permite escrever uma conclusao que a evidencia nao sustenta.

O projeto ja cometeu esse erro uma vez, produzindo "recomendacao: combustao" com zero
dinamica implementada. Convencao nao impediu. Estrutura impede.
"""

from __future__ import annotations

import pytest

from hero_atlas.propulsion_family import (
    FAMILIES,
    FamilyStatus,
    PropulsionFamily,
    blocking_unknowns_across,
    family_by_name,
    selection_verdict,
)
from hero_atlas.verdict import Verdict

pytestmark = pytest.mark.validation


def test_nao_existe_status_de_aprovacao() -> None:
    """A ausencia e o mecanismo. Se alguem adicionar um, este teste cai."""
    valores = {s.value for s in FamilyStatus}
    assert valores == {"unevaluated", "candidate", "incompatible_under_hypothesis"}
    for proibido in ("approved", "validated", "selected", "recommended", "feasible"):
        assert not any(proibido in v for v in valores)


def test_selecao_e_indeterminada_hoje() -> None:
    veredito, motivo = selection_verdict()
    assert veredito is Verdict.INDETERMINATE
    assert not veredito.is_conclusive
    assert veredito.rejects
    assert "nao seleciona tecnologia" in motivo


def test_selecao_satisfeita_e_inconstruivel_por_construcao() -> None:
    """O caminho para ``SATISFIED`` passa obrigatoriamente por medir.

    ``SATISFIED`` exige um unico ramo aberto **sem** incognita bloqueante. Mas o
    proprio construtor recusa candidata sem incognita bloqueante. Logo nao existe
    tupla de familias construivel que devolva ``SATISFIED`` com status candidato: so
    retirando incognitas da lista, que so acontece quando um marco produzir o dado.
    """
    with pytest.raises(ValueError, match="aprovacao com outro nome"):
        PropulsionFamily(
            name="atalho",
            summary="tentativa de declarar ramo aprovado",
            status=FamilyStatus.CANDIDATE,
            conditioned_on=("nada",),
            blocking_unknowns=(),
        )


def test_familia_sem_condicao_declarada_e_recusada() -> None:
    with pytest.raises(ValueError, match="conditioned_on"):
        PropulsionFamily(
            name="solta",
            summary="status sem hipotese",
            status=FamilyStatus.UNEVALUATED,
            conditioned_on=(),
        )


def test_eliminacao_sem_hipotese_e_recusada() -> None:
    """Eliminacao sem hipotese registrada nao pode ser revisitada, e vira dogma."""
    with pytest.raises(ValueError, match="sob qual hipotese"):
        PropulsionFamily(
            name="morta",
            summary="eliminada sem motivo",
            status=FamilyStatus.INCOMPATIBLE_UNDER_HYPOTHESIS,
            conditioned_on=("alguma",),
        )


def test_hipotese_de_eliminacao_so_vale_em_ramo_eliminado() -> None:
    with pytest.raises(ValueError, match="sem estar eliminada"):
        PropulsionFamily(
            name="confusa",
            summary="candidata com motivo de eliminacao",
            status=FamilyStatus.CANDIDATE,
            conditioned_on=("alguma",),
            blocking_unknowns=("uma",),
            eliminated_by="motivo",
        )


@pytest.mark.parametrize("familia", FAMILIES, ids=lambda f: f.name)
def test_toda_familia_declara_condicao(familia: PropulsionFamily) -> None:
    assert familia.conditioned_on
    assert all(c.strip() for c in familia.conditioned_on)


@pytest.mark.parametrize("familia", FAMILIES, ids=lambda f: f.name)
def test_ramo_aberto_tem_incognita_bloqueante(familia: PropulsionFamily) -> None:
    """Nenhum ramo aberto pode estar sem bloqueio. Seria aprovacao silenciosa."""
    if familia.is_open:
        assert familia.blocking_unknowns


@pytest.mark.parametrize("familia", FAMILIES, ids=lambda f: f.name)
def test_ramo_fechado_diz_como_reabrir(familia: PropulsionFamily) -> None:
    """Eliminacao carrega a hipotese, entao e sempre atacavel."""
    if not familia.is_open:
        assert familia.eliminated_by
        assert len(familia.eliminated_by) > 40


def test_o_atraso_de_pequeno_sinal_bloqueia_os_ramos_de_turbina() -> None:
    """A incognita central do projeto aparece onde deve aparecer."""
    for nome in ("turbina_compacta", "hibrido_turbina_com_buffer"):
        familia = family_by_name(nome)
        assert any("degrau pequeno" in i for i in familia.blocking_unknowns)


def test_incognitas_agregadas_nao_repetem() -> None:
    agregadas = blocking_unknowns_across()
    assert len(agregadas) == len(set(agregadas))
    assert agregadas


def test_familia_desconhecida_levanta() -> None:
    with pytest.raises(KeyError):
        family_by_name("motor_de_dobra")


def test_todos_eliminados_da_veredito_negativo_e_nao_indeterminado() -> None:
    """Se nada sobrar, a conclusao e sobre a arquitetura, nao sobre a evidencia."""
    so_fechadas = tuple(f for f in FAMILIES if not f.is_open)
    assert so_fechadas
    veredito, motivo = selection_verdict(so_fechadas)
    assert veredito is Verdict.VIOLATED
    assert veredito.is_conclusive
    assert "arquitetura precisa mudar" in motivo
