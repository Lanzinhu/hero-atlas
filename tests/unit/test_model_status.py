"""Estado do modelo: a marca que impede familia parametrica virar medicao."""

from __future__ import annotations

import pytest

from hero_atlas.model_status import (
    PROPULSAO_INSTALADA_HOJE,
    ConclusionScope,
    DeckStatus,
    EvidenceCoverage,
    ModelStatus,
    UnstampedResultError,
    assert_stamped,
)

pytestmark = pytest.mark.unit


def validado() -> ModelStatus:
    return ModelStatus(
        deck=DeckStatus.VALIDATED,
        evidence_coverage=EvidenceCoverage.FULL,
        conclusion_scope=ConclusionScope.REPRESENTATIVE_OF_HARDWARE,
        coupling_model="calibrated",
    )


def test_o_estado_de_hoje_e_condicional():
    """Sete dos oito grupos do deck sem dado. Isso nao e falha de documentacao,
    e o resultado principal do levantamento de evidencia ate agora.
    """
    assert PROPULSAO_INSTALADA_HOJE.is_conditional is True
    assert PROPULSAO_INSTALADA_HOJE.deck is DeckStatus.PARAMETRIC_UNVALIDATED


def test_modelo_validado_nao_e_condicional():
    assert validado().is_conditional is False


@pytest.mark.parametrize(
    ("deck", "coverage", "scope"),
    [
        (
            DeckStatus.PARAMETRIC_UNVALIDATED,
            EvidenceCoverage.FULL,
            ConclusionScope.REPRESENTATIVE_OF_HARDWARE,
        ),
        (
            DeckStatus.VALIDATED,
            EvidenceCoverage.PARTIAL,
            ConclusionScope.REPRESENTATIVE_OF_HARDWARE,
        ),
        (
            DeckStatus.VALIDATED,
            EvidenceCoverage.FULL,
            ConclusionScope.CONDITIONAL_ON_DECLARED_MODEL_FAMILY,
        ),
    ],
)
def test_qualquer_lacuna_torna_a_conclusao_condicional(deck, coverage, scope):
    """Basta uma das tres dimensoes estar incompleta."""
    status = ModelStatus(deck=deck, evidence_coverage=coverage, conclusion_scope=scope)
    assert status.is_conditional is True


def test_a_marca_diz_que_nao_representa_hardware():
    marca = PROPULSAO_INSTALADA_HOJE.stamp()

    assert "nao representa hardware" in marca
    assert "PARAMETRIC_UNVALIDATED" in marca
    assert "condicional" in marca


def test_a_marca_carrega_o_modelo_de_acoplamento():
    """Sob ADR-007 o resultado e reportado para a familia inteira de acoplamentos,
    entao o nome do modelo faz parte da identidade do resultado.
    """
    status = ModelStatus(
        deck=DeckStatus.PARAMETRIC_UNVALIDATED,
        evidence_coverage=EvidenceCoverage.NONE,
        conclusion_scope=ConclusionScope.CONDITIONAL_ON_DECLARED_MODEL_FAMILY,
        coupling_model="fully_coupled_latent",
    )
    assert "fully_coupled_latent" in status.stamp()


def test_saida_condicional_sem_marca_e_recusada():
    """A regra e estrutural, nao convencao. Convencao erode."""
    with pytest.raises(UnstampedResultError, match="sem marca"):
        assert_stamped("Fronteira de estabilidade", PROPULSAO_INSTALADA_HOJE)


def test_saida_condicional_com_marca_passa():
    titulo = PROPULSAO_INSTALADA_HOJE.stamped("Fronteira de estabilidade")
    assert_stamped(titulo, PROPULSAO_INSTALADA_HOJE)


def test_modelo_validado_dispensa_marca():
    assert_stamped("Fronteira de estabilidade", validado())


def test_stamped_e_idempotente():
    """Marcar duas vezes nao duplica a marca."""
    uma = PROPULSAO_INSTALADA_HOJE.stamped("titulo")
    duas = PROPULSAO_INSTALADA_HOJE.stamped(uma)
    assert uma == duas
    assert uma.count("nao representa hardware") == 1


def test_bloco_para_gravar_junto_do_artefato():
    bloco = PROPULSAO_INSTALADA_HOJE.as_dict()

    assert bloco["propulsion_installed_deck"] == "parametric_unvalidated"
    assert bloco["evidence_coverage"] == "partial"
    assert bloco["conclusion_scope"] == "conditional_on_declared_model_family"


def test_estado_e_imutavel():
    with pytest.raises(AttributeError):
        PROPULSAO_INSTALADA_HOJE.deck = DeckStatus.VALIDATED  # type: ignore[misc]
