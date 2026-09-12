"""Energia por missao: quanto custa sair do chao, e quanto tempo se fica no ar.

Ver vault/04 - Fisica/Autonomia e energia.md

Tres perguntas **diferentes**, que o vocabulario solto de "autonomia" funde e que
este modulo separa:

===========================  ==========================================================
pergunta                     o que e calculado
===========================  ==========================================================
consegue sair do chao?       existe ``T`` dentro dos limites que produz o wrench com
                             aceleracao vertical pedida. **Nao** e "empuxo total maior
                             que o peso": e existencia de trim, ver ADR-002
quanto custa sair do chao?   energia ou combustivel integrado na trajetoria declarada
quanto tempo fica no ar?     energia util embarcada dividida pelo consumo ao longo da
                             missao, ate a reserva
===========================  ==========================================================

⚠ Sair do chao e barato; **sustentar massa no ar e o que custa**. Um perfil de
missao que confunde os dois produz numero de decolagem inflado e autonomia otimista.

A comparacao justa entre eletrico e combustao **nao** e "10 litros contra uma bateria
qualquer". E: com a **mesma massa embarcada de energia**, a mesma geometria, a mesma
massa seca, o mesmo piloto, a mesma reserva e a mesma missao, quanto tempo cada
arquitetura entrega. Ver :func:`compare_storage`.

⚠ **E isso compara armazenamento de energia, nao arquiteturas completas.** Manter a
massa seca igual entre as familias e o que torna a comparacao controlada, e e tambem
o que a limita: na pratica as massas secas **nao** sao iguais.

============================  ==========================================================
familia                       massa que so ela carrega
============================  ==========================================================
eletrico distribuido          rotores, motores, inversores, barramento, gerenciamento de
                              bateria, cabeamento de alta corrente, estrutura de suporte
turbina direta                microturbinas, unidade de controle, tanques, linhas,
                              bombas, protecao termica, estrutura
hibrido serie                 gerador, eletronica de potencia, buffer, motores, cabos,
                              tanque, controle termico
turbina com buffer            turbina, buffer, eletronica, atuadores auxiliares,
                              estrutura e protecao termica
============================  ==========================================================

O titulo tecnicamente exato do experimento e **"comparacao de energia armazenada sob
massa seca e geometria fixadas"**, e nao "comparacao entre arquitetura eletrica e
arquitetura a combustao". A diferenca de massa seca por familia esta registrada como
incognita bloqueante em :mod:`hero_atlas.propulsion_family`.

Duas assimetrias fisicas que o modelo precisa capturar, e captura:

1. **Eletrico**: a massa nao cai. Cada quilo de bateria e carregado do inicio ao fim,
   e como ``P ~ T^1.5`` a autonomia cresce menos que a massa de bateria. Ver
   :func:`hero_atlas.analysis.energy.optimal_battery_mass_kg`.
2. **Combustao**: a massa cai enquanto queima, entao o empuxo de pairado cai, entao o
   fluxo cai. O efeito e favoravel e **se realimenta**.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..airframe.geometry import PropulsionGeometry
from ..model_status import PROPULSAO_INSTALADA_HOJE, ModelStatus
from ..units import G0, RHO_SEA_LEVEL_ISA
from ..verdict import Verdict
from .energy import FIGURE_OF_MERIT_DEFAULT, MOTOR_EFFICIENCY_DEFAULT
from .trim import TrimObjective, solve_trim

__all__ = [
    "MissionPhase",
    "MissionProfile",
    "BatteryStorage",
    "FuelStorage",
    "GeneratorFuelStorage",
    "Storage",
    "ThrustDemand",
    "ScalarThrustDemand",
    "GeometricThrustDemand",
    "TerminationReason",
    "MissionEnergyResult",
    "evaluate_mission_energy",
    "compare_storage",
    "JET_A_SPECIFIC_ENERGY_J_KG",
    "REFERENCE_HOVER_MISSION",
]

JET_A_SPECIFIC_ENERGY_J_KG: float = 43.0e6
"""Energia quimica de querosene de aviacao, ordem de grandeza.

⚠ Serve **so** para exibir a energia embarcada nas duas arquiteturas na mesma
unidade. Nao e comparavel com energia de bateria como energia util: a turbina
converte uma fracao pequena disso em empuxo, e essa fracao esta embutida no consumo
especifico, nao aqui. Comparar 43 MJ/kg com 180 Wh/kg diretamente e o erro classico.
"""


class TerminationReason(StrEnum):
    """Por que a missao acabou. Distinguir isto de 'autonomia' e o ponto do modulo."""

    COMPLETED = "completed"
    RESERVE_REACHED = "reserve_reached"
    TRIM_INFEASIBLE = "trim_infeasible"
    STORAGE_EXHAUSTED = "storage_exhausted"


@dataclass(frozen=True, slots=True)
class MissionPhase:
    """Uma fase de voo, declarada por aceleracao ou por velocidade vertical.

    ⚠ Velocidade vertical constante **nao** consome empuxo extra neste modelo: em
    regime permanente a aceleracao e nula e o empuxo requerido e o de pairado. O que
    custa empuxo extra e a **aceleracao**. Tratar subida a velocidade constante como
    se exigisse empuxo proporcional a velocidade e um erro comum, e este modelo nao o
    comete. O custo aerodinamico de subir entra quando houver modelo de arrasto, e
    hoje nao ha: por isso ``vertical_speed_m_s`` e registrado e nao usado na conta de
    empuxo.
    """

    name: str
    duration_s: float | None
    vertical_acceleration_m_s2: float = 0.0
    vertical_speed_m_s: float = 0.0

    def __post_init__(self) -> None:
        if self.duration_s is not None and self.duration_s <= 0.0:
            raise ValueError(f"fase {self.name!r} com duracao nao positiva")
        if not math.isfinite(self.vertical_acceleration_m_s2):
            raise ValueError(f"fase {self.name!r} com aceleracao nao finita")
        if self.vertical_acceleration_m_s2 <= -G0:
            raise ValueError(
                f"fase {self.name!r} pede aceleracao {self.vertical_acceleration_m_s2} m/s2, "
                "que anula ou inverte o peso efetivo. Queda livre nao precisa de empuxo "
                "e nao e modelavel como trim."
            )

    @property
    def open_ended(self) -> bool:
        """Se a fase dura ate a reserva acabar. E a fase que mede autonomia."""
        return self.duration_s is None


@dataclass(frozen=True, slots=True)
class MissionProfile:
    """Sequencia de fases mais a reserva.

    Attributes:
        reserve_fraction: fracao da energia util que **nao** pode ser gasta. A missao
            termina quando o restante chega nela, nao quando chega a zero.
    """

    phases: tuple[MissionPhase, ...]
    reserve_fraction: float = 0.20

    def __post_init__(self) -> None:
        if not self.phases:
            raise ValueError("missao sem nenhuma fase")
        if not 0.0 <= self.reserve_fraction < 1.0:
            raise ValueError("reserve_fraction em [0, 1)")
        abertas = [f.name for f in self.phases if f.open_ended]
        if len(abertas) > 1:
            raise ValueError(
                f"missao com mais de uma fase aberta: {abertas}. Duas fases 'ate a "
                "reserva' nao tem ordem definida de termino."
            )
        if abertas and not self.phases[-1].open_ended:
            primeira_aberta = next(i for i, f in enumerate(self.phases) if f.open_ended)
            posteriores = [f.name for f in self.phases[primeira_aberta + 1 :]]
            raise ValueError(
                f"fases {posteriores} vem depois da fase aberta {abertas[0]!r} e "
                "**nunca executam**: a fase aberta so termina quando a reserva acaba, "
                "e nesse instante a missao encerra. Declarar uma descida ali produz "
                "um perfil que parece operacional e nao e. Ou a fase aberta e a "
                "ultima, ou toda fase tem duracao."
            )


REFERENCE_HOVER_MISSION = MissionProfile(
    phases=(
        MissionPhase("arranque_e_saida_do_chao", duration_s=3.0, vertical_acceleration_m_s2=0.5),
        MissionPhase("subida", duration_s=10.0, vertical_speed_m_s=1.0),
        MissionPhase("pairado", duration_s=None),
    ),
    reserve_fraction=0.20,
)
"""Missao de referencia. ⚠ Valores **declarados**, nao derivados de requisito real.

⚠ **Nao ha fase de descida, e a ausencia e deliberada.** Uma versao anterior declarava
descida depois do pairado aberto, e essa fase **nunca executava**: o pairado aberto so
termina quando a reserva acaba, e nesse instante a missao encerra. O perfil parecia
operacional e nao era.

A autonomia que este perfil mede e, portanto:

    tempo de pairado ate a reserva, **sem** reserva separada de descida ou retorno.

Quem quiser uma missao com descida garantida tem duas rotas: dar duracao fixa ao
pairado, ou aumentar ``reserve_fraction`` ate cobrir a energia da descida declarada.
A segunda rota continua sendo uma escolha do analista, nao um calculo deste modulo."""


# ---------------------------------------------------------------------------
# Armazenamento de energia
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BatteryStorage:
    """Bateria. A massa **nao** cai durante o voo.

    Attributes:
        specific_energy_Wh_kg: energia especifica do **pack**, nao da celula.
        pack_efficiency: perdas eletricas ate o barramento.
        depth_of_discharge: fracao utilizavel antes do joelho de tensao.
        auxiliary_power_W: eletronica, controle e cargas declaradas.
        source: procedencia em uma linha. Obrigatoria, conforme a disciplina do
            projeto: parametro de energia entra no mesmo regime dos de motor.
    """

    mass_kg: float
    source: str
    specific_energy_Wh_kg: float = 180.0
    pack_efficiency: float = 0.95
    depth_of_discharge: float = 0.85
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT
    inverter_efficiency: float = 0.97
    auxiliary_power_W: float = 150.0
    rotor_disk_area_m2: float = 0.55

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            raise ValueError("massa de bateria precisa ser positiva")
        if not self.source.strip():
            raise ValueError(
                "armazenamento sem procedencia declarada. Energia especifica sem "
                "fonte e o mesmo defeito que empuxo sem ficha tecnica."
            )
        for nome in (
            "pack_efficiency",
            "depth_of_discharge",
            "figure_of_merit",
            "motor_efficiency",
            "inverter_efficiency",
        ):
            valor = getattr(self, nome)
            if not 0.0 < valor <= 1.0:
                raise ValueError(f"{nome} precisa estar em (0, 1]")
        if self.rotor_disk_area_m2 <= 0.0:
            raise ValueError("area de disco precisa ser positiva")

    @property
    def usable_energy_J(self) -> float:
        """``m * e * eta_pack * DoD``, em joule."""
        return (
            self.mass_kg
            * self.specific_energy_Wh_kg
            * 3600.0
            * self.pack_efficiency
            * self.depth_of_discharge
        )

    @property
    def embarked_energy_J(self) -> float:
        """Energia nominal embarcada, antes de rendimento e profundidade de descarga."""
        return self.mass_kg * self.specific_energy_Wh_kg * 3600.0

    def consumes_mass(self) -> bool:
        return False

    def power_W(self, thrusts_N: NDArray[np.float64], density_kg_m3: float) -> float:
        """Potencia eletrica instantanea, somada **rotor a rotor**.

        ⚠ A soma e por rotor, e nao ``(soma T)^1.5 / sqrt(2 rho A_total)``. Como a
        potencia induzida e convexa em empuxo, as duas so coincidem com empuxos
        iguais, e o trim real distribui desigual. Usar a forma agregada subestima a
        potencia sempre que a distribuicao e assimetrica.
        """
        area_por_rotor = self.rotor_disk_area_m2 / max(thrusts_N.size, 1)
        induzida = float(
            np.sum(np.power(np.maximum(thrusts_N, 0.0), 1.5))
            / math.sqrt(2.0 * density_kg_m3 * area_por_rotor)
        )
        cadeia = self.figure_of_merit * self.motor_efficiency * self.inverter_efficiency
        return induzida / cadeia + self.auxiliary_power_W


@dataclass(frozen=True, slots=True)
class FuelStorage:
    """Combustivel. A massa **cai** durante o voo, e o empuxo requerido cai junto.

    Attributes:
        tsfc_kg_per_N_s: consumo especifico ja em SI.

            ⚠ Catalogo publica em quilograma por quilograma-forca por hora, e a
            conversao e obrigatoria. E o valor de catalogo e medido perto do
            **maximo**: em pairado a fracao de empuxo e outra, e o consumo especifico
            tende a piorar. Resultado e ponto, nao banda.
    """

    mass_kg: float
    source: str
    tsfc_kg_per_N_s: float
    specific_energy_J_kg: float = JET_A_SPECIFIC_ENERGY_J_KG

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            raise ValueError("massa de combustivel precisa ser positiva")
        if self.tsfc_kg_per_N_s <= 0.0:
            raise ValueError("consumo especifico precisa ser positivo")
        if not self.source.strip():
            raise ValueError("armazenamento sem procedencia declarada")

    @property
    def usable_energy_J(self) -> float:
        """Massa utilizavel em joule quimico. Ver :data:`JET_A_SPECIFIC_ENERGY_J_KG`."""
        return self.mass_kg * self.specific_energy_J_kg

    @property
    def embarked_energy_J(self) -> float:
        return self.usable_energy_J

    def consumes_mass(self) -> bool:
        return True

    def mass_flow_kg_s(
        self,
        thrusts_N: NDArray[np.float64],
        density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    ) -> float:
        """``mdot = TSFC * soma dos empuxos``. Linear, ao contrario do eletrico.

        ``density_kg_m3`` entra so para a assinatura casar com
        :class:`GeneratorFuelStorage`, onde o consumo depende de potencia e portanto
        de densidade. Aqui o consumo especifico ja e um numero de ensaio e o modelo
        nao o corrige por altitude: fazer isso exigiria a familia de curvas do deck,
        que nao existe.
        """
        del density_kg_m3
        return self.tsfc_kg_per_N_s * float(np.sum(thrusts_N))


@dataclass(frozen=True, slots=True)
class GeneratorFuelStorage:
    """Combustivel que alimenta um gerador, que alimenta rotores. Hibrido serie.

    A diferenca em relacao a :class:`FuelStorage` e onde o combustivel entra. Ali o
    consumo e proporcional ao **empuxo**, porque o bocal queima direto. Aqui o consumo
    e proporcional a **potencia eletrica**, porque o que queima e o gerador::

        P_eletrica = potencia induzida rotor a rotor / (FM * eta_motor * eta_inversor)
        mdot       = P_eletrica / ( eta_cadeia * e_combustivel )

    ⚠ E por isso que "resolve energia, nao area" era uma frase errada sobre este ramo.
    A area de disco continua limitando a **potencia**, exatamente como no eletrico
    puro, e o hibrido serie nao melhora isso em nada. O que ele ataca e outro teto: no
    eletrico a autonomia satura porque bateria e massa carregada do inicio ao fim,
    enquanto aqui a massa **cai** enquanto queima e a energia especifica e uma ordem de
    grandeza maior.

    Attributes:
        chain_efficiency: rendimento composto de combustivel quimico ate energia
            eletrica no barramento, ou seja gerador mais retificacao mais conversao.

            ⚠ E o parametro que decide o ramo, junto da massa do conjunto, e **nao ha
            dado arquivado**. Entra como sensibilidade, nunca como valor de projeto.
    """

    mass_kg: float
    source: str
    chain_efficiency: float
    rotor_disk_area_m2: float
    specific_energy_J_kg: float = JET_A_SPECIFIC_ENERGY_J_KG
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT
    inverter_efficiency: float = 0.97
    auxiliary_power_W: float = 150.0

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            raise ValueError("massa de combustivel precisa ser positiva")
        if not self.source.strip():
            raise ValueError("armazenamento sem procedencia declarada")
        if self.rotor_disk_area_m2 <= 0.0:
            raise ValueError("area de disco precisa ser positiva")
        for nome in (
            "chain_efficiency",
            "figure_of_merit",
            "motor_efficiency",
            "inverter_efficiency",
        ):
            valor = getattr(self, nome)
            if not 0.0 < valor <= 1.0:
                raise ValueError(f"{nome} precisa estar em (0, 1]")

    @property
    def usable_energy_J(self) -> float:
        """Energia **eletrica** entregavel, ja descontada a cadeia de conversao."""
        return self.mass_kg * self.specific_energy_J_kg * self.chain_efficiency

    @property
    def embarked_energy_J(self) -> float:
        """Energia quimica embarcada, antes da cadeia."""
        return self.mass_kg * self.specific_energy_J_kg

    def consumes_mass(self) -> bool:
        return True

    def power_W(self, thrusts_N: NDArray[np.float64], density_kg_m3: float) -> float:
        """Potencia eletrica de barramento, somada rotor a rotor."""
        area_por_rotor = self.rotor_disk_area_m2 / max(thrusts_N.size, 1)
        induzida = float(
            np.sum(np.power(np.maximum(thrusts_N, 0.0), 1.5))
            / math.sqrt(2.0 * density_kg_m3 * area_por_rotor)
        )
        cadeia = self.figure_of_merit * self.motor_efficiency * self.inverter_efficiency
        return induzida / cadeia + self.auxiliary_power_W

    def mass_flow_kg_s(
        self,
        thrusts_N: NDArray[np.float64],
        density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    ) -> float:
        """Consumo de combustivel, proporcional a **potencia** e nao ao empuxo."""
        potencia = self.power_W(thrusts_N, density_kg_m3)
        return potencia / (self.chain_efficiency * self.specific_energy_J_kg)


Storage = BatteryStorage | FuelStorage | GeneratorFuelStorage


# ---------------------------------------------------------------------------
# De massa efetiva para empuxo por propulsor
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ThrustDemand:
    """Empuxo por propulsor exigido por uma massa e uma aceleracao vertical."""

    feasible: bool
    thrusts_N: NDArray[np.float64]
    total_N: float
    reason: str = ""


class ScalarThrustDemand:
    """Modelo escalar: ``T_total = m (g + a_z) / razao_de_projecao``.

    Existe para **verificacao**, nao para producao: com ele a autonomia de turbina
    tem solucao fechada e o integrador pode ser conferido contra ela. Ver
    :func:`hero_atlas.analysis.energy.turbine_endurance_s`.
    """

    def __init__(self, *, projection_ratio: float, nozzle_count: int = 1) -> None:
        if not 0.0 < projection_ratio <= 1.0:
            raise ValueError("razao de projecao em (0, 1]")
        if nozzle_count < 1:
            raise ValueError("pelo menos um propulsor")
        self.projection_ratio = projection_ratio
        self.nozzle_count = nozzle_count

    def __call__(self, mass_kg: float, vertical_acceleration_m_s2: float) -> ThrustDemand:
        total = mass_kg * (G0 + vertical_acceleration_m_s2) / self.projection_ratio
        return ThrustDemand(
            feasible=True,
            thrusts_N=np.full(self.nozzle_count, total / self.nozzle_count),
            total_N=total,
        )


class GeometricThrustDemand:
    """Modelo real: resolve o trim da geometria a cada avaliacao.

    ⚠ Aceleracao vertical entra como **gravidade efetiva**. Sob aceleracao puramente
    vertical no referencial nivelado, o problema e identico ao pairado com
    ``g_ef = g + a_z``, o que preserva o momento do peso sobre o ponto de referencia,
    conforme ADR-002. Escalar so a forca vertical e deixar o momento com ``g`` seria
    inconsistente e daria trim errado com centro de massa deslocado.
    """

    def __init__(
        self,
        geometry: PropulsionGeometry,
        *,
        center_of_mass_body_m: ArrayLike,
        objective: TrimObjective = TrimObjective.MIN_THRUST,
    ) -> None:
        self.geometry = geometry
        self.center_of_mass_body_m = np.asarray(center_of_mass_body_m, dtype=np.float64)
        self.objective = objective

    def __call__(self, mass_kg: float, vertical_acceleration_m_s2: float) -> ThrustDemand:
        massa_equivalente = mass_kg * (G0 + vertical_acceleration_m_s2) / G0
        solucao = solve_trim(
            self.geometry,
            mass_kg=massa_equivalente,
            center_of_mass_body_m=self.center_of_mass_body_m,
            objective=self.objective,
        )
        if solucao.status is not Verdict.SATISFIED:
            return ThrustDemand(
                feasible=False,
                thrusts_N=np.zeros(0),
                total_N=0.0,
                reason=f"trim inviavel a {massa_equivalente:.1f} kg equivalentes: "
                f"{solucao.cause.value}",
            )
        return ThrustDemand(
            feasible=True,
            thrusts_N=solucao.thrusts_N,
            total_N=solucao.total_thrust_N,
        )


# ---------------------------------------------------------------------------
# Resultado
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MissionEnergyResult:
    """O que a missao consumiu, e por que parou."""

    mission_completed: bool
    termination_reason: TerminationReason
    termination_detail: str
    takeoff_energy_J: float
    takeoff_storage_used_kg: float
    hover_endurance_s: float
    mission_endurance_s: float
    storage_remaining_kg: float
    energy_remaining_J: float
    peak_power_W: float | None
    peak_fuel_flow_kg_s: float | None
    min_upper_thrust_headroom_ratio: float
    """Menor folga **superior** de empuxo entre os propulsores: ``min_i (1 - T_i/T_i_max)``.

    ⚠ **Isto nao e a margem estatica de wrench do projeto.** Mede so a distancia ao
    teto do propulsor mais carregado, e ignora ``T_min``, as direcoes possiveis de
    variacao, a geometria da matriz de alocacao, a assimetria de autoridade, o wrench
    exigido e a distancia a fronteira do conjunto atingivel. Tambem nao diz nada
    sobre autoridade **dinamica**, que depende de rampa e atraso.

    **O que zero aqui significa, exatamente.** Pelo menos um propulsor esta no teto,
    entao o conjunto de variacoes admissiveis de empuxo perdeu uma direcao: aquele
    bocal so pode descer. Isso e **evidencia de saturacao local**, e nada alem disso.

    ⚠ Nao e condicao **suficiente** para perda de autoridade: os outros propulsores
    continuam podendo subir, e o wrench desejado pode continuar atingivel por eles.

    ⚠ E tambem **nao e condicao necessaria**: uma geometria de posto deficiente perde
    direcoes de wrench com **todos** os propulsores longe do teto. Saturacao e falta de
    posto sao mecanismos distintos de perda de autoridade, e esta grandeza so enxerga o
    primeiro.

    Perda de um wrench especifico tem que ser demonstrada pela margem de wrench ou pela
    alocacao sob restricoes, em :mod:`hero_atlas.analysis.authority`, nunca inferida
    daqui.
    """
    initial_gross_kg: float
    final_gross_kg: float
    model_status: ModelStatus = PROPULSAO_INSTALADA_HOJE
    phase_durations_s: tuple[tuple[str, float], ...] = field(default=())

    @property
    def hover_endurance_min(self) -> float:
        return self.hover_endurance_s / 60.0

    @property
    def mission_endurance_min(self) -> float:
        return self.mission_endurance_s / 60.0


def _upper_headroom_ratio(
    thrusts_N: NDArray[np.float64], geometry: PropulsionGeometry | None
) -> float:
    """Folga superior do propulsor mais carregado: ``min_i (1 - T_i/T_i_max)``.

    Ver o atributo homonimo de :class:`MissionEnergyResult` para o que isto **nao**
    mede."""
    if geometry is None or thrusts_N.size == 0:
        return math.nan
    tetos = np.array([n.thrust_max_N for n in geometry.available], dtype=np.float64)
    if tetos.size != thrusts_N.size:
        return math.nan
    return float(np.min(1.0 - thrusts_N / tetos))


def evaluate_mission_energy(
    *,
    dry_mass_kg: float,
    storage: Storage,
    demand: Callable[[float, float], ThrustDemand],
    profile: MissionProfile = REFERENCE_HOVER_MISSION,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    geometry: PropulsionGeometry | None = None,
    step_s: float = 0.25,
    open_phase_limit_s: float = 7200.0,
) -> MissionEnergyResult:
    """Integra a missao e devolve o que foi consumido, fase a fase.

    A integracao e de Runge-Kutta de quarta ordem sobre o estado de armazenamento,
    que e escalar: massa de combustivel para :class:`FuelStorage`, energia gasta para
    :class:`BatteryStorage`. Ela e conferida contra a solucao fechada de
    :func:`hero_atlas.analysis.energy.turbine_endurance_s` na suite de validacao.

    ⚠ **Trim inviavel encerra a missao antes de integrar energia.** Nao existe
    autonomia para uma condicao que nao consegue sequer equilibrar, e reportar tempo
    de voo para um estado sem equilibrio seria pior que reportar nada.
    """
    if dry_mass_kg <= 0.0:
        raise ValueError("massa seca precisa ser positiva")
    if step_s <= 0.0:
        raise ValueError("passo precisa ser positivo")

    consome_massa = storage.consumes_mass()
    energia_util = storage.usable_energy_J
    energia_reservada = energia_util * profile.reserve_fraction

    massa_armazenada = storage.mass_kg
    massa_reservada = storage.mass_kg * profile.reserve_fraction
    energia_gasta = 0.0

    bruto_inicial = dry_mass_kg + storage.mass_kg
    pico_potencia: float | None = None
    pico_fluxo: float | None = None
    margem_minima = math.inf
    energia_decolagem = 0.0
    massa_decolagem = 0.0
    duracoes: list[tuple[str, float]] = []

    razao = TerminationReason.COMPLETED
    detalhe = ""
    tempo_total = 0.0
    pairado = 0.0
    parou = False

    def consumo(massa_armazenada_kg: float, aceleracao: float) -> tuple[float, ThrustDemand]:
        """Taxa de consumo e o empuxo que a produziu. kg/s ou J/s conforme o caso."""
        bruto = dry_mass_kg + massa_armazenada_kg
        pedido = demand(bruto, aceleracao)
        if not pedido.feasible:
            return math.nan, pedido
        if consome_massa:
            return storage.mass_flow_kg_s(pedido.thrusts_N, density_kg_m3), pedido
        return storage.power_W(pedido.thrusts_N, density_kg_m3), pedido

    for fase in profile.phases:
        if parou:
            duracoes.append((fase.name, 0.0))
            continue

        limite = open_phase_limit_s if fase.open_ended else float(fase.duration_s)
        decorrido = 0.0
        eh_decolagem = not fase.open_ended and fase is profile.phases[0]

        while decorrido < limite - 1e-12:
            dt = min(step_s, limite - decorrido)

            # Runge-Kutta de quarta ordem sobre o escalar de armazenamento.
            estado = massa_armazenada if consome_massa else energia_gasta
            # ⚠ A massa embarcada entra na massa bruta nos **dois** casos. Para
            # bateria ela e constante, nao ausente: uma versao anterior passava zero
            # aqui e subestimava o empuxo de pairado, inflando a autonomia eletrica
            # por um fator (m_bruto/m_seco)^1.5, ou seja 37 por cento no caso de
            # referencia. O erro favorecia justamente a arquitetura que o projeto
            # estava prestes a descartar.
            restante = massa_armazenada if consome_massa else storage.mass_kg

            k1, pedido = consumo(restante, fase.vertical_acceleration_m_s2)
            if math.isnan(k1):
                razao, detalhe, parou = TerminationReason.TRIM_INFEASIBLE, pedido.reason, True
                break

            if consome_massa:
                k2, _ = consumo(restante - 0.5 * dt * k1, fase.vertical_acceleration_m_s2)
                k3, _ = consumo(restante - 0.5 * dt * k2, fase.vertical_acceleration_m_s2)
                k4, _ = consumo(restante - dt * k3, fase.vertical_acceleration_m_s2)
                if any(math.isnan(k) for k in (k2, k3, k4)):
                    razao, detalhe, parou = (
                        TerminationReason.TRIM_INFEASIBLE,
                        "trim inviavel dentro do passo",
                        True,
                    )
                    break
                delta = dt * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
                massa_armazenada = estado - delta
                gasto_passo = delta
                pico_fluxo = k1 if pico_fluxo is None else max(pico_fluxo, k1)
            else:
                delta = dt * k1  # potencia nao depende do estado: massa constante
                energia_gasta = estado + delta
                gasto_passo = delta
                pico_potencia = k1 if pico_potencia is None else max(pico_potencia, k1)

            margem_minima = min(margem_minima, _upper_headroom_ratio(pedido.thrusts_N, geometry))

            if eh_decolagem:
                if consome_massa:
                    massa_decolagem += gasto_passo
                    energia_decolagem += gasto_passo * storage.specific_energy_J_kg
                else:
                    energia_decolagem += gasto_passo
                    massa_decolagem = 0.0

            decorrido += dt
            tempo_total += dt
            if fase.open_ended:
                pairado += dt

            esgotou = (
                massa_armazenada <= massa_reservada
                if consome_massa
                else energia_gasta >= energia_util - energia_reservada
            )
            if esgotou:
                razao = TerminationReason.RESERVE_REACHED
                detalhe = (
                    f"reserva de {profile.reserve_fraction:.0%} atingida na fase {fase.name!r}"
                )
                parou = True
                break

        duracoes.append((fase.name, decorrido))

    if not parou and any(f.open_ended for f in profile.phases):
        razao = TerminationReason.COMPLETED
        detalhe = f"fase aberta atingiu o limite de {open_phase_limit_s} s sem esgotar a reserva"

    restante_massa = massa_armazenada if consome_massa else storage.mass_kg
    restante_energia = (
        massa_armazenada * storage.specific_energy_J_kg
        if consome_massa
        else energia_util - energia_gasta
    )

    return MissionEnergyResult(
        mission_completed=razao is TerminationReason.COMPLETED,
        termination_reason=razao,
        termination_detail=detalhe,
        takeoff_energy_J=energia_decolagem,
        takeoff_storage_used_kg=massa_decolagem,
        hover_endurance_s=pairado,
        mission_endurance_s=tempo_total,
        storage_remaining_kg=restante_massa,
        energy_remaining_J=restante_energia,
        peak_power_W=pico_potencia,
        peak_fuel_flow_kg_s=pico_fluxo,
        min_upper_thrust_headroom_ratio=(math.nan if margem_minima is math.inf else margem_minima),
        initial_gross_kg=bruto_inicial,
        final_gross_kg=dry_mass_kg + restante_massa,
        phase_durations_s=tuple(duracoes),
    )


def compare_storage(
    *,
    dry_mass_kg: float,
    energy_masses_kg: tuple[float, ...],
    battery_factory: Callable[[float], BatteryStorage],
    fuel_factory: Callable[[float], FuelStorage],
    demand_factory: Callable[[], Callable[[float, float], ThrustDemand]],
    profile: MissionProfile = REFERENCE_HOVER_MISSION,
    geometry: PropulsionGeometry | None = None,
    step_s: float = 0.25,
) -> tuple[tuple[float, MissionEnergyResult, MissionEnergyResult], ...]:
    """Roda a mesma missao para as duas arquiteturas, com a **mesma massa embarcada**.

    Devolve, para cada massa de energia, o par ``(eletrico, combustivel)``. Tudo o
    mais e identico por construcao: geometria, massa seca, reserva e perfil.
    """
    saida = []
    for massa in energy_masses_kg:
        eletrico = evaluate_mission_energy(
            dry_mass_kg=dry_mass_kg,
            storage=battery_factory(massa),
            demand=demand_factory(),
            profile=profile,
            geometry=geometry,
            step_s=step_s,
        )
        combustivel = evaluate_mission_energy(
            dry_mass_kg=dry_mass_kg,
            storage=fuel_factory(massa),
            demand=demand_factory(),
            profile=profile,
            geometry=geometry,
            step_s=step_s,
        )
        saida.append((massa, eletrico, combustivel))
    return tuple(saida)
