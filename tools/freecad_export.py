"""Exporta propriedades de massa de um documento FreeCAD para o deck do projeto.

⚠ **Este script NAO roda no Python do projeto.** Ele roda no Python que vem com o
FreeCAD, porque ``FreeCAD.pyd`` e binario compilado para a versao dele.

    FreeCAD 1.1 traz Python 3.11; o projeto roda em 3.12. Nao ha como importar um no
    outro, e por isso a ponte e por arquivo.

Uso::

    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py \
        modelo.FCStd docs/decks/traje.json --z-para-baixo

Ou, para gerar um deck de exemplo sem abrir o FreeCAD::

    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py --demo saida.json

O deck resultante e lido por ``hero_atlas.airframe.cad_deck.load_cad_deck``, que faz a
conversao de unidade. **Este script nao converte nada**: ele exporta o que o FreeCAD
da, em milimetro e densidade unitaria, e deixa a conversao num lugar so, com teste.

Densidade. O FreeCAD nao sabe a massa de uma peca sem material atribuido. O script
aceita um arquivo de densidades por nome de objeto e, na falta dele, exige massa
declarada. **Ele nunca chuta material.**
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

SCHEMA_VERSION = 1

DENSIDADES_PADRAO_KG_M3 = {
    "aluminio": 2700.0,
    "aco": 7850.0,
    "titanio": 4500.0,
    "fibra_de_carbono": 1600.0,
    "querosene": 800.0,
}
"""⚠ Ordem de grandeza para peca conceitual. Nao substitui ficha de material."""


def _propriedades(obj):
    """Extrai volume, centro e tensor de uma forma solida do FreeCAD."""
    forma = getattr(obj, "Shape", None)
    if forma is None or not forma.Solids:
        return None
    matriz = forma.MatrixOfInertia
    tensor = [
        [matriz.A11, matriz.A12, matriz.A13],
        [matriz.A21, matriz.A22, matriz.A23],
        [matriz.A31, matriz.A32, matriz.A33],
    ]
    return {
        "volume_mm3": float(forma.Volume),
        "center_of_mass_mm": [float(c) for c in tuple(forma.CenterOfMass)],
        "inertia_matrix": tensor,
    }


def exporta(documento: str, saida: str, *, z_para_baixo: bool, densidades: dict) -> None:
    import FreeCAD  # noqa: PLC0415  so existe no Python do FreeCAD

    doc = FreeCAD.openDocument(documento)
    doc.recompute()

    componentes = []
    ignorados = []
    for obj in doc.Objects:
        props = _propriedades(obj)
        if props is None:
            ignorados.append(obj.Name)
            continue

        nome = obj.Label or obj.Name
        material = densidades.get(nome, {}).get("material", "nao declarado")
        densidade = densidades.get(nome, {}).get("density_kg_m3")
        massa = densidades.get(nome, {}).get("mass_kg")

        if massa is None:
            if densidade is None:
                raise SystemExit(
                    f"objeto {nome!r} sem massa nem densidade declarada. Este script "
                    "NAO chuta material: declare em um arquivo de densidades, ou de "
                    "massa direta. Chutar densidade aqui produziria inercia plausivel "
                    "e errada, que e o pior resultado possivel."
                )
            massa = props["volume_mm3"] * 1e-9 * densidade

        componentes.append(
            {
                "name": nome,
                "mass_kg": float(massa),
                "material": material,
                **props,
                "orientation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            }
        )

    if ignorados:
        print(f"⚠ ignorados por nao terem solido: {ignorados}", file=sys.stderr)
    if not componentes:
        raise SystemExit("nenhum objeto com solido no documento")

    deck = {
        "schema_version": SCHEMA_VERSION,
        "source_document": Path(documento).name,
        "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "z_axis_down": bool(z_para_baixo),
        "components": componentes,
    }
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_text(json.dumps(deck, indent=2, ensure_ascii=False), encoding="utf-8")
    massa_total = sum(c["mass_kg"] for c in componentes)
    print(f"{len(componentes)} componentes, {massa_total:.2f} kg, escrito em {saida}")


def demo(saida: str) -> None:
    """Gera um deck de uma caixa conhecida, para exercitar a ponte de ponta a ponta.

    A caixa de 100 por 200 por 300 milimetros tem solucao analitica, entao serve para
    conferir a conversao de unidade sem depender de um modelo real.
    """
    import FreeCAD  # noqa: PLC0415

    doc = FreeCAD.newDocument("demo")
    caixa = doc.addObject("Part::Box", "CaixaDeReferencia")
    caixa.Length, caixa.Width, caixa.Height = 100.0, 200.0, 300.0
    doc.recompute()

    props = _propriedades(caixa)
    deck = {
        "schema_version": SCHEMA_VERSION,
        "source_document": "demo, caixa 100x200x300 mm",
        "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "z_axis_down": True,
        "components": [
            {
                "name": "caixa_de_referencia",
                "mass_kg": 1.0,
                "material": "fictício, massa declarada",
                **props,
                "orientation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            }
        ],
    }
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_text(json.dumps(deck, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"deck de demonstracao escrito em {saida}")
    print("conferencia analitica esperada, para 1 kg:")
    print("  I_xx = m(b^2+c^2)/12 = (0.2^2 + 0.3^2)/12 = 0.0108333 kg m2")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("documento", nargs="?", help="arquivo .FCStd")
    p.add_argument("saida", nargs="?", help="deck JSON de saida")
    p.add_argument("--demo", metavar="SAIDA", help="gera deck de caixa conhecida")
    p.add_argument(
        "--z-para-baixo",
        action="store_true",
        help="o documento JA esta com z apontando para baixo, conforme ADR-001",
    )
    p.add_argument("--densidades", help="JSON com massa ou densidade por nome de objeto")
    args = p.parse_args()

    if args.demo:
        demo(args.demo)
        return
    if not args.documento or not args.saida:
        p.error("informe documento e saida, ou use --demo")

    densidades = {}
    if args.densidades:
        densidades = json.loads(Path(args.densidades).read_text(encoding="utf-8"))

    exporta(
        args.documento,
        args.saida,
        z_para_baixo=args.z_para_baixo,
        densidades=densidades,
    )


if __name__ == "__main__":
    main()
