"""Estado do modelo: impede que familia parametrica vire medicao decorativa.

O risco que este modulo existe para bloquear nao e fisico, e epistemologico:

    A familia parametrica nao validada pode ganhar aparencia de medicao por meio de
    graficos precisos, amostragens densas e fronteiras suaves. Sem marca, uma
    superficie de estabilidade colorida vira "resultado do traje" na memoria de quem
    a le, inclusive de quem a gerou.

Convencao erode. Por isso a marca e **estrutural**: toda saida derivada de um modelo
condicional precisa carregar o carimbo, e :func:`assert_stamped` recusa o que nao
carrega. Ver vault/02 - Decisoes/ADR-007 - Deck de propulsao instalada.md
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "DeckStatus",
    "EvidenceCoverage",
    "ConclusionScope",
    "ModelStatus",
    "UnstampedResultError",
    "assert_stamped",
    "PROPULSAO_INSTALADA_HOJE",
]


class DeckStatus(StrEnum):
    """Quanto do deck vem de evidencia, e quanto vem de hipotese."""

    PARAMETRIC_UNVALIDATED = "parametric_unvalidated"
    PARTIALLY_CALIBRATED = "partially_calibrated"
    VALIDATED = "validated"


class EvidenceCoverage(StrEnum):
    """Fracao dos grupos de parametro com dado arquivado."""

    NONE = "none"
    PARTIAL = "partial"
    FULL = "full"


class ConclusionScope(StrEnum):
    """Ate onde a conclusao vale."""

    CONDITIONAL_ON_DECLARED_MODEL_FAMILY = "conditional_on_declared_model_family"
    REPRESENTATIVE_OF_HARDWARE = "representative_of_hardware"


class UnstampedResultError(RuntimeError):
    """Saida condicional sem a marca de estado do modelo."""


@dataclass(frozen=True, slots=True)
class ModelStatus:
    """Acompanha toda saida derivada de um modelo.

    Attributes:
        deck: estado do deck de propulsao instalada.
        evidence_coverage: quanto dos grupos de parametro tem dado arquivado.
        conclusion_scope: ate onde a conclusao vale.
        coupling_model: qual modelo de acoplamento gerou o resultado. Sob
            ADR-007 o resultado e reportado para a familia inteira, entao o
            nome do modelo faz parte da identidade do resultado.
    """

    deck: DeckStatus
    evidence_coverage: EvidenceCoverage
    conclusion_scope: ConclusionScope
    coupling_model: str = "unspecified"

    @property
    def is_conditional(self) -> bool:
        """Se a conclusao **nao** pode ser lida como propriedade de hardware."""
        return (
            self.deck is not DeckStatus.VALIDATED
            or self.evidence_coverage is not EvidenceCoverage.FULL
            or self.conclusion_scope is ConclusionScope.CONDITIONAL_ON_DECLARED_MODEL_FAMILY
        )

    def stamp(self) -> str:
        """A marca que acompanha titulo, legenda ou rodape.

        Deliberadamente verbosa. Uma marca discreta e ignorada, e o proposito dela
        e justamente nao ser ignorada.
        """
        if not self.is_conditional:
            return "modelo validado"
        return (
            f"MODELO {self.deck.value.upper()} | "
            f"evidencia {self.evidence_coverage.value} | "
            f"acoplamento {self.coupling_model} | "
            "conclusao condicional a familia declarada, nao representa hardware"
        )

    def as_dict(self) -> dict[str, str]:
        """Bloco a gravar junto de qualquer artefato de saida."""
        return {
            "propulsion_installed_deck": self.deck.value,
            "evidence_coverage": self.evidence_coverage.value,
            "conclusion_scope": self.conclusion_scope.value,
            "coupling_model": self.coupling_model,
        }

    def stamped(self, text: str) -> str:
        """Devolve o texto ja com a marca anexada, quando ela for necessaria."""
        if not self.is_conditional or self.stamp() in text:
            return text
        return f"{text}\n[{self.stamp()}]"


def assert_stamped(text: str, status: ModelStatus) -> None:
    """Falha se uma saida condicional nao carregar a marca.

    Chamado no caminho de emissao de figura e de relatorio. E o que transforma a
    regra de convencao em regra estrutural.
    """
    if status.is_conditional and status.stamp() not in text:
        raise UnstampedResultError(
            "saida condicional sem marca de estado do modelo. "
            "Use ModelStatus.stamped() no titulo, legenda ou rodape. "
            f"Marca exigida: {status.stamp()!r}"
        )


PROPULSAO_INSTALADA_HOJE = ModelStatus(
    deck=DeckStatus.PARAMETRIC_UNVALIDATED,
    evidence_coverage=EvidenceCoverage.PARTIAL,
    conclusion_scope=ConclusionScope.CONDITIONAL_ON_DECLARED_MODEL_FAMILY,
    coupling_model="unspecified",
)
"""O estado real do projeto hoje.

Sete dos oito grupos de parametro do deck nao tem dado nenhum. Isso nao e falha de
documentacao: **e o resultado principal do levantamento de evidencia ate agora.**
Ver vault/08 - Dados/Deck de propulsao instalada - schema.md
"""
