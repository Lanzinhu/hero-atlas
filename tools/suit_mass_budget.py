"""Orcamento de massa do traje inteiro, e se o trim fecha com ele.

Roda no Python do projeto::

    ./.venv/Scripts/python.exe tools/suit_mass_budget.py

Soma, com o agregador do projeto:

    piloto            manequim em pose de pairado, docs/decks/manequim/
    sete turbinas     modelo de referencia, docs/decks/referencia/
    combustivel       20 kg em caixa nas costas, posicao do guia de modelagem
    estrutura         12 kg distribuidos conforme o guia de modelagem, passo 6

e depois pergunta ao solver de trim se a geometria A equilibra essa massa.

ATENCAO: as posicoes do tanque e da estrutura sao as DECLARADAS no guia de modelagem,
nao otimizadas. Um trim que nao fecha aqui reprova ESTE arranjo de massa com ESTA
geometria. Nao prova que nenhum arranjo funciona; mede quanto ele precisaria mudar.

ATENCAO: o tanque e a estrutura sao caixas e pontos de densidade uniforme. O piloto e
feito de primitivos com fracoes de massa NAO verificadas, ver
docs/sources/de-leva-1996-segmentos-NAO-VERIFICADO.md.
"""

from __future__ import annotations

import math
import sys

import numpy as np

sys.path.insert(0, "src")

from hero_atlas.airframe.cad_deck import load_cad_deck  # noqa: E402
from hero_atlas.airframe.geometry import (  # noqa: E402
    ArmPairSpec,
    AxialNozzleSpec,
    parametric_layout,
)
from hero_atlas.airframe.mass_properties import (  # noqa: E402
    MassComponent,
    aggregate_mass_properties,
)
from hero_atlas.analysis.authority import cg_window  # noqa: E402
from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.units import G0  # noqa: E402

MASSA_COMBUSTIVEL_KG = 20.0
POSICAO_TANQUE_MM = (-220.0, 0.0, 50.0)

INERCIA_ASSUMIDA = (32.20, 32.20, 2.30)
MASSA_ASSUMIDA_KG = 115.0
CENTRO_ASSUMIDO_X_MM = 157.5

SAIDAS_MM = {
    "par0_esq": (320.0, -300.0, -150.0),
    "par0_dir": (320.0, 300.0, -150.0),
    "par1_esq": (200.0, -400.0, -260.0),
    "par1_dir": (200.0, 400.0, -260.0),
    "par2_esq": (20.0, -350.0, -370.0),
    "par2_dir": (20.0, 350.0, -370.0),
    "dorsal": (-150.0, 0.0, 100.0),
}


def _caixa(nome: str, massa: float, centro_mm, dx: float, dy: float, dz: float) -> MassComponent:
    a, b, c = dx / 1000.0, dy / 1000.0, dz / 1000.0
    tensor = np.diag(
        [
            massa * (b * b + c * c) / 12.0,
            massa * (a * a + c * c) / 12.0,
            massa * (a * a + b * b) / 12.0,
        ]
    )
    return MassComponent(
        nome, massa, np.asarray(centro_mm, dtype=float) / 1000.0, tensor, np.eye(3)
    )


def _ponto(nome: str, massa: float, centro_mm, raio_mm: float = 20.0) -> MassComponent:
    """Massa quase pontual. Esfera pequena, para o tensor nao ser singular."""
    r = raio_mm / 1000.0
    tensor = np.eye(3) * 0.4 * massa * r * r
    return MassComponent(
        nome, massa, np.asarray(centro_mm, dtype=float) / 1000.0, tensor, np.eye(3)
    )


def _geometria(teto_N: float):
    t15 = math.radians(15.0)
    return parametric_layout(
        pairs=[
            ArmPairSpec(0.32, 0.30, -0.15, math.radians(15.0), +t15),
            ArmPairSpec(0.20, 0.40, -0.26, math.radians(30.0)),
            ArmPairSpec(0.02, 0.35, -0.37, math.radians(45.0), -t15),
        ],
        axial=[AxialNozzleSpec(name="dorsal", forward_m=-0.15, height_m=0.10)],
        thrust_max_N=teto_N,
        idle_fraction=0.10,
    )


def componentes():
    piloto = list(load_cad_deck("docs/decks/manequim/manequim_pairado.json").to_mass_components())
    referencia = load_cad_deck("docs/decks/referencia/referencia.json").to_mass_components()
    turbinas = [c for c in referencia if c.name.startswith("turbina_")]

    estrutura = [
        _caixa("controle_bateria", 2.5, (-180.0, 0.0, -120.0), 200.0, 150.0, 80.0),
        _caixa("bomba_valvulas", 1.5, (-200.0, 0.0, 180.0), 90.0, 90.0, 140.0),
        _caixa("cinto_arnes", 2.4, (0.0, 0.0, 200.0), 230.0, 420.0, 30.0),
        _ponto("linhas_esq", 0.9, (200.0, -300.0, -250.0)),
        _ponto("linhas_dir", 0.9, (200.0, 300.0, -250.0)),
    ]
    for nome, posicao in SAIDAS_MM.items():
        estrutura.append(_ponto(f"berco_{nome}", 2.0 / 7.0, posicao))
    for t in turbinas:
        estrutura.append(
            _ponto(f"termica_{t.name}", 1.8 / 7.0, tuple(t.center_of_mass_body_m * 1000.0))
        )

    combustivel = [
        _caixa("combustivel", MASSA_COMBUSTIVEL_KG, POSICAO_TANQUE_MM, 208.0, 300.0, 400.0)
    ]
    return piloto, turbinas, estrutura, combustivel


def _linha(rotulo: str, comps) -> object:
    ag = aggregate_mass_properties(tuple(comps))
    tensor = ag.inertia_about_cg_kg_m2
    cg = ag.center_of_mass_body_m * 1000.0
    print(
        f"  {rotulo:24} {ag.mass_kg:7.2f} kg  "
        f"cg ({cg[0]:+6.1f}, {cg[1]:+5.1f}, {cg[2]:+6.1f}) mm  "
        f"Ixx {tensor[0, 0]:6.2f}  Iyy {tensor[1, 1]:6.2f}  Izz {tensor[2, 2]:5.2f}  "
        f"Ixz {tensor[0, 2]:+5.2f}"
    )
    return ag


def main() -> None:
    piloto, turbinas, estrutura, combustivel = componentes()

    print()
    print("ORCAMENTO DE MASSA DO TRAJE INTEIRO")
    print("somado pelo agregador do projeto; posicoes de tanque e estrutura do guia")
    print()
    _linha("piloto em pairado", piloto)
    _linha("sete turbinas K-260G4", turbinas)
    _linha("estrutura, 12 kg", estrutura)
    _linha("combustivel, 20 kg", combustivel)
    print("  " + "-" * 110)
    total = _linha("TRAJE COMPLETO", piloto + turbinas + estrutura + combustivel)
    tensor = total.inertia_about_cg_kg_m2
    print(
        f"  {'assumido ate hoje':24} {MASSA_ASSUMIDA_KG:7.2f} kg  "
        f"cg ({CENTRO_ASSUMIDO_X_MM:+6.1f},  +0.0,   +0.0) mm  "
        f"Ixx {INERCIA_ASSUMIDA[0]:6.2f}  Iyy {INERCIA_ASSUMIDA[1]:6.2f}  "
        f"Izz {INERCIA_ASSUMIDA[2]:5.2f}  Ixz +0.00"
    )
    print()
    print("RAZAO modelado / assumido")
    print(f"  Ixx {tensor[0, 0] / INERCIA_ASSUMIDA[0]:.2f}x")
    print(f"  Iyy {tensor[1, 1] / INERCIA_ASSUMIDA[1]:.2f}x")
    print(f"  Izz {tensor[2, 2] / INERCIA_ASSUMIDA[2]:.2f}x   <-- guinada")
    print()
    print("  ATENCAO: a checagem de sensibilidade a inercia do experimento 6 escalou os")
    print("  tres eixos JUNTOS, de 0,7 a 1,6 vezes. Uma guinada 3,4 vezes maior esta fora")
    print("  da faixa testada, e o experimento 4 usou tensor diagonal, sem o Ixz acima.")
    print()

    massa = total.mass_kg
    cg_x = float(total.center_of_mass_body_m[0])
    centro = [cg_x, 0.0, float(total.center_of_mass_body_m[2])]

    print("O TRIM FECHA COM ESTE TRAJE?")
    print()
    for rotulo, teto in (
        ("classe generica 35 kgf", 35.0 * G0),
        ("K-260G4 real, 26 kgf", 26.0 * G0),
    ):
        geo = _geometria(teto)
        sol = solve_trim(
            geo, mass_kg=massa, center_of_mass_body_m=centro, objective=TrimObjective.MAX_MARGIN
        )
        janela = cg_window(geo, mass_kg=massa, axis=0, span_m=(-0.40, 0.60), step_m=0.005)
        print(f"  --- {rotulo} ---")
        print(
            f"  trim no centro modelado, x = {cg_x * 1000:+.1f} mm: "
            + ("FECHA" if sol.feasible else f"NAO FECHA ({sol.cause.value})")
        )
        if janela is None:
            print("  janela longitudinal viavel: NENHUMA a esta massa")
            print()
            continue
        print(f"  janela longitudinal viavel: {janela[0] * 1000:+.0f} a {janela[1] * 1000:+.0f} mm")
        falta = janela[0] - cg_x
        if falta > 0:
            print(f"  o centro esta {falta * 1000:.0f} mm ATRAS do limite traseiro")
            mover = falta * massa / MASSA_COMBUSTIVEL_KG
            destino_x = POSICAO_TANQUE_MM[0] + mover * 1000
            print(
                f"  so movendo o tanque: {mover * 1000:.0f} mm para frente, "
                f"de x = {POSICAO_TANQUE_MM[0]:+.0f} para x = {destino_x:+.0f} mm"
            )
            lastro = falta * massa / (0.32 - janela[0])
            print(f"  ou lastro no bocal dianteiro, x = +320 mm: {lastro:.1f} kg")
        print()

    print("LEITURA")
    print()
    print("  As duas correcoes sao absurdas: um tanque na frente do peito, ou um lastro")
    print("  maior que o proprio piloto. Isso nao e ajuste fino. E incompatibilidade entre")
    print("  a geometria A, cuja janela de trim fica bem a frente, e um tanque nas costas.")
    print()
    print("  E ha uma segunda reprovacao, independente, no portao de envelope: a turbina")
    print("  dorsal fica dentro das costas do piloto. Ver docs/resultados/portao-envelope.txt.")
    print()
    print("  HIPOTESE NAO TESTADA: recuar o bocal dorsal resolveria a colisao e, ao mesmo")
    print("  tempo, puxaria a janela de trim para tras, na direcao do centro modelado. O")
    print("  guia de modelagem manda parar e avisar quando um portao reprova, entao a")
    print("  tabela de coordenadas NAO foi alterada aqui.")


if __name__ == "__main__":
    main()
