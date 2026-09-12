"""Procedencia e incerteza de cada numero do projeto.

Regra do projeto (vault/03 - Regras/Regras de procedencia.md):

    Uma ficha de fabricante e fonte primaria para saber que o fabricante DECLARA um
    valor. Isso nao a torna evidencia forte sobre o comportamento em toda condicao
    operacional. A mesma ficha e evidencia muito forte para massa seca, razoavel para
    empuxo estatico em condicao especificada, e NENHUMA para resposta transitoria.

    URL sem copia arquivada nao conta como procedencia.

E a tolerancia de teste pertence a grandeza, nao a fonte:

    aceitar se |y_modelo - y_referencia| <= delta_y_referencia + delta_y_modelo
"""

from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .units import dimension_of, to_si
from .verdict import Verdict

__all__ = [
    "SourceType",
    "EvidenceClass",
    "Applicability",
    "Uncertainty",
    "Provenance",
    "TracedValue",
    "sha256_of_file",
    "within_combined_uncertainty",
    "AcceptanceResult",
]


class SourceType(StrEnum):
    """De onde o numero veio."""

    DATASHEET = "datasheet"
    LITERATURE = "literature"
    DERIVED = "derived"
    PRESS = "press"
    ESTIMATE = "estimate"
    TEST = "test"


class EvidenceClass(StrEnum):
    """O que a fonte fez com a grandeza."""

    MEASURED = "measured"
    DECLARED = "declared"
    DERIVED = "derived"
    INFERRED = "inferred"


def sha256_of_file(path: str | pathlib.Path) -> str:
    """Hash de uma fonte arquivada em ``docs/sources/``."""
    digest = hashlib.sha256()
    with pathlib.Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Applicability(BaseModel):
    """Em que condicao o numero vale.

    O campo mais importante do schema. Um empuxo de bancada estatica ao nivel do mar
    nao diz nada sobre o mesmo motor instalado, a 1000 m, com distorcao de entrada.
    """

    model_config = ConfigDict(extra="allow", frozen=True)

    configuration: str | None = None
    altitude_m: float | None = None
    atmosphere: str | None = None
    inlet_distortion: str | None = None
    installation: str | None = None


class Uncertainty(BaseModel):
    """Incerteza declarada, em unidade explicita."""

    model_config = ConfigDict(frozen=True)

    type: Literal["bounded", "normal", "uniform", "unknown"] = "unknown"
    unit: str | None = None
    lower: float | None = None
    upper: float | None = None
    mean: float | None = None
    std: float | None = None

    @model_validator(mode="after")
    def _check_shape(self) -> Uncertainty:
        if self.type in ("bounded", "uniform"):
            if self.lower is None or self.upper is None:
                raise ValueError(f"incerteza {self.type!r} exige lower e upper")
            if self.lower > self.upper:
                raise ValueError(f"lower {self.lower} maior que upper {self.upper}")
        if self.type == "normal" and self.std is None:
            raise ValueError("incerteza 'normal' exige std")
        if self.unit is not None:
            dimension_of(self.unit)  # levanta UnitError se desconhecida
        return self

    @property
    def is_known(self) -> bool:
        """Se ha incerteza declarada.

        Quando falso, nenhuma comparacao numerica pode ser feita. **Nao** e o mesmo
        que tolerancia infinita: ver :class:`AcceptanceResult`.
        """
        return self.type != "unknown"

    def half_width(self, nominal: float) -> float | None:
        """Meia largura da faixa, ou ``None`` quando a incerteza nao foi declarada.

        ⚠ Antes esta funcao devolvia infinito para o caso desconhecido, o que fazia
        qualquer divergencia passar no criterio de aceitacao. Isso invertia a regra
        central do projeto: um numero **sem** procedencia virava irrefutavel por
        tolerancia infinita, em vez de inconclusivo.

        Para ``normal`` usa dois desvios padrao.
        """
        if self.type in ("bounded", "uniform"):
            assert self.lower is not None and self.upper is not None
            return max(self.upper - nominal, nominal - self.lower, 0.0)
        if self.type == "normal":
            assert self.std is not None
            return 2.0 * self.std
        return None


class Provenance(BaseModel):
    """A procedencia completa de um numero."""

    model_config = ConfigDict(frozen=True)

    source_type: SourceType
    evidence_class: EvidenceClass
    retrieval_date: date | None = None
    source_uri: str | None = None
    source_revision: str | None = None
    source_file_sha256: str | None = Field(default=None, min_length=64, max_length=64)
    applicability: Applicability = Field(default_factory=Applicability)
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    note: str | None = None

    @model_validator(mode="after")
    def _check_consistency(self) -> Provenance:
        # Imprensa e estimativa nunca medem nada. Bloquear no schema evita que uma
        # alegacao de marketing entre como se fosse medicao.
        press_or_estimate = self.source_type in (SourceType.PRESS, SourceType.ESTIMATE)
        if press_or_estimate and self.evidence_class == EvidenceClass.MEASURED:
            raise ValueError(
                f"source_type {self.source_type!r} nao pode ter evidence_class 'measured'"
            )
        return self

    @property
    def is_archived(self) -> bool:
        """Se ha copia versionada com hash.

        Enquanto for falso, o numero **nao pode** virar teste de regressao que
        quebra o build.
        """
        return self.source_file_sha256 is not None

    def require_archived(self) -> None:
        """Falha se a fonte nao tiver copia arquivada."""
        if not self.is_archived:
            raise ValueError(
                "fonte sem copia arquivada: registre o arquivo em docs/sources/ e "
                "preencha source_file_sha256. URL sozinha nao conta como procedencia."
            )


class TracedValue(BaseModel):
    """Um numero com unidade e procedencia, convertivel para SI."""

    model_config = ConfigDict(frozen=True)

    value: float
    unit: str
    provenance: Provenance

    @model_validator(mode="after")
    def _check_unit(self) -> TracedValue:
        dimension_of(self.unit)  # levanta UnitError se desconhecida
        return self

    @property
    def dimension(self) -> str:
        return dimension_of(self.unit)

    @property
    def si(self) -> float:
        """Valor em SI. E isto que o nucleo consome."""
        return to_si(self.value, self.unit)

    @property
    def half_width(self) -> float | None:
        """Meia largura da incerteza, ou ``None`` se nao foi declarada."""
        return self.provenance.uncertainty.half_width(self.value)

    def agrees_with(
        self, model_value: float, model_half_width: float | None = 0.0
    ) -> AcceptanceResult:
        """Criterio de aceitacao por incerteza somada.

            |y_modelo - y_referencia| <= delta_y_referencia + delta_y_modelo

        Compara na unidade declarada deste valor, nao em SI, porque a incerteza foi
        declarada nela. Devolve resultado de **tres valores**: sem incerteza
        declarada nao ha comparacao, e portanto nao ha aprovacao nem reprovacao.
        """
        return within_combined_uncertainty(
            model_value, self.value, model_half_width, self.half_width
        )


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    """Resultado de comparar modelo com referencia.

    ⚠ Existe porque booleano aqui produzia o mesmo defeito que ja fora corrigido em
    ``analysis.requirements``: incerteza ausente colapsava para aprovado. Um numero
    sem incerteza declarada nao e irrefutavel, e **inconclusivo**.

    Attributes:
        status: o veredito de tres valores.
        reason: por que, util quando indeterminado.
        numeric_comparison_performed: se a comparacao chegou a ser feita.
        eligible_for_regression: se este par pode virar teste congelado. Verdadeiro
            para ``SATISFIED`` **e** para ``VIOLATED``, porque congelar uma
            discordancia conhecida e teste legitimo. Falso para indeterminado.
        difference: |modelo - referencia|, quando calculavel.
        budget: soma das meias larguras, quando calculavel.

    ⚠ ``eligible_for_regression`` estava fazendo dois trabalhos. Congelar uma
    comparacao conclusiva e uma coisa; tratar o valor como referencia aceita e
    outra. Um resultado ``VIOLATED`` pode e deve virar teste que confirma a
    rejeicao, mas **nao** e benchmark aceito. Por isso existe
    :attr:`accepted_as_benchmark`, e as implicacoes sao:

        eligible_for_regression  =>  numeric_comparison_performed
                                 e   status != INDETERMINATE
        accepted_as_benchmark    =>  status == SATISFIED
        accepted_as_benchmark    =>  eligible_for_regression
    """

    status: Verdict
    reason: str
    numeric_comparison_performed: bool
    eligible_for_regression: bool
    difference: float | None = None
    budget: float | None = None

    @property
    def accepted_as_benchmark(self) -> bool:
        """Se o valor do modelo pode ser tratado como concordante com a referencia.

        Mais estrito que :attr:`eligible_for_regression`: exige ``SATISFIED``.
        """
        return self.status is Verdict.SATISFIED

    def __bool__(self) -> bool:
        """Apenas ``SATISFIED`` e verdadeiro.

        Indeterminado e falso **operacionalmente**, mas ver :attr:`status` antes de
        escrever qualquer frase sobre o motivo.
        """
        return self.status is Verdict.SATISFIED


def within_combined_uncertainty(
    model_value: float,
    reference_value: float,
    model_half_width: float | None,
    reference_half_width: float | None,
) -> AcceptanceResult:
    """Criterio de aceitacao do projeto, de tres valores.

    Substitui a tolerancia percentual fixa. Um catalogo pode dar massa com precisao
    de gramas e empuxo arredondado ao quilograma-forca na mesma pagina; aplicar a
    mesma porcentagem aos dois produz bloqueio falso no integrador continuo.

    Incerteza ausente de qualquer um dos lados devolve ``INDETERMINATE``: a
    comparacao nao e feita, e o par **nao** e elegivel como teste de regressao.
    """
    if model_half_width is None or reference_half_width is None:
        faltando = []
        if model_half_width is None:
            faltando.append("modelo")
        if reference_half_width is None:
            faltando.append("referencia")
        return AcceptanceResult(
            status=Verdict.INDETERMINATE,
            reason=f"uncertainty_missing: {', '.join(faltando)}",
            numeric_comparison_performed=False,
            eligible_for_regression=False,
        )

    difference = abs(model_value - reference_value)
    budget = model_half_width + reference_half_width
    dentro = difference <= budget

    return AcceptanceResult(
        status=Verdict.SATISFIED if dentro else Verdict.VIOLATED,
        reason="within_combined_uncertainty" if dentro else "outside_combined_uncertainty",
        numeric_comparison_performed=True,
        eligible_for_regression=True,
        difference=difference,
        budget=budget,
    )
