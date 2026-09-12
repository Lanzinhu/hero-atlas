"""Funil de arquiteturas: muitas hipoteses entram, poucas candidatas saem.

O projeto **nao** escolhe componentes para justificar uma arquitetura. Ele cria
arquiteturas parametricas para descobrir **quais especificacoes de componente seriam
necessarias**, e elimina as ruins com numeros rastreaveis.

    muitas possibilidades -> modelos comparaveis -> eliminacao por criterio -> poucas

Cada familia e uma hipotese com poucos parametros interpretaveis. O funil aplica
filtros **do mais barato para o mais caro**, e para na primeira reprovacao: uma
familia que nao fecha trim nao merece que se gaste integracao de missao nela, muito
menos dinamica fechada.

A ordem importa e esta em :class:`ScreeningStage`:

======  ==========================  =====================================
ordem   estagio                     custo
======  ==========================  =====================================
1       empuxo instalado x peso     aritmetica
2       posto da alocacao           uma decomposicao em valores singulares
3       trim nominal                um programa linear
4       saida do chao               um programa linear
5       tolerancia de centro lateral  varredura de programas lineares
6       folga de empuxo             um programa linear
7       energia de missao           integracao com um programa linear por passo
8       falha unica                 um programa linear por propulsor
======  ==========================  =====================================

⚠ **Sobreviver ao funil nao aprova nada.** Todos estes filtros sao **estaticos**:
nenhum deles ve atraso, rampa, saturacao dinamica ou estabilidade. Uma familia que
passa em tudo aqui continua sendo apenas candidata a receber dinamica, e e ai que a
incognita central do projeto, a resposta a degrau pequeno, entra. Ver
:mod:`hero_atlas.propulsion_family`.

⚠ **E reprovar tambem nao elimina, quando o criterio nao serve a familia.** O filtro
de centro de massa lateral exige equilibrio **sem inclinar o tronco**, que e um
requisito de traje. Um multirrotor responde a centro deslocado inclinando o veiculo,
e reprova nesse filtro por nao fazer algo que ele nunca precisaria fazer. Ver
``ScreeningRequirements.lateral_cg_tolerance_m``. Familias de rotor mortas ali contam
como **nao julgadas**.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum

from ..airframe.geometry import PropulsionGeometry
from ..units import G0
from ..verdict import Verdict
from .authority import analyse_authority, cg_window, lateral_cg_authority, single_failure_survey
from .mission_energy import (
    REFERENCE_HOVER_MISSION,
    BatteryStorage,
    FuelStorage,
    GeneratorFuelStorage,
    GeometricThrustDemand,
    MissionProfile,
    Storage,
    TerminationReason,
    evaluate_mission_energy,
)
from .trim import InfeasibilityCause, TrimObjective, solve_trim

__all__ = [
    "PropulsionKind",
    "ScreeningStage",
    "ArchitectureFamily",
    "ScreeningRequirements",
    "StageOutcome",
    "ScreeningResult",
    "screen_family",
    "run_funnel",
    "survivors",
    "mortality_by_stage",
    "TRIAGEM_PADRAO",
]


class PropulsionKind(StrEnum):
    """Como a familia produz empuxo, o que decide o modelo de energia."""

    JET = "jet"
    """Empuxo direto. Consumo proporcional ao empuxo, por consumo especifico."""

    ROTOR_BATTERY = "rotor_battery"
    """Rotor eletrico. Potencia pela area de disco, energia por massa de bateria."""

    ROTOR_GENERATOR = "rotor_generator"
    """Rotor movido por gerador a combustao. Potencia pela area, energia por
    combustivel: a massa cai enquanto queima."""

    @property
    def needs_disk_area(self) -> bool:
        return self is not PropulsionKind.JET


class ScreeningStage(IntEnum):
    """Os filtros, na ordem em que sao aplicados. Valor menor, custo menor."""

    INSTALLED_THRUST = 1
    ALLOCATION_RANK = 2
    NOMINAL_TRIM = 3
    LIFTOFF = 4
    LATERAL_CG = 5
    THRUST_HEADROOM = 6
    MISSION_ENERGY = 7
    SINGLE_FAILURE = 8


@dataclass(frozen=True, slots=True)
class ArchitectureFamily:
    """Uma hipotese de arquitetura, com os poucos parametros que a definem.

    ⚠ Nenhuma familia e promessa de construcao. Sao hipoteses que **podem morrer
    cedo**, e morrer cedo e o resultado util.

    Attributes:
        dry_mass_kg: massa de tudo menos a energia embarcada, **propria da familia**.
            Rotores, motores, inversores e cabeamento de um lado; unidade de controle,
            tanques e linhas do outro. Igualar massa seca entre familias compara
            armazenamento de energia, nao arquitetura.
        unmodelled: o que esta fora do modelo nesta familia. Campo obrigatorio e nao
            vazio: uma familia sem nada por modelar seria uma familia ja concluida, e
            nenhuma esta.
    """

    code: str
    name: str
    summary: str
    geometry: PropulsionGeometry
    dry_mass_kg: float
    energy_mass_kg: float
    kind: PropulsionKind
    unmodelled: tuple[str, ...]
    disk_area_m2: float | None = None
    tsfc_kg_per_N_s: float | None = None
    chain_efficiency: float | None = None
    source: str = "hipotese parametrica, sem dado arquivado"
    notes: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if self.dry_mass_kg <= 0.0 or self.energy_mass_kg <= 0.0:
            raise ValueError(f"familia {self.code!r} com massa nao positiva")
        if not self.unmodelled:
            raise ValueError(
                f"familia {self.code!r} nao declara nada fora do modelo. Uma familia "
                "sem lacuna declarada seria uma familia concluida, e nenhuma esta."
            )
        if self.kind.needs_disk_area and not self.disk_area_m2:
            raise ValueError(f"familia {self.code!r} e de rotor e precisa de area de disco")
        if self.kind is PropulsionKind.JET and not self.tsfc_kg_per_N_s:
            raise ValueError(f"familia {self.code!r} e de jato e precisa de consumo especifico")
        if self.kind is PropulsionKind.ROTOR_GENERATOR and not self.chain_efficiency:
            raise ValueError(
                f"familia {self.code!r} e de gerador e precisa de rendimento de cadeia"
            )

    @property
    def gross_mass_kg(self) -> float:
        return self.dry_mass_kg + self.energy_mass_kg

    @property
    def installed_thrust_N(self) -> float:
        return self.geometry.total_thrust_max_N

    def storage(self) -> Storage:
        """O armazenamento de energia correspondente ao tipo de propulsao."""
        if self.kind is PropulsionKind.JET:
            return FuelStorage(
                mass_kg=self.energy_mass_kg,
                source=self.source,
                tsfc_kg_per_N_s=float(self.tsfc_kg_per_N_s),
            )
        if self.kind is PropulsionKind.ROTOR_BATTERY:
            return BatteryStorage(
                mass_kg=self.energy_mass_kg,
                source=self.source,
                rotor_disk_area_m2=float(self.disk_area_m2),
            )
        return GeneratorFuelStorage(
            mass_kg=self.energy_mass_kg,
            source=self.source,
            chain_efficiency=float(self.chain_efficiency),
            rotor_disk_area_m2=float(self.disk_area_m2),
        )


@dataclass(frozen=True, slots=True)
class ScreeningRequirements:
    """O que uma familia precisa entregar para continuar no funil.

    ⚠ Estes numeros sao **escolha declarada de campanha**, nao requisito derivado de
    uso real. Mudar um deles muda quem sobrevive, e por isso eles aparecem no
    relatorio junto do resultado.
    """

    liftoff_acceleration_m_s2: float = 0.5

    lateral_cg_tolerance_m: float = 0.02
    """Desvio lateral de centro de massa que a familia precisa equilibrar **sem
    inclinar o tronco**.

    ⚠ **Este criterio tem forma de traje, e elimina multirrotor pelo motivo errado.**

    Num traje, o corpo do piloto e a referencia: se ele levanta um braco, o centro de
    massa anda e o tronco precisa continuar de pe. Equilibrar isso exige momento de
    rolagem **sem** forca lateral, e e por isso que o criterio existe.

    Num multirrotor, nao. A resposta normal a centro de massa deslocado e **inclinar o
    veiculo inteiro** ate o empuxo passar pelo novo centro. Isso e voo normal, nao
    falha, e a aeronave nem tenta produzir rolagem pura.

    O efeito aparece no funil: um anel plano e simetrico de rotores so consegue
    rolagem pura pelo canal de **torque de reacao**, cujo coeficiente e cerca de duas
    ordens de grandeza menor que o do canal principal de empuxo. A rolagem pura
    existe, entao o filtro de posto passa, mas a janela lateral fica em milimetros e o
    filtro de centro de massa mata a familia.

    Isso e verdade e e inutil como eliminacao: diz que um multirrotor e um traje ruim,
    o que ja se sabia. Para julgar um multirrotor como multirrotor, o trim precisa
    poder inclinar, o que ``solve_trim`` ja aceita por
    ``rotation_body_from_inertial`` e este funil ainda nao usa. Ate la, familias de
    rotor mortas neste filtro contam como **nao julgadas**, nao como reprovadas.
    """
    min_thrust_headroom: float = 0.10
    min_hover_endurance_s: float = 180.0
    min_rank: int = 5
    require_pure_roll: bool = True
    tolerate_single_failure: bool = False
    mission: MissionProfile = REFERENCE_HOVER_MISSION

    def __post_init__(self) -> None:
        if not 1 <= self.min_rank <= 6:
            raise ValueError("posto minimo em [1, 6]")
        if not 0.0 <= self.min_thrust_headroom < 1.0:
            raise ValueError("folga minima em [0, 1)")


TRIAGEM_PADRAO = ScreeningRequirements()
"""Criterios de triagem da campanha atual. Singleton, para nao construir em default."""


@dataclass(frozen=True, slots=True)
class StageOutcome:
    """O que um filtro disse, e com que numero."""

    stage: ScreeningStage
    verdict: Verdict
    metric: float
    detail: str

    @property
    def passed(self) -> bool:
        return self.verdict is Verdict.SATISFIED


@dataclass(frozen=True, slots=True)
class ScreeningResult:
    """O caminho de uma familia pelo funil, ate onde ela chegou."""

    family: ArchitectureFamily
    outcomes: tuple[StageOutcome, ...]
    center_of_mass_body_m: tuple[float, float, float] | None

    @property
    def survived(self) -> bool:
        """Passou por **todos** os filtros. Nao quer dizer viavel: ver o modulo."""
        return len(self.outcomes) == len(ScreeningStage) and all(o.passed for o in self.outcomes)

    @property
    def died_at(self) -> ScreeningStage | None:
        for outcome in self.outcomes:
            if not outcome.passed:
                return outcome.stage
        return None

    @property
    def stages_cleared(self) -> int:
        return sum(1 for o in self.outcomes if o.passed)

    def metric(self, stage: ScreeningStage) -> float:
        for outcome in self.outcomes:
            if outcome.stage is stage:
                return outcome.metric
        return math.nan


def _nominal_center_of_mass(
    family: ArchitectureFamily,
) -> tuple[float, float, float] | None:
    """Meio da janela longitudinal viavel, ou ``None`` se nao houver janela."""
    janela = cg_window(
        family.geometry,
        mass_kg=family.gross_mass_kg,
        axis=0,
        span_m=(-0.60, 0.80),
        step_m=0.005,
    )
    if janela is None:
        return None
    return (0.5 * (janela[0] + janela[1]), 0.0, 0.0)


def screen_family(
    family: ArchitectureFamily,
    requirements: ScreeningRequirements = TRIAGEM_PADRAO,
) -> ScreeningResult:
    """Passa uma familia pelos filtros, **parando na primeira reprovacao**.

    Parar cedo nao e otimizacao, e disciplina de custo: rodar integracao de missao
    numa geometria que nao fecha trim produz um numero que nao significa nada e custa
    caro para produzir.
    """
    resultados: list[StageOutcome] = []
    geo = family.geometry
    bruto = family.gross_mass_kg
    peso_N = bruto * G0

    def registrar(stage: ScreeningStage, ok: bool, metric: float, detail: str) -> bool:
        resultados.append(
            StageOutcome(
                stage=stage,
                verdict=Verdict.SATISFIED if ok else Verdict.VIOLATED,
                metric=metric,
                detail=detail,
            )
        )
        return ok

    # 1. empuxo instalado contra peso. Condicao necessaria, nunca suficiente.
    razao = family.installed_thrust_N / peso_N
    if not registrar(
        ScreeningStage.INSTALLED_THRUST,
        razao >= 1.0,
        razao,
        f"soma escalar dos maximos sobre o peso: {razao:.2f}",
    ):
        return ScreeningResult(family, tuple(resultados), None)

    # 2. posto da matriz de alocacao, mais rolagem pura se exigida.
    mapa = analyse_authority(geo)
    rolagem = lateral_cg_authority(geo)
    posto_ok = mapa.rank >= requirements.min_rank and (
        rolagem or not requirements.require_pure_roll
    )
    detalhe = f"posto {mapa.rank}/6, rolagem pura {'sim' if rolagem else 'nao'}"
    if not registrar(ScreeningStage.ALLOCATION_RANK, posto_ok, float(mapa.rank), detalhe):
        return ScreeningResult(family, tuple(resultados), None)

    # 3. trim nominal, no melhor centro longitudinal que a geometria admite.
    centro = _nominal_center_of_mass(family)
    if centro is None:
        registrar(
            ScreeningStage.NOMINAL_TRIM,
            False,
            math.nan,
            "nenhuma posicao longitudinal de centro de massa admite trim",
        )
        return ScreeningResult(family, tuple(resultados), None)

    nominal = solve_trim(geo, mass_kg=bruto, center_of_mass_body_m=list(centro))
    if not registrar(
        ScreeningStage.NOMINAL_TRIM,
        nominal.feasible,
        nominal.total_thrust_N / G0,
        f"soma de empuxo {nominal.total_thrust_N / G0:.1f} kgf"
        if nominal.feasible
        else f"inviavel: {nominal.cause.value}",
    ):
        return ScreeningResult(family, tuple(resultados), centro)

    # 4. saida do chao: aceleracao vertical entra como gravidade efetiva.
    fator = (G0 + requirements.liftoff_acceleration_m_s2) / G0
    subida = solve_trim(geo, mass_kg=bruto * fator, center_of_mass_body_m=list(centro))
    if not registrar(
        ScreeningStage.LIFTOFF,
        subida.feasible,
        fator,
        f"aceleracao de {requirements.liftoff_acceleration_m_s2:.2f} m/s2 "
        + ("cabe" if subida.feasible else f"nao cabe: {subida.cause.value}"),
    ):
        return ScreeningResult(family, tuple(resultados), centro)

    # 5. tolerancia de centro de massa lateral.
    lateral = cg_window(
        geo,
        mass_kg=bruto,
        axis=1,
        span_m=(-0.20, 0.20),
        step_m=0.002,
        fixed_cg_m=centro,
    )
    meia_janela = 0.0 if lateral is None else 0.5 * (lateral[1] - lateral[0])
    if not registrar(
        ScreeningStage.LATERAL_CG,
        meia_janela >= requirements.lateral_cg_tolerance_m,
        meia_janela,
        f"tolera {meia_janela * 100:.1f} cm de desvio lateral, "
        f"exigido {requirements.lateral_cg_tolerance_m * 100:.1f} cm",
    ):
        return ScreeningResult(family, tuple(resultados), centro)

    # 6. folga de empuxo no trim de margem maxima.
    margem = solve_trim(
        geo,
        mass_kg=bruto,
        center_of_mass_body_m=list(centro),
        objective=TrimObjective.MAX_MARGIN,
    )
    folga = (
        min(1.0 - t / n.thrust_max_N for t, n in zip(margem.thrusts_N, geo.available, strict=True))
        if margem.feasible
        else 0.0
    )
    if not registrar(
        ScreeningStage.THRUST_HEADROOM,
        folga >= requirements.min_thrust_headroom,
        folga,
        f"folga superior de {folga:.1%}, exigida {requirements.min_thrust_headroom:.0%}",
    ):
        return ScreeningResult(family, tuple(resultados), centro)

    # 7. energia de missao.
    missao = evaluate_mission_energy(
        dry_mass_kg=family.dry_mass_kg,
        storage=family.storage(),
        demand=GeometricThrustDemand(geo, center_of_mass_body_m=list(centro)),
        profile=requirements.mission,
        geometry=geo,
        step_s=1.0,
    )
    autonomia = missao.hover_endurance_s
    energia_ok = (
        missao.termination_reason is not TerminationReason.TRIM_INFEASIBLE
        and autonomia >= requirements.min_hover_endurance_s
    )
    if not registrar(
        ScreeningStage.MISSION_ENERGY,
        energia_ok,
        autonomia,
        f"{autonomia / 60:.2f} min de pairado, exigido "
        f"{requirements.min_hover_endurance_s / 60:.1f} min",
    ):
        return ScreeningResult(family, tuple(resultados), centro)

    # 8. falha unica.
    falhas = single_failure_survey(geo, mass_kg=bruto, center_of_mass_body_m=list(centro))
    toleradas = sum(1 for causa in falhas.values() if causa is InfeasibilityCause.NONE)
    falha_ok = toleradas > 0 or not requirements.tolerate_single_failure
    registrar(
        ScreeningStage.SINGLE_FAILURE,
        falha_ok,
        float(toleradas),
        f"{toleradas} de {geo.count} perdas unicas ainda admitem trim",
    )
    return ScreeningResult(family, tuple(resultados), centro)


def run_funnel(
    families: tuple[ArchitectureFamily, ...],
    requirements: ScreeningRequirements = TRIAGEM_PADRAO,
) -> tuple[ScreeningResult, ...]:
    """Passa todas as familias pelo funil, preservando a ordem de entrada."""
    if not families:
        raise ValueError("funil sem nenhuma familia")
    codigos = [f.code for f in families]
    duplicados = {c for c in codigos if codigos.count(c) > 1}
    if duplicados:
        raise ValueError(f"codigos de familia duplicados: {sorted(duplicados)}")
    return tuple(screen_family(f, requirements) for f in families)


def survivors(results: tuple[ScreeningResult, ...]) -> tuple[ScreeningResult, ...]:
    """As que passaram por todos os filtros. **Candidatas, nao aprovadas.**"""
    return tuple(r for r in results if r.survived)


def mortality_by_stage(
    results: tuple[ScreeningResult, ...],
) -> dict[ScreeningStage, int]:
    """Quantas familias morreram em cada estagio. Diz qual filtro esta mordendo."""
    contagem = dict.fromkeys(ScreeningStage, 0)
    for resultado in results:
        morte = resultado.died_at
        if morte is not None:
            contagem[morte] += 1
    return contagem
