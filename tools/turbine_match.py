"""Experimento 5: turbinas reais contra a especificacao que o simulador produziu.

Roda com::

    ./.venv/Scripts/python.exe tools/turbine_match.py

A pergunta:

    Com a especificacao que saiu do passo 5, quais microturbinas de catalogo
    atendem, quais nao atendem, e **quais requisitos nao podem sequer ser
    verificados** com o que os fabricantes publicam?

⚠ Este experimento **nao** seleciona turbina, nao aprova nenhuma, e nao afirma que
alguma funcionaria. Ele confronta requisito com dado publicado e, principalmente,
**expoe o que falta**.

⚠ **A massa da turbina entra na conta.** Sete turbinas de quatro quilos sao vinte e
oito quilos que o veiculo precisa sustentar, o que muda o empuxo exigido, que muda a
turbina necessaria. O laco e fechado aqui em vez de ignorado.

Dados de catalogo recuperados em 2026-09-12. ⚠ Sem copia arquivada com hash: o
projeto registra a data e a origem, e isso ainda e evidencia mais fraca do que o
regime de procedencia do ADR-007 exige.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass

import numpy as np

sys.path.insert(0, "src")

from hero_atlas.airframe.geometry import (  # noqa: E402
    ArmPairSpec,
    AxialNozzleSpec,
    parametric_layout,
)
from hero_atlas.analysis.control_budget import (  # noqa: E402
    achievable_bandwidth_rad_s,
    moment_budget,
)
from hero_atlas.analysis.energy import turbine_endurance_s  # noqa: E402
from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.propulsion.actuator import ActuatorEnvelope  # noqa: E402
from hero_atlas.units import G0  # noqa: E402
from hero_atlas.verdict import Verdict  # noqa: E402

N_PROPULSORES = 7
PILOTO_KG = 80.0
ESTRUTURA_KG = 12.0
"""Tanques, linhas, aviônica, fixacao. ⚠ Estimativa, nao de CAD."""

COMBUSTIVEL_KG = 20.0
CENTRO_DE_MASSA_M = np.array([0.1575, 0.0, 0.0])
INERCIA = np.diag([32.2, 32.2, 2.3])
HORIZONTE_S = 0.20
BANDA_ALVO_RAD_S = 1.5
"""Banda que o passo 5 mostrou ser o teto util desta arquitetura."""

DENSIDADE_QUEROSENE_KG_L = 0.80


@dataclass(frozen=True, slots=True)
class Turbina:
    """Uma turbina de catalogo, com o que o fabricante publica e o que nao publica."""

    nome: str
    fonte: str
    data_consulta: str
    empuxo_max_N: float
    empuxo_idle_N: float | None
    massa_kg: float
    consumo_max_kg_s: float
    rpm_idle: float
    rpm_max: float

    # ⚠ Nenhum fabricante publica estes. None significa DESCONHECIDO, nao zero.
    tau_pequeno_sinal_s: float | None = None
    rampa_max_N_s: float | None = None
    atraso_transporte_s: float | None = None

    @property
    def tsfc_kg_per_N_s(self) -> float:
        return self.consumo_max_kg_s / self.empuxo_max_N

    @property
    def empuxo_por_massa(self) -> float:
        """Empuxo maximo por quilo de turbina, em newton por quilo."""
        return self.empuxo_max_N / self.massa_kg

    @property
    def frequencia_eixo_max_Hz(self) -> float:
        return self.rpm_max / 60.0


CANDIDATAS = (
    Turbina(
        nome="JetCat P400-PRO-LN",
        fonte="jetcat.de, pagina do produto",
        data_consulta="2026-09-12",
        empuxo_max_N=425.0,
        empuxo_idle_N=14.0,
        massa_kg=4.010,
        consumo_max_kg_s=1392.0 / 1000.0 * DENSIDADE_QUEROSENE_KG_L / 60.0,
        rpm_idle=30_000.0,
        rpm_max=98_000.0,
    ),
    Turbina(
        nome="Kingtech K-260G4",
        fonte="kingtechtw.com e revendedores",
        data_consulta="2026-09-12",
        empuxo_max_N=26.0 * G0,
        empuxo_idle_N=None,
        massa_kg=2.200,
        consumo_max_kg_s=760.0 / 1000.0 / 60.0,
        rpm_idle=33_000.0,
        rpm_max=112_000.0,
    ),
    Turbina(
        nome="Kingtech K-210G4",
        fonte="kingtechtw.com e revendedores",
        data_consulta="2026-09-12",
        empuxo_max_N=21.0 * G0,
        empuxo_idle_N=None,
        massa_kg=1.740,
        consumo_max_kg_s=590.0 / 1000.0 / 60.0,
        rpm_idle=33_000.0,
        rpm_max=120_000.0,
    ),
)


def geometria():
    t15 = math.radians(15.0)
    return parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15),
            ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
            ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15),
        ],
        axial=[AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)],
        thrust_max_N=343.0,
        idle_fraction=0.10,
    )


def avalia(t: Turbina) -> dict[str, object]:
    """Monta o veiculo com esta turbina e mede o que da para medir."""
    massa_bruta = PILOTO_KG + ESTRUTURA_KG + N_PROPULSORES * t.massa_kg + COMBUSTIVEL_KG

    geo = parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +math.radians(15.0)),
            ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
            ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -math.radians(15.0)),
        ],
        axial=[AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)],
        thrust_max_N=t.empuxo_max_N,
        idle_fraction=(t.empuxo_idle_N / t.empuxo_max_N) if t.empuxo_idle_N else 0.10,
    )

    trim = solve_trim(
        geo,
        mass_kg=massa_bruta,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        objective=TrimObjective.MAX_MARGIN,
    )
    resultado: dict[str, object] = {
        "massa_bruta": massa_bruta,
        "massa_turbinas": N_PROPULSORES * t.massa_kg,
        "trim": trim.status,
    }
    if trim.status is not Verdict.SATISFIED:
        resultado["motivo"] = trim.cause.value
        return resultado

    empuxo_trim = trim.total_thrust_N / N_PROPULSORES
    resultado["empuxo_por_bocal_N"] = empuxo_trim
    resultado["fracao_do_teto"] = empuxo_trim / t.empuxo_max_N

    # ⚠ A rampa nao e publicada. Para medir o orcamento de momento e preciso supor
    # uma, e a suposicao vai declarada junto do resultado.
    rampa_suposta = 120.0
    envs = tuple(
        ActuatorEnvelope(
            thrust_min_N=t.empuxo_idle_N if t.empuxo_idle_N else 0.10 * t.empuxo_max_N,
            thrust_max_N=t.empuxo_max_N,
            tau_up_s=0.35,
            tau_down_s=0.30,
            rate_up_max_N_s=rampa_suposta,
            rate_down_max_N_s=1.25 * rampa_suposta,
        )
        for _ in geo.available
    )
    orc = moment_budget(geo, thrust_trim_N=trim.thrusts_N, envelopes=envs, horizon_s=HORIZONTE_S)
    banda = achievable_bandwidth_rad_s(
        orc, inertia_kg_m2=INERCIA, reference_error_rad=math.radians(10.0)
    )
    resultado["momento_horizonte_Nm"] = float(orc.horizon_Nm[0])
    resultado["banda_rad_s"] = banda
    resultado["banda_ok"] = banda >= 0.99 * BANDA_ALVO_RAD_S

    autonomia = turbine_endurance_s(
        gross_kg=massa_bruta,
        usable_fuel_kg=0.8 * COMBUSTIVEL_KG,
        tsfc_kg_per_N_s=t.tsfc_kg_per_N_s,
        nozzle_tilt_rad=math.acos(min(1.0, trim.vertical_thrust_projection_ratio)),
    )
    resultado["autonomia_min"] = autonomia.endurance_min
    return resultado


def main() -> None:
    print()
    print("EXPERIMENTO 5: TURBINAS REAIS CONTRA A ESPECIFICACAO")
    print("sete propulsores, geometria A, piloto 80 kg, estrutura 12 kg, 20 kg de combustivel")
    print()

    print("O QUE OS FABRICANTES PUBLICAM")
    cab = (
        f"{'turbina':22} {'T max':>8} {'T idle':>8} {'massa':>7} {'T/massa':>9} "
        f"{'consumo':>11} {'RPM max':>9}"
    )
    print(cab)
    print(f"{'':22} {'N':>8} {'N':>8} {'kg':>7} {'N/kg':>9} {'kg/(N.s)':>11} {'1/min':>9}")
    print("-" * len(cab))
    for t in CANDIDATAS:
        idle = f"{t.empuxo_idle_N:8.0f}" if t.empuxo_idle_N else f"{'--':>8}"
        print(
            f"{t.nome:22} {t.empuxo_max_N:8.0f} {idle} {t.massa_kg:7.2f} "
            f"{t.empuxo_por_massa:9.0f} {t.tsfc_kg_per_N_s:11.2e} {t.rpm_max:9.0f}"
        )
    print()

    print("O QUE NENHUM DELES PUBLICA, E QUE E O QUE DECIDE")
    print(f"  {'parametro':38} {'estado':>14}")
    for parametro in (
        "constante de tempo de pequeno sinal",
        "rampa maxima de empuxo",
        "atraso de transporte do comando",
        "empuxo minimo estavel em voo",
        "consumo especifico em carga parcial",
        "perda de instalacao em arranjo vestivel",
    ):
        print(f"  {parametro:38} {'DESCONHECIDO':>14}")
    print()
    print("  Verificado na pagina do fabricante da JetCat em 2026-09-12: nenhuma")
    print("  especificacao de tempo, resposta, constante ou taxa aparece.")
    print()
    print("  ⚠ E ha um motivo tecnico, nao comercial: a taxa de subida de empuxo e")
    print("    limitada DELIBERADAMENTE pela unidade de controle, para nao afogar a")
    print("    camara na aceleracao nem apagar a chama na desaceleracao. Ou seja, a")
    print("    rampa nao e propriedade fixa do motor: e parametro de controle, com")
    print("    margem termica e risco de apagamento do outro lado. Isso a torna, em")
    print("    principio, NEGOCIAVEL com o fabricante, e e por isso que pedir o dado")
    print("    e mais util que procura-lo.")
    print()

    print("O QUE DA PARA VERIFICAR, montando o veiculo com cada uma")
    cab2 = (
        f"{'turbina':22} {'bruto':>7} {'turbinas':>9} {'trim':>6} {'T/Tmax':>8} "
        f"{'Mx horiz':>9} {'banda':>8} {'autonomia':>10}"
    )
    print(cab2)
    print(f"{'':22} {'kg':>7} {'kg':>9} {'':>6} {'':>8} {'Nm':>9} {'rad/s':>8} {'min':>10}")
    print("-" * len(cab2))
    for t in CANDIDATAS:
        r = avalia(t)
        if r["trim"] is not Verdict.SATISFIED:
            print(
                f"{t.nome:22} {r['massa_bruta']:7.1f} {r['massa_turbinas']:9.1f} "
                f"{'NAO':>6}   {r['motivo']}"
            )
            continue
        marca = "ok" if r["banda_ok"] else "BAIXA"
        print(
            f"{t.nome:22} {r['massa_bruta']:7.1f} {r['massa_turbinas']:9.1f} "
            f"{'sim':>6} {r['fracao_do_teto']:8.2f} {r['momento_horizonte_Nm']:9.1f} "
            f"{r['banda_rad_s']:6.2f} {marca:>2} {r['autonomia_min']:10.2f}"
        )
    print()
    print("  ⚠ A banda acima supoe rampa de 120 N/s, que **nao e publicada**. Ela e")
    print("    hipotese de trabalho, e o numero de banda herda essa incerteza inteira.")
    print()

    print("VEREDITO POR REQUISITO")
    print(f"  {'requisito':44} {'verificavel?':>14}")
    linhas = (
        ("empuxo de pairado por bocal", "sim"),
        ("faixa de empuxo suficiente para o momento", "sim"),
        ("massa de propulsao dentro do orcamento", "sim"),
        ("autonomia de missao", "sim, com ressalva"),
        ("momento disponivel no horizonte", "NAO, depende da rampa"),
        ("banda de atitude alcancavel", "NAO, depende da rampa"),
        ("tolerancia a atraso", "NAO, atraso nao publicado"),
        ("estabilidade em malha fechada", "NAO"),
    )
    for requisito, estado in linhas:
        print(f"  {requisito:44} {estado:>14}")
    print()
    print("  Quatro dos oito requisitos NAO podem ser verificados com dado publicado.")
    print("  Os quatro sao exatamente os que dependem de dinamica.")
    print()
    print("  ⚠ Conclusao permitida: com os dados publicados, nenhuma candidata pode")
    print("    ser aprovada nem reprovada nos criterios dinamicos. O que o passo 5")
    print("    produziu e uma LISTA DE PERGUNTAS para o fabricante, nao um pedido de")
    print("    compra. Este e o resultado util deste experimento.")


if __name__ == "__main__":
    main()
