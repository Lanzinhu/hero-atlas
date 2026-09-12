"""Autonomia: turbina integrada e eletrico pela teoria do disco atuador.

Ver vault/04 - Fisica/Autonomia e energia.md

Duas leis diferentes, e a diferenca entre elas e o resultado mais interessante do
estudo.

**Turbina:** a massa cai enquanto queima, entao a autonomia sai de uma integral e a
estimativa a taxa constante subestima.

**Eletrico:** a autonomia depende de **area do disco e de bateria ao mesmo tempo**,
e nao de uma so das duas:

    t = E_util / P        E_util = m_bateria * e_especifica * DoD
    P/T = sqrt(L / (2*rho)) / (FM * eta)     com  L = T/A  (carga de disco)

⚠ Uma revisao anterior deste modulo afirmava "funcao da area, nao da bateria". Era
**falso**, e contradizia a propria assinatura de :func:`electric_endurance_s`, que
exige ``battery_kg``. A afirmacao correta e mais forte, porque e quantitativa: como
``P`` cresce com ``m^1.5`` e a bateria entra na massa sustentada, a autonomia tem
**maximo interior** em massa de bateria, e esse maximo tem forma fechada:

    t(m_b) proporcional a  m_b / (m_seco + m_b)^1.5
    dt/dm_b = 0   <=>   m_b = 2 * m_seco

Ver :func:`optimal_battery_mass_kg`. Passado esse ponto, adicionar bateria **reduz**
a autonomia: o quilo a mais nao paga o proprio transporte. Por isso "e so por mais
bateria" nao e resposta, e por isso a area continua sendo a alavanca real.
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
    "optimal_battery_mass_kg",
    "optimal_battery_mass_with_auxiliary_kg",
    "ElectricOptimum",
    "max_electric_endurance_s",
    "disk_area_for_endurance_m2",
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


def optimal_battery_mass_kg(dry_mass_kg: float) -> float:
    """Massa de bateria que **maximiza** a autonomia: o dobro da massa seca.

    Derivacao. Com potencia de pairado ``P ~ (m_g*g)^1.5 / sqrt(2*rho*A)`` e energia
    util ``E ~ m_b``, a autonomia e

        t(m_b) = C * m_b / (m_seco + m_b)^1.5

    e a derivada se anula quando

        (m_seco + m_b) - 1.5*m_b = 0   =>   m_b = 2 * m_seco

    ⚠ **Hipoteses sob as quais isto vale, e so sob elas.** O resultado e uma
    referencia analitica do modelo idealizado de pairado, nao identidade universal:

    - energia util estritamente proporcional a massa de bateria;
    - potencia de pairado estritamente ``~ (m_seco + m_b)^1.5``;
    - **potencia auxiliar nula**. Com ``P_aux > 0`` o otimo se desloca para cima. Ver
      :func:`optimal_battery_mass_with_auxiliary_kg`;
    - **sem teto de trim, sem saturacao de empuxo e sem fase de aceleracao**. Num
      perfil de missao real o teto de massa costuma morder antes do otimo: no
      experimento 2 o otimo pedia 190 kg e a geometria so permitia 103 kg;
    - geometria, densidade e rendimentos fixos ao longo da varredura.

    Dentro dessas hipoteses o resultado e **independente** de area do disco,
    densidade, energia especifica, figura de merito e rendimento de motor: todos
    entram em ``C``, que nao move o ponto de maximo. Eles mudam **quanto** de
    autonomia, nunca **onde** esta o otimo.

    ⚠ E o maximo e interior, nao assintotico: com ``m_b > 2*m_seco`` a autonomia
    **cai**. "Poe mais bateria" deixa de funcionar antes do que a intuicao sugere.

    Args:
        dry_mass_kg: massa de tudo **menos** a bateria, ja incluindo piloto,
            estrutura, rotores e carga util.

            ⚠ E **especifica da familia de propulsao**. Um veiculo eletrico carrega
            motores, inversores, gerenciamento de bateria e cabeamento de alta
            corrente que um de turbina nao carrega, e vice-versa. Comparar familias
            com a mesma massa seca compara armazenamento de energia, nao arquiteturas.
    """
    if not math.isfinite(dry_mass_kg) or dry_mass_kg <= 0.0:
        raise ValueError(f"massa seca precisa ser positiva e finita, recebeu {dry_mass_kg!r}")
    return 2.0 * dry_mass_kg


@dataclass(frozen=True, slots=True)
class ElectricOptimum:
    """Melhor autonomia eletrica possivel para uma massa seca e uma area de disco.

    "Melhor possivel" no sentido estrito de otimizar **so** a massa de bateria. Nao
    e previsao de desempenho: continua condicional a energia especifica, figura de
    merito e rendimento declarados, e a modelo de pairado sem vento.
    """

    battery_kg: float
    gross_kg: float
    endurance_s: float
    disk_loading_N_m2: float
    hover_power_W: float

    @property
    def endurance_min(self) -> float:
        return self.endurance_s / 60.0

    @property
    def battery_mass_fraction(self) -> float:
        """Fracao da massa bruta que e bateria. No otimo vale sempre ``2/3``."""
        return self.battery_kg / self.gross_kg


def max_electric_endurance_s(
    *,
    dry_mass_kg: float,
    disk_area_m2: float,
    pack_specific_energy_Wh_kg: float = 180.0,
    depth_of_discharge: float = 0.85,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT,
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT,
) -> ElectricOptimum:
    """Autonomia no otimo de bateria, com a massa bruta que resulta dele.

    ⚠ A massa bruta **nao** e dado de entrada aqui, e sim consequencia: no otimo ela
    vale ``3 * m_seco``. Fixar massa bruta e massa de bateria ao mesmo tempo e o erro
    que faz uma comparacao entre eletrico e combustao parecer justa quando nao e.
    """
    battery_kg = optimal_battery_mass_kg(dry_mass_kg)
    gross_kg = dry_mass_kg + battery_kg
    endurance = electric_endurance_s(
        gross_kg=gross_kg,
        disk_area_m2=disk_area_m2,
        battery_kg=battery_kg,
        pack_specific_energy_Wh_kg=pack_specific_energy_Wh_kg,
        depth_of_discharge=depth_of_discharge,
        density_kg_m3=density_kg_m3,
        figure_of_merit=figure_of_merit,
        motor_efficiency=motor_efficiency,
    )
    thrust_N = gross_kg * G0
    return ElectricOptimum(
        battery_kg=battery_kg,
        gross_kg=gross_kg,
        endurance_s=endurance,
        disk_loading_N_m2=thrust_N / disk_area_m2,
        hover_power_W=electrical_hover_power_W(
            thrust_N,
            disk_area_m2,
            density_kg_m3=density_kg_m3,
            figure_of_merit=figure_of_merit,
            motor_efficiency=motor_efficiency,
        ),
    )


def disk_area_for_endurance_m2(
    *,
    dry_mass_kg: float,
    target_endurance_s: float,
    pack_specific_energy_Wh_kg: float = 180.0,
    depth_of_discharge: float = 0.85,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT,
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT,
) -> float:
    """Area de disco necessaria para uma autonomia alvo, **ja no otimo de bateria**.

    Esta e a pergunta de dimensionamento correta para o ramo eletrico, e substitui a
    forma ingenua "area necessaria com bateria fixa", que responde a uma pergunta
    diferente e mais otimista.

    Invertendo a autonomia no otimo, onde ``m_b = 2*m_seco`` e ``m_g = 3*m_seco``:

        t = K * sqrt(2*rho*A),   K = 2*e*DoD*3600*FM*eta / ( g^1.5 * 3^1.5 * sqrt(m_seco) )
        A = (t/K)^2 / (2*rho)

    ⚠ ``A`` cresce com o **quadrado** da autonomia alvo. Dobrar o tempo de voo exige
    quadruplicar a area de disco, nao o dobro. E essa area e geometria fisica do
    veiculo, nao um componente que se compra maior.
    """
    if target_endurance_s <= 0.0:
        raise ValueError("autonomia alvo precisa ser positiva")
    if not 0.0 < depth_of_discharge <= 1.0:
        raise ValueError("profundidade de descarga em (0, 1]")
    if not 0.0 < figure_of_merit <= 1.0 or not 0.0 < motor_efficiency <= 1.0:
        raise ValueError("eficiencias precisam estar em (0, 1]")
    if not math.isfinite(dry_mass_kg) or dry_mass_kg <= 0.0:
        raise ValueError("massa seca precisa ser positiva e finita")

    energia_J_por_kg_seco = 2.0 * pack_specific_energy_Wh_kg * depth_of_discharge * 3600.0
    k = (
        energia_J_por_kg_seco
        * figure_of_merit
        * motor_efficiency
        / (G0**1.5 * 3.0**1.5 * math.sqrt(dry_mass_kg))
    )
    return (target_endurance_s / k) ** 2 / (2.0 * density_kg_m3)


def optimal_battery_mass_with_auxiliary_kg(
    *,
    dry_mass_kg: float,
    disk_area_m2: float,
    auxiliary_power_W: float,
    density_kg_m3: float = RHO_SEA_LEVEL_ISA,
    figure_of_merit: float = FIGURE_OF_MERIT_DEFAULT,
    motor_efficiency: float = MOTOR_EFFICIENCY_DEFAULT,
) -> float:
    """Otimo de bateria **com** potencia auxiliar fixa, que desloca o resultado.

    A forma fechada ``m_b = 2*m_seco`` supoe ``P_aux = 0``. Com uma carga fixa de
    aviônica e controle, a autonomia passa a ser

        t(m_b) = c * m_b / ( K*(m_seco + m_b)^1.5 + P_aux )

    e anular a derivada da

        P_aux = K * u^0.5 * ( 0.5*u - 1.5*m_seco ),   u = m_seco + m_b

    que nao tem forma fechada simples e e resolvida por busca de raiz. A funcao e
    crescente em ``u`` acima de ``3*m_seco``, entao a raiz e unica.

    ⚠ O otimo **sobe** com potencia auxiliar, nunca desce: carga fixa e paga por
    tempo, e mais bateria compra tempo. Com ``P_aux = 0`` esta funcao devolve
    exatamente ``2*m_seco``, e o teste que fixa isso e parte da suite.

    ⚠ Continua sem teto de trim e sem fase de aceleracao. O otimo aqui pode estar
    fora do que a geometria equilibra: ver
    :func:`hero_atlas.analysis.mission_energy.evaluate_mission_energy`.
    """
    if not math.isfinite(dry_mass_kg) or dry_mass_kg <= 0.0:
        raise ValueError("massa seca precisa ser positiva e finita")
    if disk_area_m2 <= 0.0:
        raise ValueError("area de disco precisa ser positiva")
    if auxiliary_power_W < 0.0:
        raise ValueError("potencia auxiliar nao pode ser negativa")
    if not 0.0 < figure_of_merit <= 1.0 or not 0.0 < motor_efficiency <= 1.0:
        raise ValueError("eficiencias precisam estar em (0, 1]")

    if auxiliary_power_W == 0.0:
        return optimal_battery_mass_kg(dry_mass_kg)

    k = G0**1.5 / (
        math.sqrt(2.0 * density_kg_m3 * disk_area_m2) * figure_of_merit * motor_efficiency
    )

    def residuo(u: float) -> float:
        return k * math.sqrt(u) * (0.5 * u - 1.5 * dry_mass_kg) - auxiliary_power_W

    baixo = 3.0 * dry_mass_kg
    alto = max(6.0 * dry_mass_kg, 1.0)
    while residuo(alto) < 0.0:
        alto *= 2.0
        if alto > 1e9:
            raise ValueError("otimo com auxiliar nao encontrado na faixa procurada")

    for _ in range(200):
        meio = 0.5 * (baixo + alto)
        if residuo(meio) < 0.0:
            baixo = meio
        else:
            alto = meio

    return 0.5 * (baixo + alto) - dry_mass_kg
