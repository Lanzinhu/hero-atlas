"""Autonomia: turbina integrada e eletrico pela teoria do disco atuador.

Ver vault/04 - Fisica/Autonomia e energia.md

Duas leis diferentes, e a diferenca entre elas e o resultado mais interessante do
estudo:

- turbina: autonomia cai com o consumo especifico, e a massa cai enquanto queima
- eletrico: autonomia e funcao da **area do disco**, nao da bateria

    P/T = sqrt(L / (2*rho)) / (FM * eta)     com  L = T/A  (carga de disco)

Como ``P`` cresce com ``m^1.5``, cada quilo de bateria carrega a si mesmo. Triplicar
a bateria so dobra a autonomia. Nao existe "mochila eletrica de 30 minutos"; existe
"aeronave de 3 m de diametro de 30 minutos".
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..units import G0, RHO_SEA_LEVEL_ISA

__all__ = [
    "FIGURE_OF_MERIT_DEFAULT",
    "MOTOR_EFFICIENCY_DEFAULT",
    "induced_velocity_m_s",
    "ideal_hover_power_W",
    "electrical_hover_power_W",
    "power_per_newton_W_N",
    "electric_endurance_s",
    "turbine_endurance_s",
    "TurbineEndurance",
    "disk_area_from_rotors_m2",
]

FIGURE_OF_MERIT_DEFAULT: float = 0.70
"""Figura de merito do rotor: quanto do ideal o rotor real entrega."""

MOTOR_EFFICIENCY_DEFAULT: float = 0.88
"""Motor mais controlador eletronico."""


def disk_area_from_rotors_m2(diameter_m: float, count: int) -> float:
    """Area total de disco de ``count`` rotores de diametro ``diameter_m``."""
    if diameter_m <= 0.0 or count <= 0:
        raise ValueError("diametro e contagem precisam ser positivos")
    return count * math.pi * (diameter_m / 2.0) ** 2


def induced_velocity_m_s(
    thrust_N: float, disk_area_m2: float, density_kg_m3: float = RHO_SEA_LEVEL_ISA
) -> float:
    """Velocidade induzida no disco, em pairado.

    v_i = sqrt( T / (2 * rho * A) )
    """
    if thrust_N < 0.0 or disk_area_m2 <= 0.0 or density_kg_m3 <= 0.0:
        raise ValueError("empuxo nao negativo, area e densidade positivas")
    return math.sqrt(thrust_N / (2.0 * density_kg_m3 * disk_area_m2))


def ideal_hover_power_W(
    thrust_N: float, disk_area_m2: float, density_kg_m3: float = RHO_SEA_LEVEL_ISA
) -> float:
    """Potencia ideal de sustentacao: ``P = T * v_i``."""
    return thrust_N * induced_velocity_m_s(thrust_N, disk_area_m2, density_kg_m3)


def electrical_hover_power_W(
    thrust_N: float,
    disk_area_m2: float,
    *,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT,
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT,
) -> float:
    """Potencia eletrica na bateria, incluindo as duas ineficiencias."""
    if not 0.0 < figure_of_merit <= 1.0 or not 0.0 < motor_efficiency <= 1.0:
        raise ValueError("eficiencias precisam estar em (0, 1]")
    return ideal_hover_power_W(thrust_N, disk_area_m2, density_kg_m3) / (
        figure_of_merit * motor_efficiency
    )


def power_per_newton_W_N(
    disk_loading_N_m2: float,
    *,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT,
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT,
) -> float:
    """Potencia por newton de sustentacao, funcao **so** da carga de disco.

        P/T = sqrt( L / (2*rho) ) / (FM * eta)

    E esta forma que mostra por que a area manda: o empuxo sai da conta, e sobra a
    carga de disco sob raiz quadrada. Dobrar a area reduz a potencia por newton em
    raiz de dois.
    """
    if disk_loading_N_m2 <= 0.0:
        raise ValueError("carga de disco precisa ser positiva")
    return math.sqrt(disk_loading_N_m2 / (2.0 * density_kg_m3)) / (
        figure_of_merit * motor_efficiency
    )


def electric_endurance_s(
    *,
    gross_kg: float,
    disk_area_m2: float,
    battery_kg: float,
    pack_specific_energy_Wh_kg: float = 180.0,
    depth_of_discharge: float = 0.85,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT,
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT,
) -> float:
    """Autonomia eletrica em pairado, a massa constante.

    A massa nao cai, diferente da turbina. Por isso nao ha integral aqui.

    Os valores padrao sao de pack de **alta descarga**, que e o que um veiculo
    destes exige, e nao de celula de alta energia. A profundidade de descarga
    utilizavel fica em 0,85 porque a queda de tensao sob corrente alta impede usar
    o fim da curva.
    """
    if not 0.0 < depth_of_discharge <= 1.0:
        raise ValueError("profundidade de descarga em (0, 1]")
    if battery_kg <= 0.0:
        raise ValueError("massa de bateria precisa ser positiva")

    thrust_N = gross_kg * G0
    power_W = electrical_hover_power_W(
        thrust_N,
        disk_area_m2,
        density_kg_m3=density_kg_m3,
        figure_of_merit=figure_of_merit,
        motor_efficiency=motor_efficiency,
    )
    energy_Wh = battery_kg * pack_specific_energy_Wh_kg * depth_of_discharge
    return energy_Wh * 3600.0 / power_W


@dataclass(frozen=True, slots=True)
class TurbineEndurance:
    """Autonomia de turbina, com o que a integracao muda em relacao a taxa constante."""

    endurance_s: float
    endurance_constant_rate_s: float
    initial_flow_kg_s: float
    final_flow_kg_s: float
    fuel_burned_kg: float

    @property
    def endurance_min(self) -> float:
        return self.endurance_s / 60.0

    @property
    def integration_gain(self) -> float:
        """Quanto a integracao ganha sobre a estimativa a taxa constante.

        Maior que 1,0 porque a massa cai enquanto queima, e o empuxo de pairado cai
        junto. Estimar a taxa inicial constante **subestima** a autonomia.
        """
        return self.endurance_s / self.endurance_constant_rate_s


def turbine_endurance_s(
    *,
    gross_kg: float,
    usable_fuel_kg: float,
    tsfc_kg_per_N_s: float,
    nozzle_tilt_rad: float = 0.0,
) -> TurbineEndurance:
    """Autonomia de turbina, integrada porque a massa cai com o consumo.

        mdot = TSFC * T_pairado(t),   T_pairado = m(t)*g / cos(theta)
        dm/dt = -k*m,                 k = TSFC * g / cos(theta)

    Que tem solucao fechada:

        t = ln( m0 / (m0 - combustivel_util) ) / k

    ⚠ ``tsfc_kg_per_N_s`` esta em unidade SI. Consumo especifico de catalogo vem em
    quilograma por quilograma-forca por hora, e converter e obrigatorio: a forma
    ``mdot = TSFC * T`` so fecha dimensionalmente com o empuxo na unidade que casa
    com o consumo especifico.

    ⚠ E o consumo especifico de catalogo e medido perto do **maximo**. Em pairado a
    fracao de empuxo e outra, e o consumo especifico tende a piorar em carga
    parcial. Este resultado e ponto, nao banda: a banda exige a familia de curvas
    de carga parcial do deck, que ainda nao existe.
    """
    if usable_fuel_kg <= 0.0 or usable_fuel_kg >= gross_kg:
        raise ValueError(
            f"combustivel util {usable_fuel_kg} kg incompativel com massa {gross_kg} kg"
        )
    if tsfc_kg_per_N_s <= 0.0:
        raise ValueError("consumo especifico precisa ser positivo")

    cos_tilt = math.cos(nozzle_tilt_rad)
    k = tsfc_kg_per_N_s * G0 / cos_tilt

    final_kg = gross_kg - usable_fuel_kg
    endurance = math.log(gross_kg / final_kg) / k

    fluxo_inicial = tsfc_kg_per_N_s * gross_kg * G0 / cos_tilt
    fluxo_final = tsfc_kg_per_N_s * final_kg * G0 / cos_tilt

    return TurbineEndurance(
        endurance_s=endurance,
        endurance_constant_rate_s=usable_fuel_kg / fluxo_inicial,
        initial_flow_kg_s=fluxo_inicial,
        final_flow_kg_s=fluxo_final,
        fuel_burned_kg=usable_fuel_kg,
    )
