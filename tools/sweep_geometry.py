# -*- coding: utf-8 -*-
"""Experimento 1: quais geometrias congeladas admitem trim e preservam autoridade.

Roda com::

    ./.venv/Scripts/python.exe tools/sweep_geometry.py

Nao faz parte do nucleo: so consome a API publica, nao adiciona superficie.

⚠ Toda geometria aqui e **plausivel, nao medida**, e todo resultado e condicional a
pairado nivelado com pose e massa congeladas. A pergunta que este experimento
responde nao e "qual traje construir". E:

    Quais classes de geometria NAO merecem dinamica, porque nao fecham trim ou
    falham com deslocamento minimo de centro de massa?

Eliminar candidata ruim cedo e o proposito do codigo.
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
    PropulsionGeometry,
    allocation_matrix,
    parametric_layout,
)
from hero_atlas.analysis.authority import (  # noqa: E402
    analyse_authority,
    lateral_cg_authority,
    cg_window,
    single_failure_survey,
)
from hero_atlas.analysis.trim import (  # noqa: E402
    InfeasibilityCause,
    TrimObjective,
    solve_trim,
)
from hero_atlas.units import G0, to_si  # noqa: E402

MASSA_KG = 117.0
EMPUXO_MAX = to_si(35.0, "kgf")
T25 = math.radians(25.0)
T15 = math.radians(15.0)


def acoplamento_lateral_rolagem(geo: PropulsionGeometry) -> bool:
    """Se forca lateral e momento de rolagem sao o mesmo canal."""
    W = allocation_matrix(geo)
    ativos = np.abs(W[1, :]) > 1e-9
    if ativos.sum() < 2:
        return False
    razoes = W[3, ativos] / W[1, ativos]
    return bool(np.allclose(razoes, razoes[0], atol=1e-9))


def _folga_minima(geo: PropulsionGeometry, solucao) -> float:
    """Folga do trim de margem maxima, em kgf.

    ⚠ Posto diz se a direcao existe; **isto** diz se sobra empuxo para usa-la.
    Exige trim de ``MAX_MARGIN``: com ``MIN_THRUST`` a solucao encosta nos limites
    por construcao e a folga sai zero sempre, o que seria artefato do objetivo.
    """
    del geo
    return solucao.margin_N / G0 if solucao.feasible else 0.0


@dataclass(frozen=True)
class Resultado:
    nome: str
    n_bocais: int
    posto: int
    acoplado: bool
    trim_viavel: bool
    causa: str
    janela_long_cm: float
    janela_lat_cm: float
    projecao_vertical: float
    falhas_toleradas: int
    condicionamento: float
    rolagem_pura: bool
    menor_singular: float
    folga_min_kgf: float


def avaliar(nome: str, geo: PropulsionGeometry) -> Resultado:
    mapa = analyse_authority(geo)

    # centro de massa: procura o melhor ponto longitudinal antes de medir o resto
    janela_x = cg_window(geo, mass_kg=MASSA_KG, axis=0, span_m=(-0.40, 0.60), step_m=0.005)
    cg_x = 0.0 if janela_x is None else 0.5 * (janela_x[0] + janela_x[1])

    # ⚠ max_margin, nao min_thrust: minimizar empuxo encosta nos limites por
    # construcao, e reportaria folga zero como se fosse propriedade da arquitetura.
    solucao = solve_trim(
        geo,
        mass_kg=MASSA_KG,
        center_of_mass_body_m=[cg_x, 0.0, 0.0],
        objective=TrimObjective.MAX_MARGIN,
    )

    janela_y = cg_window(
        geo,
        mass_kg=MASSA_KG,
        axis=1,
        span_m=(-0.15, 0.15),
        step_m=0.002,
        fixed_cg_m=(cg_x, 0.0, 0.0),
    )

    falhas = single_failure_survey(geo, mass_kg=MASSA_KG, center_of_mass_body_m=[cg_x, 0.0, 0.0])
    toleradas = sum(1 for c in falhas.values() if c is InfeasibilityCause.NONE)

    return Resultado(
        nome=nome,
        n_bocais=geo.count,
        posto=mapa.rank,
        acoplado=acoplamento_lateral_rolagem(geo),
        trim_viavel=solucao.feasible,
        causa="-" if solucao.feasible else solucao.cause.value[:12],
        janela_long_cm=0.0 if janela_x is None else 100 * (janela_x[1] - janela_x[0]),
        janela_lat_cm=0.0 if janela_y is None else 100 * (janela_y[1] - janela_y[0]),
        projecao_vertical=solucao.vertical_thrust_projection_ratio,
        falhas_toleradas=toleradas,
        condicionamento=mapa.condition_number,
        rolagem_pura=lateral_cg_authority(geo),
        menor_singular=mapa.smallest_nonzero_singular,
        folga_min_kgf=_folga_minima(geo, solucao),
    )


def variantes() -> list[tuple[str, PropulsionGeometry]]:
    """Nove arquiteturas, cada uma isolando uma decisao de projeto."""
    base = [
        ArmPairSpec(forward_m=0.30, span_m=0.35, height_m=-0.20, lateral_tilt_rad=T25),
        ArmPairSpec(forward_m=0.15, span_m=0.35, height_m=-0.20, lateral_tilt_rad=T25),
    ]
    dorsal = [AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)]

    def build(pares, axiais=dorsal):
        return parametric_layout(
            pairs=pares, axial=axiais, thrust_max_N=EMPUXO_MAX, idle_fraction=0.10
        )

    return [
        ("base 5 bocais", build(base)),
        (
            "altura escalonada",
            build(
                [
                    base[0],
                    ArmPairSpec(0.15, 0.35, -0.32, T25),
                ]
            ),
        ),
        (
            "envergadura escalonada",
            build([base[0], ArmPairSpec(0.15, 0.48, -0.20, T25)]),
        ),
        (
            "inclinacao lateral escalonada",
            build([base[0], ArmPairSpec(0.15, 0.35, -0.20, math.radians(45.0))]),
        ),
        (
            "com inclinacao longitudinal",
            build(
                [
                    ArmPairSpec(0.30, 0.35, -0.20, T25, longitudinal_tilt_rad=+T15),
                    ArmPairSpec(0.15, 0.35, -0.20, T25, longitudinal_tilt_rad=-T15),
                ]
            ),
        ),
        (
            "altura + longitudinal",
            build(
                [
                    ArmPairSpec(0.30, 0.35, -0.20, T25, longitudinal_tilt_rad=+T15),
                    ArmPairSpec(0.15, 0.35, -0.32, T25, longitudinal_tilt_rad=-T15),
                ]
            ),
        ),
        (
            "tres pares, altura escalonada",
            build(
                [
                    ArmPairSpec(0.32, 0.35, -0.15, T25),
                    ArmPairSpec(0.20, 0.35, -0.26, T25),
                    ArmPairSpec(0.08, 0.35, -0.37, T25),
                ]
            ),
        ),
        (
            "tres pares + longitudinal",
            build(
                [
                    ArmPairSpec(0.32, 0.35, -0.15, T25, longitudinal_tilt_rad=+T15),
                    ArmPairSpec(0.20, 0.35, -0.26, T25),
                    ArmPairSpec(0.08, 0.35, -0.37, T25, longitudinal_tilt_rad=-T15),
                ]
            ),
        ),
        (
            "3 pares, tudo escalonado",
            build(
                [
                    ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0)),
                    ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
                    ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0)),
                ]
            ),
        ),
        (
            "3 pares escalonados + longitudinal",
            build(
                [
                    ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +T15),
                    ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
                    ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -T15),
                ]
            ),
        ),
        (
            "dois pares + dois dorsais",
            build(
                [
                    ArmPairSpec(0.30, 0.35, -0.20, T25, longitudinal_tilt_rad=+T15),
                    ArmPairSpec(0.15, 0.35, -0.32, T25),
                ],
                axiais=[
                    AxialNozzleSpec("dorsal_sup", forward_m=-0.15, height_m=-0.05),
                    AxialNozzleSpec(
                        "dorsal_inf", forward_m=-0.28, height_m=0.15, longitudinal_tilt_rad=-T15
                    ),
                ],
            ),
        ),
    ]


def main() -> None:
    print()
    print("EXPERIMENTO 1: geometria de autoridade")
    print("massa 117 kg, empuxo maximo 35 kgf por bocal, marcha lenta 10 por cento")
    print("ATENCAO: geometrias plausiveis, nao medidas. Pairado nivelado, pose congelada.")
    print()

    cab = (
        f"{'arquitetura':30} {'n':>2} {'posto':>5} {'acopl':>6} {'trim':>5} "
        f"{'jan_x':>6} {'jan_y':>6} {'roll':>5} {'sigma':>7} {'folga':>6} {'falhas':>6}"
    )
    print(cab)
    print("-" * len(cab))

    resultados = [avaliar(nome, geo) for nome, geo in variantes()]
    for r in resultados:
        trim = "sim" if r.trim_viavel else r.causa[:5]
        print(
            f"{r.nome:30} {r.n_bocais:2} {r.posto:2}/6   "
            f"{'SIM' if r.acoplado else 'nao':>6} {trim:>5} "
            f"{r.janela_long_cm:5.1f}  {r.janela_lat_cm:5.1f}  "
            f"{'SIM' if r.rolagem_pura else 'nao':>5} "
            f"{r.menor_singular:7.4f} {r.folga_min_kgf:6.1f} {r.falhas_toleradas:2}/{r.n_bocais:<3}"
        )

    print()
    print("legenda: jan_x e jan_y em cm; roll = rolagem pura sem forca lateral;")
    print("         sigma = menor valor singular, quao FRACA e a direcao mais fraca;")
    print("         folga = empuxo em kgf ate o limite mais proximo no trim;")
    print("         falhas = perdas unicas que ainda admitem trim")
    print()

    sobreviventes = [r for r in resultados if r.trim_viavel and r.rolagem_pura and r.posto >= 5]
    print(f"CANDIDATAS QUE MERECEM DINAMICA: {len(sobreviventes)} de {len(resultados)}")
    for r in sobreviventes:
        print(
            f"  {r.nome}: posto {r.posto}, janela lateral {r.janela_lat_cm:.1f} cm, "
            f"{r.falhas_toleradas} perdas toleradas"
        )
    if not sobreviventes:
        print("  nenhuma. Nenhuma destas classes fecha os criterios minimos.")


if __name__ == "__main__":
    main()
