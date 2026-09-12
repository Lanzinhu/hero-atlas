"""Regiao admissivel: a saida do deck e requisito, nao estimativa.

Inversao de proposito registrada no ADR-007. A familia parametrica inicial e um
**objeto de exploracao de requisitos**, nao um modelo de veiculo. O valor dela nao e
produzir uma estimativa central de ``tau``, ``eta_inst`` ou consumo especifico. E
produzir afirmacoes da forma:

    Para que o cenario seja controlavel no modelo, o conjunto instalado precisa
    satisfazer Theta_prop pertencente a A.

Isso transforma ausencia de dado em **especificacao futura verificavel**. Nao "a
turbina parece rapida", e sim "a arquitetura exige resposta local, rampa, autoridade
residual e perda instalada dentro desta regiao".

Exemplos do tipo de condicao que este modulo representa:

    tau <= tau_max
    Tdot_up_max >= Tdot_min
    eta_inst >= eta_min
    M_max / (I * omega_c^2) >= Gamma_min

sempre **sob a familia declarada de acoplamentos** entre esses parametros, porque uma
condicao satisfeita isoladamente pode ser inatingivel em conjunto.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ..model_status import ModelStatus, assert_stamped
from ..units import dimension_of

__all__ = [
    "Relation",
    "ActuatorRequirement",
    "AdmissibleRegion",
]


class Relation(StrEnum):
    """Sentido da condicao."""

    AT_MOST = "at_most"
    AT_LEAST = "at_least"

    @property
    def symbol(self) -> str:
        return "<=" if self is Relation.AT_MOST else ">="


@dataclass(frozen=True, slots=True)
class ActuatorRequirement:
    """Uma condicao minima sobre o conjunto instalado.

    Attributes:
        parameter: nome do parametro, por exemplo ``'tau_subida'``.
        relation: se o limite e teto ou piso.
        threshold: o valor limite, na unidade declarada.
        unit: unidade do limite. Validada contra o registro de unidades.
        conditioned_on: o que estava fixo quando esta condicao foi obtida.
            Pose, margem de empuxo, modelo de acoplamento, familia de
            perturbacao. Sem isso a condicao nao e interpretavel.
        note: observacao livre.
    """

    parameter: str
    relation: Relation
    threshold: float
    unit: str
    conditioned_on: Mapping[str, Any] = field(default_factory=dict)
    note: str | None = None

    def __post_init__(self) -> None:
        if not self.parameter:
            raise ValueError("parameter nao pode ser vazio")
        dimension_of(self.unit)  # levanta UnitError se desconhecida
        if not self.conditioned_on:
            raise ValueError(
                f"requisito {self.parameter!r} sem 'conditioned_on'. "
                "Uma condicao sem o contexto em que foi obtida nao e interpretavel: "
                "declare pose, margem, modelo de acoplamento e perturbacao."
            )

    def satisfied_by(self, value: float) -> bool:
        """Se um valor candidato satisfaz a condicao."""
        if self.relation is Relation.AT_MOST:
            return value <= self.threshold
        return value >= self.threshold

    def as_text(self) -> str:
        return f"{self.parameter} {self.relation.symbol} {self.threshold:g} {self.unit}"


@dataclass(frozen=True, slots=True)
class AdmissibleRegion:
    """Conjunto conjunto de condicoes, mais o estado do modelo que as gerou.

    O estado do modelo **faz parte** da regiao, nao e metadado opcional. Uma regiao
    admissivel derivada de deck nao validado e uma especificacao condicional, e o
    relatorio tem que dizer isso.
    """

    requirements: tuple[ActuatorRequirement, ...]
    status: ModelStatus
    scenario: str

    def __post_init__(self) -> None:
        if not self.requirements:
            raise ValueError("uma regiao admissivel vazia nao diz nada")
        if not self.scenario:
            raise ValueError("scenario nao pode ser vazio")

    def __iter__(self) -> Iterator[ActuatorRequirement]:
        return iter(self.requirements)

    def __len__(self) -> int:
        return len(self.requirements)

    @classmethod
    def of(
        cls,
        requirements: Iterable[ActuatorRequirement],
        *,
        status: ModelStatus,
        scenario: str,
    ) -> AdmissibleRegion:
        return cls(tuple(requirements), status, scenario)

    def satisfied_by(self, candidate: Mapping[str, float]) -> bool:
        """Se um conjunto candidato satisfaz **todas** as condicoes.

        Um parametro ausente no candidato conta como nao satisfeito: silencio nao e
        aprovacao.
        """
        for requirement in self.requirements:
            if requirement.parameter not in candidate:
                return False
            if not requirement.satisfied_by(candidate[requirement.parameter]):
                return False
        return True

    def unmet_by(self, candidate: Mapping[str, float]) -> tuple[ActuatorRequirement, ...]:
        """Quais condicoes o candidato nao atende, para diagnostico."""
        return tuple(
            r
            for r in self.requirements
            if r.parameter not in candidate or not r.satisfied_by(candidate[r.parameter])
        )

    def as_specification(self) -> str:
        """O texto que vai ao relatorio, ja com a marca de estado do modelo.

        E aqui que a inversao fica visivel: o entregavel e uma especificacao para
        evidencia futura, nao uma estimativa apresentada como propriedade do veiculo.
        """
        linhas = [
            f"Para o cenario {self.scenario!r}, o conjunto instalado precisa satisfazer:",
            "",
        ]
        linhas.extend(f"  {r.as_text()}" for r in self.requirements)
        texto = "\n".join(linhas)
        marcado = self.status.stamped(texto)
        assert_stamped(marcado, self.status)
        return marcado
