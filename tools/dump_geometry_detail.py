"""Despejo auditavel da geometria sobrevivente: bocal a bocal, matriz e trim.

Roda com::

    ./.venv/Scripts/python.exe tools/dump_geometry_detail.py

Existe porque as tabelas dos experimentos viviam so no terminal de quem rodou. Um
revisor que le o repositorio sem executar nada precisa conseguir **conferir os numeros
centrais**, e para isso precisa ver a geometria, a matriz de alocacao e a distribuicao
de empuxo do trim, nao so a conclusao.

⚠ Geometria **plausivel, nao medida**. Nada aqui representa hardware.
"""

from __future__ import annotations

import math
import sys

import numpy as np

sys.path.insert(0, "src")

from hero_atlas.airframe.geometry import (  # noqa: E402
    ArmPairSpec,
    AxialNozzleSpec,
    allocation_matrix,
    parametric_layout,
)
from hero_atlas.analysis.authority import analyse_authority, cg_window  # noqa: E402
from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.units import G0, to_si  # noqa: E402

MASSA_KG = 117.0
EMPUXO_MAX_KGF = 35.0


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
        thrust_max_N=to_si(EMPUXO_MAX_KGF, "kgf"),
        idle_fraction=0.10,
    )


def main() -> None:
    geo = geometria()

    print()
    print("GEOMETRIA SOBREVIVENTE, DESPEJO AUDITAVEL")
    print("tres pares de braco com envergadura, altura e inclinacao escalonadas,")
    print("mais um bocal dorsal. ATENCAO: plausivel, nao medida.")
    print()
    print(f"massa de referencia {MASSA_KG:.0f} kg, teto {EMPUXO_MAX_KGF:.0f} kgf por bocal")
    print(f"ponto de referencia no corpo: {geo.reference_point_body_m}")
    print()

    print("BOCAIS: posicao e direcao no referencial do corpo")
    cab = (
        f"{'nome':12} {'x':>7} {'y':>7} {'z':>7} | "
        f"{'nx':>7} {'ny':>7} {'nz':>7} | {'Tmin':>6} {'Tmax':>6}"
    )
    print(cab)
    print(
        f"{'':12} {'m':>7} {'m':>7} {'m':>7} | {'-':>7} {'-':>7} {'-':>7} | {'kgf':>6} {'kgf':>6}"
    )
    print("-" * len(cab))
    for bocal in geo.nozzles:
        p = bocal.position_body_m
        d = bocal.direction_body
        print(
            f"{bocal.name:12} {p[0]:7.3f} {p[1]:7.3f} {p[2]:7.3f} | "
            f"{d[0]:7.4f} {d[1]:7.4f} {d[2]:7.4f} | "
            f"{bocal.thrust_min_N / G0:6.2f} {bocal.thrust_max_N / G0:6.2f}"
        )
    print()

    W = allocation_matrix(geo)
    print("MATRIZ DE ALOCACAO W, seis linhas por sete colunas")
    print("linhas: Fx Fy Fz Mx My Mz   colunas: um bocal cada, na ordem acima")
    print("(forca adimensional por newton de empuxo; momento em metro por newton)")
    print()
    rotulos = ["Fx", "Fy", "Fz", "Mx", "My", "Mz"]
    print(f"{'':4}" + "".join(f"{b.name:>12}" for b in geo.nozzles))
    for i, rotulo in enumerate(rotulos):
        print(f"{rotulo:4}" + "".join(f"{W[i, j]:12.5f}" for j in range(W.shape[1])))
    print()

    mapa = analyse_authority(geo)
    print("AUTORIDADE")
    print(f"  posto:                    {mapa.rank} de 6")
    print(f"  valores singulares:       {np.array2string(mapa.singular_values, precision=5)}")
    print(f"  menor nao nulo:           {mapa.smallest_nonzero_singular:.6f}")
    print(f"  condicionamento:          {mapa.condition_number:.2f}")
    print(f"  graus de atuador ociosos: {mapa.wasted_actuator_freedoms}")
    print()

    janela = cg_window(geo, mass_kg=MASSA_KG, axis=0, span_m=(-0.40, 0.60), step_m=0.005)
    cg_x = 0.5 * (janela[0] + janela[1])
    print("CENTRO DE MASSA")
    print(f"  janela longitudinal viavel: [{janela[0]:.4f}, {janela[1]:.4f}] m")
    print(f"  usado nos trims abaixo:     x = {cg_x:.4f} m, y = 0, z = 0")
    print()

    print("TRIM: a distribuicao de empuxo nao e uniforme, e depende do objetivo")
    print()
    for objetivo in (TrimObjective.MIN_THRUST, TrimObjective.MAX_MARGIN):
        s = solve_trim(
            geo,
            mass_kg=MASSA_KG,
            center_of_mass_body_m=[cg_x, 0.0, 0.0],
            objective=objetivo,
        )
        empuxos = s.thrusts_N / G0
        print(f"  --- objetivo: {objetivo.value} --- viavel: {s.feasible}")
        for nome, valor in zip(s.nozzle_names, empuxos, strict=True):
            marca = "  <-- NO TETO" if abs(valor - EMPUXO_MAX_KGF) < 1e-6 else ""
            print(f"      {nome:12} {valor:7.3f} kgf{marca}")
        print(
            f"      soma {empuxos.sum():.3f} kgf | menor {empuxos.min():.3f} | "
            f"maior {empuxos.max():.3f} | media {empuxos.mean():.3f}"
        )
        print(f"      razao de projecao vertical:  {s.vertical_thrust_projection_ratio:.6f}")
        print(f"      folga ao limite mais proximo: {s.margin_N / G0:.3f} kgf")
        folga_sup = min(
            1.0 - t / n.thrust_max_N for t, n in zip(s.thrusts_N, geo.available, strict=True)
        )
        print(f"      menor folga superior, fracao do teto: {folga_sup:.6f}")
        print(f"      limites ativos: {s.active_constraints or '(nenhum)'}")
        print()

    s = solve_trim(geo, mass_kg=MASSA_KG, center_of_mass_body_m=[cg_x, 0.0, 0.0])
    print("CONFERENCIA: peso dividido pela razao de projecao da a soma de empuxo")
    print(
        f"  {MASSA_KG:.1f} / {s.vertical_thrust_projection_ratio:.6f} = "
        f"{MASSA_KG / s.vertical_thrust_projection_ratio:.3f} kgf"
    )
    print(f"  soma dos empuxos do trim:               {s.total_thrust_N / G0:.3f} kgf")
    print()
    print("⚠ E por isso que 'massa dividida pelo numero de bocais' esta errado: ignora")
    print("  a projecao vertical e supoe distribuicao uniforme, que o solver desmente.")


if __name__ == "__main__":
    main()
