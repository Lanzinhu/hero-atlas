"""Experimento 4: quanto atraso e quanta lentidao a arquitetura tolera.

Roda com::

    ./.venv/Scripts/python.exe tools/delay_sweep.py

A pergunta:

    Para cada arquitetura sobrevivente, com massa, centro de massa, missao e limites
    declarados, quais combinacoes de atraso de transporte e constante de tempo ainda
    permitem recuperar de uma perturbacao de atitude declarada?

O que este experimento **nao** responde: se um humano conseguiria pilotar, se alguma
turbina real atende, se o conjunto e seguro, ou se ha estabilidade fora da faixa
varrida e da perturbacao declarada.

⚠ **O atraso e varrido como hipotese, nunca usado como fato.** Nenhum fabricante de
microturbina publica resposta de pequeno sinal perto do ponto de operacao, entao o
parametro entra como eixo de varredura e sai como **fronteira**, nao como numero
unico. Nao existe "atraso critico da arquitetura" sem dizer massa, centro de massa,
rampa, perturbacao e limites junto.

⚠ **Nenhum comando vira empuxo.** O alocador empilha comando; quem decide o empuxo e
a equacao diferencial do atuador. Ver ADR-003.
"""

from __future__ import annotations

import math
import sys

import numpy as np

sys.path.insert(0, "src")

from hero_atlas.airframe.geometry import (  # noqa: E402
    ArmPairSpec,
    AxialNozzleSpec,
    PropulsionGeometry,
    parametric_layout,
)
from hero_atlas.analysis.control_budget import (  # noqa: E402
    achievable_bandwidth_rad_s,
    moment_budget,
)
from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.control.attitude import AttitudeGains, HoverController  # noqa: E402
from hero_atlas.dynamics.quaternion import from_axis_angle  # noqa: E402
from hero_atlas.dynamics.rigid_body import PlantState, RigidBodyProperties  # noqa: E402
from hero_atlas.propulsion.actuator import ActuatorEnvelope  # noqa: E402
from hero_atlas.sim.closed_loop import TerminationMode, simulate  # noqa: E402
from hero_atlas.units import G0, to_si  # noqa: E402

# --------------------------------------------------------------------------- config
MASSA_KG = 115.0
"""Piloto, traje e energia. **Estimada**, nao reconciliada com CAD."""

CENTRO_DE_MASSA_M = np.array([0.1575, 0.0, 0.0])
"""Meio da janela longitudinal do experimento 1. Declarado."""

INERCIA = np.diag([32.2, 32.2, 2.3])
"""Cilindro equivalente de 1,8 m por 0,2 m de raio. ⚠ **Estimada**, nao de geometria."""

PERTURBACAO_GRAUS = 10.0
"""Perturbacao de rolagem a recuperar. Escolha de campanha, nao requisito."""

HORIZONTE_ALOCADOR_S = 0.20
BANDA_FRACAO = 0.70
"""Fracao da banda alcancavel que o controlador usa. Margem declarada."""

PASSO_MAX_S = 0.002
TEMPO_FINAL_S = 12.0

ATRASOS_S = (0.0, 0.02, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
CONSTANTES_S = (0.10, 0.20, 0.35, 0.50, 0.80, 1.20, 1.80)
RAMPAS_N_S = (40.0, 80.0, 120.0, 200.0, 400.0)


def geometria_a() -> PropulsionGeometry:
    """Familia A: bocais vetorizados compactos. Sobrevivente do funil."""
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


def envelope(tau_s: float, rampa_N_s: float) -> ActuatorEnvelope:
    """Envelope com a constante de tempo **perto do ponto de operacao**.

    ⚠ O laco fechado opera perto do trim, entao a constante que ele exercita e a de
    **pequeno sinal**, que e a incognita central do projeto. O modelo usa uma
    constante por direcao, independente da amplitude: e simplificacao declarada, nao
    resultado. A assimetria entre subir e descer e mantida em vinte por cento, que e
    hipotese de trabalho.
    """
    return ActuatorEnvelope(
        thrust_min_N=to_si(3.5, "kgf"),
        thrust_max_N=to_si(35.0, "kgf"),
        tau_up_s=tau_s,
        tau_down_s=0.85 * tau_s,
        rate_up_max_N_s=rampa_N_s,
        rate_down_max_N_s=1.25 * rampa_N_s,
    )


_BANDA_CACHE: dict[float, float] = {}


def banda_de_referencia(geo: PropulsionGeometry, perturbacao_graus: float) -> float:
    """Banda derivada do envelope de **referencia**, nao do envelope da celula.

    O envelope de referencia e ``tau = 0,35 s`` e rampa de 120 N/s, que e a hipotese
    central do deck. Fixar a banda e o que torna a varredura um experimento sobre a
    planta.
    """
    chave = round(perturbacao_graus, 6)
    if chave in _BANDA_CACHE:
        return _BANDA_CACHE[chave]
    envs = tuple(envelope(0.35, 120.0) for _ in geo.available)
    trim = solve_trim(
        geo,
        mass_kg=MASSA_KG,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        objective=TrimObjective.MAX_MARGIN,
    )
    orcamento = moment_budget(
        geo, thrust_trim_N=trim.thrusts_N, envelopes=envs, horizon_s=HORIZONTE_ALOCADOR_S
    )
    banda = achievable_bandwidth_rad_s(
        orcamento, inertia_kg_m2=INERCIA, reference_error_rad=math.radians(perturbacao_graus)
    )
    _BANDA_CACHE[chave] = banda
    return banda


def roda(
    geo: PropulsionGeometry,
    *,
    tau_s: float,
    rampa_N_s: float,
    atraso_s: float,
    perturbacao_graus: float = PERTURBACAO_GRAUS,
    banda_rad_s: float | None = None,
) -> tuple[TerminationMode, float, float, float]:
    """Um caso. Devolve modo de termino, pico angular, perda de altura e fracao de rampa."""
    envs = tuple(envelope(tau_s, rampa_N_s) for _ in geo.available)
    corpo = RigidBodyProperties(
        mass_kg=MASSA_KG,
        inertia_about_cg_kg_m2=INERCIA,
        cg_offset_from_reference_m=CENTRO_DE_MASSA_M,
    )
    trim = solve_trim(
        geo,
        mass_kg=MASSA_KG,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        objective=TrimObjective.MAX_MARGIN,
    )
    if not trim.feasible:
        return TerminationMode.ALLOCATOR_INFEASIBLE, math.nan, math.nan, math.nan

    # ⚠ A banda e FIXA ao longo de toda a varredura, calculada uma vez a partir do
    # envelope de referencia. Deixa-la seguir o envelope de cada celula foi o primeiro
    # desenho e estava errado: tornar o atuador mais lento tambem tornava o
    # controlador mais manso, e a fronteira media a adaptatividade do controlador em
    # vez da tolerancia da planta. Com banda fixa, a unica coisa que muda entre
    # celulas e o atuador, que e o que se quer medir.
    banda = (
        banda_de_referencia(geo, perturbacao_graus) * BANDA_FRACAO
        if banda_rad_s is None
        else banda_rad_s
    )

    controlador = HoverController(
        mass_kg=MASSA_KG,
        inertia_kg_m2=INERCIA,
        sample_period_s=0.01,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        reference_altitude_m=10.0,
        attitude=AttitudeGains(natural_frequency_rad_s=banda, damping_ratio=0.9),
    )
    estado0 = PlantState(
        position_O_I_m=np.array([0.0, 0.0, -10.0]),
        velocity_O_I_m_s=np.zeros(3),
        quaternion_ib=from_axis_angle([1.0, 0.0, 0.0], math.radians(perturbacao_graus)),
        omega_B_rad_s=np.zeros(3),
    )
    r = simulate(
        geo,
        corpo,
        envs,
        controlador,
        initial_state=estado0,
        initial_thrust_N=trim.thrusts_N,
        t_final_s=TEMPO_FINAL_S,
        transport_delay_s=atraso_s,
        allocation_horizon_s=HORIZONTE_ALOCADOR_S,
        max_step_s=PASSO_MAX_S,
        collect_telemetry=False,
    )
    return (
        r.mode,
        r.peak_attitude_error_deg,
        r.max_altitude_loss_m,
        r.rate_limited_fraction,
    )


SIMBOLO = {
    TerminationMode.CAPTURED: "ok",
    TerminationMode.HORIZON_REACHED: "..",
    TerminationMode.ATTITUDE_LIMIT_EXCEEDED: "AT",
    TerminationMode.ALTITUDE_LOSS_LIMIT: "AL",
    TerminationMode.WRENCH_UNATTAINABLE: "WR",
    TerminationMode.ALLOCATOR_INFEASIBLE: "AI",
    TerminationMode.NUMERICAL_FAILURE: "NU",
}


def main() -> None:
    geo = geometria_a()

    print()
    print("EXPERIMENTO 4: TOLERANCIA A ATRASO E A LENTIDAO DO ATUADOR")
    print("familia A, bocais vetorizados compactos, sobrevivente do funil")
    print()
    print("CONDICOES DECLARADAS (a fronteira depende de TODAS elas)")
    print(f"  massa                        {MASSA_KG:.1f} kg   (estimada)")
    print(f"  centro de massa              {CENTRO_DE_MASSA_M.tolist()} m")
    print(f"  inercia diagonal             {np.diag(INERCIA).tolist()} kg m2   (estimada)")
    print(f"  perturbacao de rolagem       {PERTURBACAO_GRAUS:.1f} graus")
    print(f"  horizonte do alocador        {HORIZONTE_ALOCADOR_S:.2f} s")
    banda_ref = banda_de_referencia(geometria_a(), PERTURBACAO_GRAUS)
    print(
        f"  banda do controlador         {BANDA_FRACAO * banda_ref:.2f} rad/s, "
        f"{BANDA_FRACAO:.0%} de {banda_ref:.2f} alcancavel"
    )
    print("  banda FIXA na varredura      so o atuador muda entre celulas")
    print(f"  passo maximo                 {PASSO_MAX_S} s, Runge-Kutta de quarta ordem")
    print("  tique do controlador         100 Hz, amostrado e retido")
    print()

    trim = solve_trim(
        geo,
        mass_kg=MASSA_KG,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        objective=TrimObjective.MAX_MARGIN,
    )
    envs_ref = tuple(envelope(0.35, 120.0) for _ in geo.available)
    orc = moment_budget(
        geo, thrust_trim_N=trim.thrusts_N, envelopes=envs_ref, horizon_s=HORIZONTE_ALOCADOR_S
    )
    print("ORCAMENTO DE MOMENTO, as duas margens do ADR-004")
    print(f"  {'eixo':8} {'estatica':>12} {'no horizonte':>14} {'razao':>8}")
    for nome, est, hor, raz in orc.as_rows():
        print(f"  {nome:8} {est:9.1f} Nm {hor:11.1f} Nm {raz:7.1f}x")
    print()
    print("  ⚠ A margem de curto prazo e cinco a seis vezes menor que a estatica.")
    print("    Empuxo maximo excelente nao implica autoridade de curto prazo.")
    print(f"    Soma de empuxo no trim: {trim.total_thrust_N / G0:.1f} kgf.")
    print()

    # ---------------------------------------------------------------- grade 2D
    print("FRONTEIRA: atraso de transporte contra constante de tempo")
    print("  ok = recuperou  AT = excedeu atitude  AL = perdeu altitude")
    print("  WR = wrench inatingivel  .. = nao recuperou no horizonte")
    print()
    cab = f"  {'tau \\ atraso':>14} " + " ".join(f"{a:>6.2f}" for a in ATRASOS_S)
    print(cab)
    print("  " + "-" * (len(cab) - 2))
    fronteira: dict[float, float | None] = {}
    for tau in CONSTANTES_S:
        celulas = []
        maior_ok: float | None = None
        for atraso in ATRASOS_S:
            modo, _, _, _ = roda(geo, tau_s=tau, rampa_N_s=120.0, atraso_s=atraso)
            celulas.append(f"{SIMBOLO[modo]:>6}")
            if modo is TerminationMode.CAPTURED:
                maior_ok = atraso
        fronteira[tau] = maior_ok
        print(f"  {tau:14.2f} " + " ".join(celulas))
    print()

    print("MAIOR ATRASO QUE AINDA RECUPERA, por constante de tempo")
    for tau, atraso in fronteira.items():
        if atraso is None:
            print(f"  tau = {tau:4.2f} s -> nenhum atraso da faixa recupera")
        else:
            print(f"  tau = {tau:4.2f} s -> ate {atraso:4.2f} s de atraso de transporte")
    print()

    # ---------------------------------------------------------------- rampa
    print("EFEITO DA RAMPA MAXIMA, com atraso de 0,05 s")
    print(f"  {'rampa':>10} {'tau=0,35':>12} {'tau=0,80':>12} {'tau=1,20':>12}")
    for rampa in RAMPAS_N_S:
        linha = []
        for tau in (0.35, 0.80, 1.20):
            modo, pico, _, frac = roda(geo, tau_s=tau, rampa_N_s=rampa, atraso_s=0.05)
            marca = SIMBOLO[modo]
            linha.append(f"{marca:>4} {frac:6.0%}")
        print(f"  {rampa:7.0f} N/s " + " ".join(f"{c:>12}" for c in linha))
    print()
    print("  A fracao ao lado e o tempo em que o limite de rampa esteve ativo.")
    print()

    # ---------------------------------------------------------------- dependencia
    print("A FRONTEIRA DEPENDE DA CONDICAO, e nao e propriedade da arquitetura")
    print(f"  {'perturbacao':>12} {'maior atraso que recupera, tau=0,35 s':>40}")
    for graus in (5.0, 10.0, 20.0, 30.0):
        maior: float | None = None
        for atraso in ATRASOS_S:
            modo, _, _, _ = roda(
                geo, tau_s=0.35, rampa_N_s=120.0, atraso_s=atraso, perturbacao_graus=graus
            )
            if modo is TerminationMode.CAPTURED:
                maior = atraso
        texto = "nenhum" if maior is None else f"{maior:.2f} s"
        print(f"  {graus:9.1f} graus {texto:>38}")
    print()

    # ------------------------------------------------- o achado que reordena tudo
    print("O QUE REALMENTE MANDA: banda exigida contra atraso tolerado")
    print("  tau fixo em 0,35 s, rampa em 120 N/s, perturbacao de 10 graus")
    print()
    print(f"  {'banda':>10} {'periodo':>9} {'maior atraso que recupera':>28}")
    for banda in (0.5, 1.05, 2.0, 3.0, 4.5, 6.0):
        maior: float | None = None
        for atraso in ATRASOS_S:
            modo, _, _, _ = roda(
                geo, tau_s=0.35, rampa_N_s=120.0, atraso_s=atraso, banda_rad_s=banda
            )
            if modo is TerminationMode.CAPTURED:
                maior = atraso
        periodo = 2.0 * math.pi / banda
        texto = "nenhum" if maior is None else f"{maior:.2f} s"
        fracao = "" if maior is None else f"  ({maior / periodo:.1%} do periodo)"
        print(f"  {banda:7.2f} r/s {periodo:7.1f} s {texto:>18}{fracao}")
    print()
    print("  ⚠ **A arquitetura tolera atraso porque e obrigada a ser lenta.** A banda")
    print("    que a autoridade de curto prazo permite e de cerca de 1,5 rad/s, ou um")
    print("    periodo de quatro segundos. Qualquer atraso da faixa varrida e uma")
    print("    fracao pequena disso. O parametro que limita esta arquitetura NAO e o")
    print("    atraso: e o momento disponivel no horizonte.")
    print()
    print("  Isso inverte a pergunta do passo seguinte. A especificacao que sai daqui")
    print("  nao e 'a turbina precisa ser rapida', e sim 'a turbina precisa entregar")
    print("  momento', o que se traduz em faixa de empuxo e rampa, nao em atraso.")
    print()

    print("  ⚠ Nao existe 'atraso critico da arquitetura'. A fronteira e funcao de")
    print("    geometria, massa, centro de massa, inercia, rampa, banda, perturbacao")
    print("    e limites de falha, e todos estao declarados acima.")


if __name__ == "__main__":
    main()
