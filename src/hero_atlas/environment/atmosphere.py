"""Atmosfera padrao com desvio de temperatura, sem dupla contagem.

Ver vault/04 - Fisica/Atmosfera.md

    Densidade ja depende de temperatura, porque rho = p / (R * T). Multiplicar razao
    de densidade por uma penalidade termica generica penaliza a mesma fisica duas
    vezes.

A forma correta e calcular o estado atmosferico completo primeiro, e so depois
aplicar o que a densidade **nao** cobre: o efeito residual de limite de temperatura
de entrada da turbina.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

from ..units import (
    G0,
    P_SEA_LEVEL_ISA,
    R_DRY_AIR,
    RHO_SEA_LEVEL_ISA,
    T_SEA_LEVEL_ISA,
)

__all__ = [
    "LAPSE_RATE_K_PER_M",
    "TROPOPAUSE_M",
    "AtmosphereState",
    "Scenario",
    "isa",
    "density_ratio",
    "SCENARIOS",
]

LAPSE_RATE_K_PER_M: float = 6.5e-3
"""Gradiente termico da troposfera padrao [K/m]."""

TROPOPAUSE_M: float = 11_000.0
"""Limite de validade do modelo linear. Muito acima de qualquer coisa deste projeto."""


@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Estado completo do ar num ponto.

    Attributes:
        altitude_m: altitude geopotencial.
        delta_isa_K: desvio de temperatura em relacao a atmosfera padrao.
        temperature_K: temperatura resultante.
        pressure_Pa: pressao, que **nao** depende do desvio de temperatura.
        density_kg_m3: densidade, que depende dos dois.
    """

    altitude_m: float
    delta_isa_K: float
    temperature_K: float
    pressure_Pa: float
    density_kg_m3: float

    @property
    def density_ratio(self) -> float:
        """Densidade relativa ao nivel do mar em atmosfera padrao."""
        return self.density_kg_m3 / RHO_SEA_LEVEL_ISA

    @property
    def speed_of_sound_m_s(self) -> float:
        return math.sqrt(1.4 * R_DRY_AIR * self.temperature_K)


def isa(altitude_m: float = 0.0, delta_isa_K: float = 0.0) -> AtmosphereState:
    """Estado atmosferico a uma altitude, com desvio de temperatura opcional.

    A pressao vem do perfil padrao e **nao** e alterada pelo desvio: um dia quente
    nao muda a coluna de ar acima, muda a densidade dela. Por isso o desvio entra
    apenas via temperatura na equacao de estado.

    Args:
        altitude_m: altitude geopotencial, valida ate a tropopausa.
        delta_isa_K: quanto mais quente que o padrao. Use ``15.0`` para ISA+15.
    """
    if not 0.0 <= altitude_m <= TROPOPAUSE_M:
        raise ValueError(f"altitude {altitude_m} m fora do modelo troposferico [0, {TROPOPAUSE_M}]")

    temperature_isa = T_SEA_LEVEL_ISA - LAPSE_RATE_K_PER_M * altitude_m
    exponent = G0 / (R_DRY_AIR * LAPSE_RATE_K_PER_M)
    pressure = P_SEA_LEVEL_ISA * (temperature_isa / T_SEA_LEVEL_ISA) ** exponent

    temperature = temperature_isa + delta_isa_K
    if temperature <= 0.0:
        raise ValueError(f"temperatura absoluta nao positiva: {temperature} K")

    return AtmosphereState(
        altitude_m=altitude_m,
        delta_isa_K=delta_isa_K,
        temperature_K=temperature,
        pressure_Pa=pressure,
        density_kg_m3=pressure / (R_DRY_AIR * temperature),
    )


def density_ratio(altitude_m: float = 0.0, delta_isa_K: float = 0.0) -> float:
    """Atalho para a razao de densidade, que e o fator que interessa ao empuxo."""
    return isa(altitude_m, delta_isa_K).density_ratio


class Scenario(StrEnum):
    """Cenarios nomeados, cada um calculado. Nao existe um 'nominal' ambiguo.

    Ver vault/04 - Fisica/Atmosfera.md: a distribuicao de perda ambiental nasce de
    cenario fisico, nao de preferencia narrativa.
    """

    REFERENCE = "reference"
    MISSION_NOMINAL = "mission_nominal"
    HOT_DAY = "hot_day"
    ADVERSE = "adverse"


SCENARIOS: dict[Scenario, AtmosphereState] = {
    Scenario.REFERENCE: isa(0.0, 0.0),
    Scenario.MISSION_NOMINAL: isa(1000.0, 0.0),
    Scenario.HOT_DAY: isa(1000.0, 15.0),
    Scenario.ADVERSE: isa(2000.0, 20.0),
}
"""Os cenarios do projeto, prontos.

``REFERENCE`` vale 1,00 de razao de densidade por definicao. Os outros sao
calculados, nunca arbitrados.
"""
