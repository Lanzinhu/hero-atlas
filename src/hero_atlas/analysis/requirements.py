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
from ..verdict import Verdict

__all__ = [
    "Relation",
    "Verdict",
    "ActuatorRequirement",
    "AdmissibleRegion",
    "RegionVerdict",
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

    def evaluate(self, candidate: Mapping[str, float]) -> Verdict:
        """Veredito de tres valores para um candidato.

        Parametro ausente devolve ``INDETERMINATE``, nao ``VIOLATED``: o sistema
        fisico nao necessariamente falha, mas a conclusao nao e demonstravel.
        """
        if self.parameter not in candidate:
            return Verdict.INDETERMINATE
        if self.satisfied_by(candidate[self.parameter]):
            return Verdict.SATISFIED
        return Verdict.VIOLATED

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
        """Quais condicoes o candidato nao atende, violadas e indeterminadas juntas.

        Para o relatorio use :meth:`evaluate`, que separa as duas.
        """
        return tuple(r for r in self.requirements if r.evaluate(candidate) is not Verdict.SATISFIED)

    def violated_by(self, candidate: Mapping[str, float]) -> tuple[ActuatorRequirement, ...]:
        """Condicoes que o candidato **fura**. Aqui o modelo esta dizendo nao."""
        return tuple(r for r in self.requirements if r.evaluate(candidate) is Verdict.VIOLATED)

    def indeterminate_for(self, candidate: Mapping[str, float]) -> tuple[ActuatorRequirement, ...]:
        """Condicoes que o candidato **nao permite avaliar**, por parametro ausente.

        Aqui o modelo nao esta dizendo nao. Esta dizendo que nao da para concluir.
        """
        return tuple(r for r in self.requirements if r.evaluate(candidate) is Verdict.INDETERMINATE)

    def evaluate(self, candidate: Mapping[str, float]) -> RegionVerdict:
        """Veredito completo, com as tres classes separadas."""
        satisfeitos: list[ActuatorRequirement] = []
        violados: list[ActuatorRequirement] = []
        indeterminados: list[ActuatorRequirement] = []

        for requirement in self.requirements:
            veredito = requirement.evaluate(candidate)
            if veredito is Verdict.SATISFIED:
                satisfeitos.append(requirement)
            elif veredito is Verdict.VIOLATED:
                violados.append(requirement)
            else:
                indeterminados.append(requirement)

        return RegionVerdict(
            scenario=self.scenario,
            status=self.status,
            satisfied=tuple(satisfeitos),
            violated=tuple(violados),
            indeterminate=tuple(indeterminados),
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


@dataclass(frozen=True, slots=True)
class RegionVerdict:
    """Resultado de avaliar um candidato, com as tres classes separadas.

    A separacao entre violado e indeterminado **sobrevive ate o relatorio**. Fundir
    as duas faria uma lacuna de evidencia aparecer como reprovacao do conceito.
    """

    scenario: str
    status: ModelStatus
    satisfied: tuple[ActuatorRequirement, ...]
    violated: tuple[ActuatorRequirement, ...]
    indeterminate: tuple[ActuatorRequirement, ...]

    @property
    def is_satisfied(self) -> bool:
        """Todas as condicoes demonstradas. Indeterminado **nao** conta como sim."""
        return not self.violated and not self.indeterminate

    @property
    def is_demonstrable(self) -> bool:
        """Se todo requisito pode ser avaliado sob este candidato.

        Quando falso, um veredito negativo nao e conclusao sobre o conceito: e falta
        de parametro.
        """
        return not self.indeterminate

    @property
    def is_refuted(self) -> bool:
        """Se ha condicao **furada**. Aqui o modelo esta afirmando falha.

        Diferente de :attr:`is_satisfied` ser falso, que tambem acontece por falta
        de parametro.
        """
        return bool(self.violated)

    @property
    def is_rejected(self) -> bool:
        """Se o candidato deve ser bloqueado operacionalmente.

        Verdadeiro para violado **e** para indeterminado, porque nao demonstrado nao
        e aprovado. A rejeicao pode tratar os dois igual; o dado e o relatorio, nao.
        """
        return not self.is_satisfied

    @property
    def verdict(self) -> Verdict:
        """O veredito agregado, no mesmo vocabulario de tres valores.

        Violacao tem precedencia sobre indeterminacao: se ja ha condicao furada, o
        modelo diz nao mesmo que outra condicao seja inavaliavel.
        """
        if self.violated:
            return Verdict.VIOLATED
        if self.indeterminate:
            return Verdict.INDETERMINATE
        return Verdict.SATISFIED

    def as_report(self) -> str:
        """Texto para o relatorio, marcado e com a distincao preservada."""
        linhas = [f"Cenario {self.scenario!r}: veredito {self.verdict.value}.", ""]

        if self.satisfied:
            linhas.append("Demonstradas:")
            linhas.extend(f"  {r.as_text()}" for r in self.satisfied)
            linhas.append("")

        if self.violated:
            linhas.append("Violadas, o modelo diz nao:")
            linhas.extend(f"  {r.as_text()}" for r in self.violated)
            linhas.append("")

        if self.indeterminate:
            linhas.append(
                "Nao demonstraveis sob este candidato, parametro ausente. "
                "Isto NAO e reprovacao, e falta de evidencia:"
            )
            linhas.extend(f"  {r.as_text()}  [parametro ausente]" for r in self.indeterminate)
            linhas.append("")

        texto = "\n".join(linhas).rstrip()
        marcado = self.status.stamped(texto)
        assert_stamped(marcado, self.status)
        return marcado
