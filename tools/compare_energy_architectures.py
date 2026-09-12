"""Experimento 2: mesma massa embarcada de energia, eletrico contra combustivel.

Roda com::

    ./.venv/Scripts/python.exe tools/compare_energy_architectures.py

Nao faz parte do nucleo: so consome a API publica.

A pergunta que este experimento responde:

    Com a **mesma massa embarcada**, a mesma geometria, a mesma massa seca, a mesma
    reserva e a mesma missao, quanto tempo cada arquitetura entrega, e quanto custa
    sair do chao?

⚠ Tudo aqui e condicional a geometria plausivel e nao medida, a consumo especifico de
catalogo extrapolado para pairado, e a energia especifica de pack declarada. Nada
disto seleciona tecnologia: ver ``hero_atlas.propulsion_family``.
"""

from __future__ import annotations

import math
import sys

sys.path.insert(0, "src")

from hero_atlas.airframe.geometry import (  # noqa: E402
    ArmPairSpec,
    AxialNozzleSpec,
    parametric_layout,
)
from hero_atlas.analysis.energy import (  # noqa: E402
    electrical_hover_power_W,
    optimal_battery_mass_kg,
)
from hero_atlas.analysis.mission_energy import (  # noqa: E402
    BatteryStorage,
    FuelStorage,
    GeometricThrustDemand,
    MissionPhase,
    MissionProfile,
    TerminationReason,
    evaluate_mission_energy,
)
from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.propulsion_family import FAMILIES, selection_verdict  # noqa: E402
from hero_atlas.units import RHO_SEA_LEVEL_ISA, to_si  # noqa: E402
from hero_atlas.verdict import Verdict  # noqa: E402

MASSA_SECA_KG = 95.0
"""Piloto, estrutura, propulsores e aviônica, **sem** energia embarcada. Estimado."""

CENTRO_DE_MASSA = [0.1575, 0.0, 0.0]
"""Meio da janela longitudinal medida no experimento 1."""

TSFC_SI = to_si(1.54, "kg/(kgf*h)")
"""JetCat P400 Pro, derivado de 1,04 kg/min a 40,5 kgf. Catalogo, sem hash."""

FONTE_COMB = "catalogo JetCat P400 Pro, derivado, sem copia arquivada"
FONTE_BAT = "pack de alta descarga, 180 Wh/kg, ordem de grandeza sem copia arquivada"

MASSAS_DE_ENERGIA = (5.0, 10.0, 15.0, 20.0, 30.0, 50.0)

MISSAO = MissionProfile(
    phases=(
        MissionPhase("saida_do_chao", duration_s=3.0, vertical_acceleration_m_s2=0.5),
        MissionPhase("subida", duration_s=10.0, vertical_speed_m_s=1.0),
        MissionPhase("pairado", duration_s=None),
    ),
    reserve_fraction=0.20,
)


def geometria():
    """A variante de posto 6 com rolagem pura que sobreviveu ao experimento 1."""
    t15 = math.radians(15.0)
    return parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15),
            ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
            ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15),
        ],
        axial=[AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)],
        thrust_max_N=to_si(35.0, "kgf"),
        idle_fraction=0.10,
    )


def area_de_disco_vestivel(n_rotores: int, diametro_m: float) -> float:
    return n_rotores * math.pi * (diametro_m / 2.0) ** 2


def main() -> None:
    geo = geometria()
    demanda = lambda: GeometricThrustDemand(  # noqa: E731
        geo, center_of_mass_body_m=CENTRO_DE_MASSA, objective=TrimObjective.MIN_THRUST
    )

    print()
    print("EXPERIMENTO 2: mesma massa embarcada, eletrico contra combustivel")
    print(f"massa seca {MASSA_SECA_KG:.0f} kg, sem energia. Geometria de 7 bocais, posto 6.")
    print("missao: 3 s de arranque, 10 s de subida, pairado ate a reserva de 20 por cento.")
    print("ATENCAO: geometria plausivel nao medida; consumo de catalogo extrapolado.")
    print()

    # area de disco realmente disponivel num arranjo vestivel de bracos
    area_vestivel = area_de_disco_vestivel(7, 0.22)
    print(f"area de disco assumida no ramo eletrico: {area_vestivel:.3f} m2")
    print("  (7 rotores de 22 cm, o maior que cabe junto ao braco sem travar o movimento)")
    print()

    cab = (
        f"{'m_energia':>9} {'bruto':>7} | {'COMBUSTAO':>9} {'decolagem':>9} | "
        f"{'ELETRICO':>9} {'decolagem':>9} | {'razao':>6}"
    )
    print(cab)
    print(f"{'kg':>9} {'kg':>7} | {'min':>9} {'g':>9} | {'min':>9} {'kJ':>9} | {'x':>6}")
    print("-" * len(cab))

    for massa in MASSAS_DE_ENERGIA:
        comb = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=FuelStorage(mass_kg=massa, source=FONTE_COMB, tsfc_kg_per_N_s=TSFC_SI),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=0.5,
        )
        elet = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=BatteryStorage(
                mass_kg=massa, source=FONTE_BAT, rotor_disk_area_m2=area_vestivel
            ),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=0.5,
        )

        def marca(r):
            return "-" if r.termination_reason is TerminationReason.TRIM_INFEASIBLE else ""

        razao = (
            comb.hover_endurance_s / elet.hover_endurance_s
            if elet.hover_endurance_s > 0
            else float("inf")
        )
        print(
            f"{massa:9.0f} {MASSA_SECA_KG + massa:7.0f} | "
            f"{comb.hover_endurance_min:9.2f}{marca(comb):>1} "
            f"{comb.takeoff_storage_used_kg * 1000:9.1f} | "
            f"{elet.hover_endurance_min:9.2f}{marca(elet):>1} "
            f"{elet.takeoff_energy_J / 1000:9.1f} | {razao:6.1f}"
        )

    print()
    print("decolagem = consumo so dos 3 s de arranque, separado do custo de pairar")
    print("razao = quantas vezes a combustao pura o eletrico, na mesma massa embarcada")
    print()

    # ------------------------------------------------------------------
    print("AUTONOMIA POR QUILO EMBARCADO")
    print()
    for massa in (10.0, 20.0):
        comb = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=FuelStorage(mass_kg=massa, source=FONTE_COMB, tsfc_kg_per_N_s=TSFC_SI),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=0.5,
        )
        elet = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=BatteryStorage(
                mass_kg=massa, source=FONTE_BAT, rotor_disk_area_m2=area_vestivel
            ),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=0.5,
        )
        print(
            f"  {massa:.0f} kg embarcados: combustao {comb.hover_endurance_s / massa:6.1f} s/kg, "
            f"eletrico {elet.hover_endurance_s / massa:6.1f} s/kg"
        )
    print()

    # ------------------------------------------------------------------
    print("ONDE O RAMO ELETRICO REALMENTE PARA")
    print()

    # maior massa bruta que a geometria ainda equilibra
    baixo, alto = 50.0, 400.0
    for _ in range(50):
        meio = 0.5 * (baixo + alto)
        s_trim = solve_trim(
            geo,
            mass_kg=meio,
            center_of_mass_body_m=CENTRO_DE_MASSA,
            objective=TrimObjective.MIN_THRUST,
        )
        if s_trim.status is Verdict.SATISFIED:
            baixo = meio
        else:
            alto = meio
    massa_max = baixo
    bateria_max = massa_max - MASSA_SECA_KG

    # e a bateria maxima que ainda deixa a MISSAO INTEIRA viavel, nao so o pairado:
    # a fase de arranque pede aceleracao vertical, que exige empuxo alem do pairado.
    def missao_viavel(bateria_kg: float) -> object | None:
        r = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=BatteryStorage(
                mass_kg=bateria_kg, source=FONTE_BAT, rotor_disk_area_m2=area_vestivel
            ),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=1.0,
        )
        return None if r.termination_reason is TerminationReason.TRIM_INFEASIBLE else r

    b_lo, b_hi = 1.0, bateria_max
    for _ in range(24):
        b_mid = 0.5 * (b_lo + b_hi)
        if missao_viavel(b_mid) is not None:
            b_lo = b_mid
        else:
            b_hi = b_mid
    bateria_decolavel = b_lo

    print(f"  empuxo instalado:              {7 * 35:7.0f} kgf")
    print(f"  maior massa bruta com trim:    {massa_max:7.1f} kg   (so pairado)")
    print(f"  logo, bateria maxima:          {bateria_max:7.1f} kg   (so pairado)")
    print(f"  bateria que ainda DECOLA:      {bateria_decolavel:7.1f} kg")
    print(f"  bateria do otimo irrestrito:   {optimal_battery_mass_kg(MASSA_SECA_KG):7.1f} kg")
    print()
    print("  ⚠ Dois tetos, e o que manda e o menor. O otimo de bateria fica fora do que a")
    print("    geometria equilibra, e a massa que ainda paira ja nao consegue ACELERAR")
    print("    para cima: pedir 0,5 m/s2 de subida corta mais 10 kg de bateria. A")
    print("    autonomia eletrica nao para por area de rotor, para por saturacao de massa.")
    print()

    melhor = missao_viavel(bateria_decolavel)
    bateria_max = bateria_decolavel
    print(f"  teto de autonomia eletrica:    {melhor.hover_endurance_min:7.2f} min")
    print(f"    com {bateria_max:.0f} kg de bateria e {area_vestivel:.2f} m2 de disco")

    # quanto combustivel alcanca o mesmo tempo
    alvo = melhor.hover_endurance_s
    baixo_c, alto_c = 0.5, 60.0
    for _ in range(40):
        meio_c = 0.5 * (baixo_c + alto_c)
        r = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=FuelStorage(mass_kg=meio_c, source=FONTE_COMB, tsfc_kg_per_N_s=TSFC_SI),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=1.0,
        )
        if r.hover_endurance_s < alvo:
            baixo_c = meio_c
        else:
            alto_c = meio_c
    print(f"  mesmo tempo com combustivel:   {alto_c:7.1f} kg")
    print(f"  fator de massa embarcada:      {bateria_max / alto_c:7.1f} vezes")
    print()

    print("  quanta area o eletrico precisaria, com a bateria no teto que decola:")
    for fator in (1, 2, 4, 8):
        a = area_vestivel * fator
        d = 2.0 * math.sqrt(a / (7.0 * math.pi))
        r = evaluate_mission_energy(
            dry_mass_kg=MASSA_SECA_KG,
            storage=BatteryStorage(mass_kg=bateria_max, source=FONTE_BAT, rotor_disk_area_m2=a),
            demand=demanda(),
            profile=MISSAO,
            geometry=geo,
            step_s=1.0,
        )
        print(
            f"    area x{fator:2d} = {a:5.2f} m2, rotor de {d:4.2f} m -> "
            f"{r.hover_endurance_min:6.2f} min"
        )
    print()

    # ------------------------------------------------------------------
    print("POTENCIA DE BARRAMENTO, o numero que decide o hibrido serie")
    print()
    # ⚠ A potencia sai do MESMO caminho do experimento: trim geometrico, empuxos
    # desiguais, soma rotor a rotor. A forma escalar `m*g/razao` com area agregada da
    # um numero menor, porque a potencia induzida e convexa em empuxo e a forma
    # agregada ignora a desigualdade que o trim produz. A diferenca vai impressa.
    escopo_barramento = BatteryStorage(
        mass_kg=1.0,
        source=FONTE_BAT,
        rotor_disk_area_m2=area_vestivel,
        auxiliary_power_W=0.0,
    )
    print(f"{'bruto':>8} {'rotor a rotor':>15} {'escalar agregado':>18} {'razao':>7}")
    print(f"{'kg':>8} {'kW':>15} {'kW':>18} {'x':>7}")
    print("-" * 52)
    for bruto in (120.0, 150.0, massa_max):
        pedido = demanda()(bruto, 0.0)
        if not pedido.feasible:
            print(f"{bruto:8.1f}   sem trim")
            continue
        por_rotor = escopo_barramento.power_W(pedido.thrusts_N, RHO_SEA_LEVEL_ISA)
        agregado = electrical_hover_power_W(
            float(pedido.total_N), area_vestivel, figure_of_merit=0.70, motor_efficiency=0.88
        )
        print(
            f"{bruto:8.1f} {por_rotor / 1000:15.1f} {agregado / 1000:18.1f} "
            f"{por_rotor / agregado:7.2f}"
        )
    print()
    print("  ⚠ Este numero e faixa parametrica preliminar, NAO especificacao de gerador.")
    print("    O que esta dentro: potencia induzida rotor a rotor, figura de merito,")
    print("    rendimento de motor e de inversor. O que NAO esta: perdas de barramento,")
    print("    rendimento do gerador, buffer, potencia auxiliar, derating termico e")
    print("    margem de contingencia. Cada um desses SOBE o requisito.")
    print()
    print("  ⚠ Uma versao anterior deste projeto eliminou o hibrido serie dizendo que")
    print("    ele 'resolve energia, nao area'. A frase confundia energia com potencia.")
    print("    A area limita a POTENCIA, e o hibrido serie nao a melhora. Mas o teto do")
    print("    eletrico puro e de MASSA DE BATERIA, e trocar bateria por gerador mais")
    print("    combustivel ataca exatamente esse teto. A eliminacao foi retirada.")
    print("    O ramo agora depende de um numero: kW por kg do conjunto gerador.")
    print()

    veredito, motivo = selection_verdict()
    print("VEREDITO DE SELECAO DE TECNOLOGIA")
    print(f"  {veredito.name}: {motivo}")
    print()
    for f in FAMILIES:
        marca = "aberto " if f.is_open else "fechado"
        print(f"  [{marca}] {f.name}")
        if not f.is_open:
            print(f"            eliminado por: {f.eliminated_by[:70]}...")
        else:
            print(f"            faltam {len(f.blocking_unknowns)} incognitas bloqueantes")
    print()
    print("  Nenhum ramo esta aprovado. Aprovacao exige os marcos 3 a 5.")


if __name__ == "__main__":
    main()
