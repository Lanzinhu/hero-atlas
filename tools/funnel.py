"""Experimento 3: funil de arquiteturas. Seis familias, oito filtros, quem sobra.

Roda com::

    ./.venv/Scripts/python.exe tools/funnel.py

A pergunta nao e "qual traje construir". E:

    Quais familias de arquitetura **nao merecem dinamica**, porque ja morrem em
    empuxo, posto, trim, saida do chao, tolerancia de centro de massa, folga,
    energia ou falha unica?

⚠ Nenhuma familia aqui e promessa de construcao, e nenhuma esta aprovada. Massas,
geometrias, consumos e rendimentos sao **hipoteses parametricas sem dado arquivado**.
Sobreviver ao funil significa apenas "merece receber dinamica".
"""

from __future__ import annotations

import math
import sys

import numpy as np

sys.path.insert(0, "src")

from hero_atlas.airframe.geometry import (  # noqa: E402
    ArmPairSpec,
    AxialNozzleSpec,
    NozzleSpec,
    PropulsionGeometry,
    parametric_layout,
)
from hero_atlas.analysis.funnel import (  # noqa: E402
    ArchitectureFamily,
    PropulsionKind,
    ScreeningRequirements,
    ScreeningStage,
    mortality_by_stage,
    run_funnel,
    survivors,
)
from hero_atlas.propulsion_family import selection_verdict  # noqa: E402
from hero_atlas.units import to_si  # noqa: E402

TSFC_SI = to_si(1.54, "kg/(kgf*h)")
"""JetCat P400 Pro, derivado de catalogo. Sem copia arquivada."""

PILOTO_KG = 80.0
"""Piloto com equipamento de protecao. Estimado."""


def area_de_rotores(quantidade: int, diametro_m: float) -> float:
    return quantidade * math.pi * (diametro_m / 2.0) ** 2


VELOCIDADE_DE_PONTA_M_S = 150.0
"""Velocidade de ponta de pa assumida. Limitada por ruido e compressibilidade.

⚠ Valor **declarado**, tipico de veiculo eletrico de decolagem vertical. Nao medido.
"""


def torque_por_empuxo_m(
    *, empuxo_por_rotor_N: float, area_por_rotor_m2: float, raio_m: float
) -> float:
    """Torque de reacao por newton de empuxo, ``Q/T``, pela teoria do disco.

    Em pairado, a potencia de eixo vale ``P = T*v_i/FM`` e tambem ``P = Q*omega``.
    Igualando, com ``omega = V_ponta / R``::

        Q/T = v_i * R / ( FM * V_ponta ),    v_i = sqrt( T / (2*rho*A) )

    ⚠ **Derivado, nao medido**, e avaliado no empuxo de pairado: ``Q/T`` varia com o
    empuxo, e usa-lo constante e uma linearizacao declarada em torno do ponto de
    operacao. Serve para dizer se existe autoridade de guinada e de que ordem, nao
    para dimensionar um rotor.
    """
    velocidade_induzida = math.sqrt(empuxo_por_rotor_N / (2.0 * 1.225 * area_por_rotor_m2))
    return velocidade_induzida * raio_m / (0.70 * VELOCIDADE_DE_PONTA_M_S)


def anel_de_rotores(
    *,
    quantidade: int,
    raio_do_anel_m: float,
    raio_do_rotor_m: float,
    altura_m: float,
    empuxo_max_N: float,
    empuxo_de_pairado_N: float,
    avanco_m: float = 0.0,
    inclinacao_rad: float = 0.0,
) -> PropulsionGeometry:
    """Rotores em anel em torno do tronco, com sentidos de giro **alternados**.

    Dois detalhes decidem o posto da matriz de alocacao, e os dois sao fisica de
    rotor que um bocal nao tem:

    1. **Inclinacao radial.** Rotor perfeitamente vertical nao produz forca lateral
       nenhuma. E o mesmo mecanismo que o experimento 1 encontrou nos bocais.
    2. **Sentido de giro alternado.** O torque de reacao entra na coluna com o sinal
       do giro. Com todos girando igual, a contribuicao de guinada de cada rotor tem
       o mesmo sinal e a linha ``Mz`` vira um multiplo de ``Fz``: guinada e
       sustentacao deixam de ser independentes. Alternar e o que separa as duas, e e
       por isso que todo quadricoptero real faz isso.

    ⚠ Quantidade impar nao permite alternancia equilibrada, e o anel fica com torque
    de guinada residual em pairado. A funcao recusa, em vez de produzir uma geometria
    que so funciona por acaso numerico.
    """
    if quantidade < 3:
        raise ValueError("anel precisa de pelo menos tres rotores")
    if quantidade % 2 != 0:
        raise ValueError(
            f"anel de {quantidade} rotores nao permite alternar sentido de giro em "
            "pares. Com quantidade impar sobra torque de guinada em pairado, e o "
            "trim passa a depender de um desequilibrio permanente de empuxo."
        )

    area_por_rotor = math.pi * raio_do_rotor_m**2
    razao = torque_por_empuxo_m(
        empuxo_por_rotor_N=empuxo_de_pairado_N,
        area_por_rotor_m2=area_por_rotor,
        raio_m=raio_do_rotor_m,
    )

    bocais = []
    for i in range(quantidade):
        angulo = 2.0 * math.pi * i / quantidade
        x = avanco_m + raio_do_anel_m * math.cos(angulo)
        y = raio_do_anel_m * math.sin(angulo)
        si, ci = math.sin(inclinacao_rad), math.cos(inclinacao_rad)
        direcao = np.array([si * math.cos(angulo), si * math.sin(angulo), -ci])
        sentido = 1.0 if i % 2 == 0 else -1.0
        bocais.append(
            NozzleSpec(
                name=f"rotor{i}",
                position_body_m=np.array([x, y, altura_m]),
                direction_body=direcao,
                thrust_min_N=0.0,
                thrust_max_N=empuxo_max_N,
                torque_per_thrust_m=sentido * razao,
            )
        )
    return PropulsionGeometry(nozzles=tuple(bocais), reference_point_body_m=np.zeros(3))


def familia_a() -> ArchitectureFamily:
    """Bocais vetorizados compactos. A referencia ja explorada."""
    t15 = math.radians(15.0)
    geo = parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15),
            ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
            ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15),
        ],
        axial=[AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)],
        thrust_max_N=to_si(35.0, "kgf"),
        idle_fraction=0.10,
    )
    return ArchitectureFamily(
        code="A",
        name="bocais vetorizados compactos",
        summary="sete microturbinas nos bracos e dorsal, vetorizadas pelo corpo",
        geometry=geo,
        dry_mass_kg=PILOTO_KG + 15.0,
        energy_mass_kg=20.0,
        kind=PropulsionKind.JET,
        tsfc_kg_per_N_s=TSFC_SI,
        unmodelled=(
            "atraso de degrau pequeno perto do trim",
            "perda de instalacao e interacao em arranjo vestivel",
            "consumo especifico em carga parcial",
        ),
    )


def familia_b() -> ArchitectureFamily:
    """Rotores distribuidos compactos, presos ao corpo. Sem estrutura larga."""
    return ArchitectureFamily(
        code="B",
        name="rotores distribuidos compactos",
        summary="quatro rotores de 45 cm num quadro junto ao tronco",
        geometry=anel_de_rotores(
            quantidade=4,
            raio_do_anel_m=0.45,
            raio_do_rotor_m=0.225,
            altura_m=-0.10,
            empuxo_max_N=to_si(70.0, "kgf"),
            empuxo_de_pairado_N=to_si(37.0, "kgf"),
            inclinacao_rad=math.radians(12.0),
        ),
        dry_mass_kg=PILOTO_KG + 28.0,
        energy_mass_kg=40.0,
        kind=PropulsionKind.ROTOR_BATTERY,
        disk_area_m2=area_de_rotores(4, 0.45),
        unmodelled=(
            "interferencia aerodinamica entre rotores proximos e o corpo",
            "massa real de motores, inversores e gerenciamento de bateria",
        ),
    )


def familia_c() -> ArchitectureFamily:
    """Rotores em estrutura lateral. Mais area, mais massa, mais braco de alavanca."""
    return ArchitectureFamily(
        code="C",
        name="rotores em estrutura lateral",
        summary="seis rotores de 70 cm numa estrutura que passa da largura do corpo",
        geometry=anel_de_rotores(
            quantidade=6,
            raio_do_anel_m=0.85,
            raio_do_rotor_m=0.35,
            altura_m=-0.05,
            empuxo_max_N=to_si(55.0, "kgf"),
            empuxo_de_pairado_N=to_si(30.0, "kgf"),
            inclinacao_rad=math.radians(10.0),
        ),
        dry_mass_kg=PILOTO_KG + 42.0,
        energy_mass_kg=55.0,
        kind=PropulsionKind.ROTOR_BATTERY,
        disk_area_m2=area_de_rotores(6, 0.70),
        unmodelled=(
            "massa estrutural real de uma estrutura desse vao",
            "efeito da estrutura no centro de massa e na inercia",
        ),
    )


def familia_d() -> ArchitectureFamily:
    """Estrutura larga tipo aeronave leve. Deixa de ser traje, e isso e o achado."""
    return ArchitectureFamily(
        code="D",
        name="estrutura larga, quatro rotores grandes",
        summary="quatro rotores de 1,1 m num vao de 2,4 m: ja nao e um traje",
        geometry=anel_de_rotores(
            quantidade=4,
            raio_do_anel_m=1.20,
            raio_do_rotor_m=0.55,
            altura_m=0.05,
            empuxo_max_N=to_si(90.0, "kgf"),
            empuxo_de_pairado_N=to_si(59.0, "kgf"),
            inclinacao_rad=math.radians(8.0),
        ),
        dry_mass_kg=PILOTO_KG + 65.0,
        energy_mass_kg=90.0,
        kind=PropulsionKind.ROTOR_BATTERY,
        disk_area_m2=area_de_rotores(4, 1.10),
        unmodelled=(
            "aerodinamica do piloto exposto numa estrutura desse tamanho",
            "o veiculo deixou de ser vestivel, entao o requisito mudou",
        ),
    )


def familia_e() -> ArchitectureFamily:
    """Turbina com canal eletrico rapido. Mesma geometria de A, mais massa."""
    familia = familia_a()
    return ArchitectureFamily(
        code="E",
        name="turbina com buffer eletrico",
        summary="geometria de A, mais um canal eletrico pequeno so para autoridade",
        geometry=familia.geometry,
        dry_mass_kg=familia.dry_mass_kg + 9.0,
        energy_mass_kg=20.0,
        kind=PropulsionKind.JET,
        tsfc_kg_per_N_s=TSFC_SI,
        unmodelled=(
            "o canal eletrico rapido NAO esta no modelo: entra como massa, nao como "
            "autoridade, entao esta familia so pode ser comparada com A em energia",
            "quanta autoridade rapida seria necessaria depende do atraso da turbina",
        ),
        notes=("so se separa de A quando houver dinamica com atraso",),
    )


def familia_f() -> ArchitectureFamily:
    """Hibrido serie: rotores movidos por gerador a combustao."""
    return ArchitectureFamily(
        code="F",
        name="hibrido serie",
        summary="geometria de C, mas gerador a combustao no lugar da bateria",
        geometry=familia_c().geometry,
        dry_mass_kg=PILOTO_KG + 42.0 + 48.0,
        energy_mass_kg=25.0,
        kind=PropulsionKind.ROTOR_GENERATOR,
        disk_area_m2=area_de_rotores(6, 0.70),
        chain_efficiency=0.28,
        unmodelled=(
            "massa de 48 kg para gerador, eletronica e termico e HIPOTESE, nao dado",
            "rendimento de cadeia de 0,28 e ordem de grandeza, nao medida",
            "potencia transitoria e derating termico do barramento",
        ),
    )


FAMILIAS = (familia_a(), familia_b(), familia_c(), familia_d(), familia_e(), familia_f())

ROTULOS = {
    ScreeningStage.INSTALLED_THRUST: "empuxo",
    ScreeningStage.ALLOCATION_RANK: "posto",
    ScreeningStage.NOMINAL_TRIM: "trim",
    ScreeningStage.LIFTOFF: "decola",
    ScreeningStage.LATERAL_CG: "cg lat",
    ScreeningStage.THRUST_HEADROOM: "folga",
    ScreeningStage.MISSION_ENERGY: "energia",
    ScreeningStage.SINGLE_FAILURE: "falha",
}


def main() -> None:
    criterios = ScreeningRequirements()
    resultados = run_funnel(FAMILIAS, criterios)

    print()
    print("EXPERIMENTO 3: FUNIL DE ARQUITETURAS")
    print("seis familias parametricas, oito filtros estaticos, do mais barato ao mais caro")
    print()
    print("CRITERIOS DECLARADOS DA CAMPANHA (mudar um muda quem sobrevive)")
    print(f"  posto minimo da alocacao:        {criterios.min_rank} de 6")
    print(f"  rolagem pura exigida:            {'sim' if criterios.require_pure_roll else 'nao'}")
    print(f"  aceleracao de saida do chao:     {criterios.liftoff_acceleration_m_s2:.2f} m/s2")
    print(f"  desvio lateral de centro de massa: {criterios.lateral_cg_tolerance_m * 100:.1f} cm")
    print(f"  folga superior de empuxo:        {criterios.min_thrust_headroom:.0%}")
    print(f"  autonomia minima de pairado:     {criterios.min_hover_endurance_s / 60:.1f} min")
    print()

    print("MASSAS E GEOMETRIA DECLARADAS POR FAMILIA")
    cab = f"{'':2} {'familia':32} {'seco':>6} {'energia':>8} {'bruto':>6} {'n':>3} {'T inst':>8}"
    print(cab)
    print(f"{'':2} {'':32} {'kg':>6} {'kg':>8} {'kg':>6} {'':>3} {'kgf':>8}")
    print("-" * len(cab))
    for f in FAMILIAS:
        print(
            f"{f.code:2} {f.name:32} {f.dry_mass_kg:6.0f} {f.energy_mass_kg:8.0f} "
            f"{f.gross_mass_kg:6.0f} {f.geometry.count:3} "
            f"{f.installed_thrust_N / 9.80665:8.0f}"
        )
    print()

    print("O FUNIL: ok = passou, X = morreu aqui, ponto = nem foi avaliado")
    cab2 = f"{'':2} {'familia':32} " + " ".join(f"{ROTULOS[s]:>7}" for s in ScreeningStage)
    print(cab2)
    print("-" * len(cab2))
    for r in resultados:
        celulas = []
        for estagio in ScreeningStage:
            achou = [o for o in r.outcomes if o.stage is estagio]
            if not achou:
                celulas.append(f"{'.':>7}")
            else:
                celulas.append(f"{('ok' if achou[0].passed else 'X'):>7}")
        print(f"{r.family.code:2} {r.family.name:32} " + " ".join(celulas))
    print()

    print("ONDE CADA UMA MORREU, E COM QUE NUMERO")
    for r in resultados:
        if r.survived:
            print(f"  {r.family.code}: SOBREVIVEU aos oito filtros")
            for estagio in (
                ScreeningStage.LATERAL_CG,
                ScreeningStage.THRUST_HEADROOM,
                ScreeningStage.MISSION_ENERGY,
                ScreeningStage.SINGLE_FAILURE,
            ):
                detalhe = next(o for o in r.outcomes if o.stage is estagio)
                print(f"       {ROTULOS[estagio]:>8}: {detalhe.detail}")
        else:
            morte = next(o for o in r.outcomes if not o.passed)
            print(f"  {r.family.code}: morreu em {ROTULOS[morte.stage]!r} -> {morte.detail}")
    print()

    print("MORTALIDADE POR FILTRO")
    for estagio, quantas in mortality_by_stage(resultados).items():
        if quantas:
            print(f"  {ROTULOS[estagio]:>8}: {quantas}")
    print()

    vivas = survivors(resultados)
    print(f"CANDIDATAS QUE MERECEM DINAMICA: {len(vivas)} de {len(resultados)}")
    for r in vivas:
        print(f"  {r.family.code} - {r.family.name}")
        for lacuna in r.family.unmodelled:
            print(f"      fora do modelo: {lacuna}")
    if not vivas:
        print("  nenhuma. Nenhuma destas familias fecha os criterios declarados.")
    print()

    veredito, motivo = selection_verdict()
    print(f"VEREDITO DE SELECAO DE TECNOLOGIA: {veredito.name}")
    print(f"  {motivo}")
    print()
    print("⚠ Todos os oito filtros sao ESTATICOS. Nenhum ve atraso, rampa ou")
    print("  estabilidade. Sobreviver aqui significa 'merece receber dinamica',")
    print("  nunca 'funciona'.")


if __name__ == "__main__":
    main()
