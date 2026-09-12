"""Gera o modelo de referencia no FreeCAD, para conferir a mao contra o correto.

⚠ **Roda no Python do FreeCAD**, nao no do projeto.

    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_reference_model.py saida/

Produz tres coisas em ``saida/``:

    referencia.FCStd      documento com a caixa de calibracao e os sete propulsores
    referencia.json       deck exportado, pronto para o simulador ler
    densidades.json       exemplo do arquivo de massa por objeto

O proposito e pedagogico e de verificacao ao mesmo tempo. Quem esta aprendendo CAD
modela a mao e compara com este arquivo; quem ja sabe usa para conferir se a ponte de
exportacao continua correta depois de mexer nela.

⚠ **A colocacao do cilindro da turbina tem um sinal que e facil de errar.** O ponto
tabelado e a **saida do bocal**, e o corpo da turbina fica **a montante**, ou seja no
mesmo sentido do vetor de empuxo, nao no contrario. Um bocal de sustentacao empurra
para cima, o jato sai para baixo, e a turbina fica **acima** da saida.

    centro_do_cilindro = saida_do_bocal + (comprimento/2) * direcao_de_empuxo

Somar em vez de subtrair coloca as sete turbinas trezentos milimetros do lado errado,
o que inverte a distribuicao de massa inteira sem produzir erro nenhum de geometria.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

TURBINA_DIAMETRO_MM = 120.0
TURBINA_COMPRIMENTO_MM = 299.0
TURBINA_MASSA_KG = 2.20

CAIXA = (100.0, 200.0, 300.0)
CAIXA_MASSA_KG = 1.0

BOCAIS = (
    ("par0_esq", (320.0, -300.0, -150.0), (+0.2506, -0.2506, -0.9351)),
    ("par0_dir", (320.0, +300.0, -150.0), (+0.2506, +0.2506, -0.9351)),
    ("par1_esq", (200.0, -400.0, -260.0), (0.0000, -0.5000, -0.8660)),
    ("par1_dir", (200.0, +400.0, -260.0), (0.0000, +0.5000, -0.8660)),
    ("par2_esq", (20.0, -350.0, -370.0), (-0.2506, -0.6846, -0.6846)),
    ("par2_dir", (20.0, +350.0, -370.0), (-0.2506, +0.6846, -0.6846)),
    ("dorsal", (-150.0, 0.0, +100.0), (0.0000, 0.0000, -1.0000)),
)


def _rotacao_para(direcao, FreeCAD):
    """Rotacao que leva o eixo local +Z do cilindro ate ``direcao``.

    O eixo de rotacao e o produto vetorial dos dois, e o angulo e o arco cosseno do
    produto escalar. O caso degenerado, quando os dois ja sao paralelos ou opostos,
    precisa de tratamento proprio: o produto vetorial e nulo e nao define eixo.
    """
    z = FreeCAD.Vector(0.0, 0.0, 1.0)
    alvo = FreeCAD.Vector(*direcao).normalize()
    escalar = max(-1.0, min(1.0, z.dot(alvo)))

    if escalar > 1.0 - 1e-12:
        return FreeCAD.Rotation()
    if escalar < -1.0 + 1e-12:
        return FreeCAD.Rotation(FreeCAD.Vector(1.0, 0.0, 0.0), 180.0)

    eixo = z.cross(alvo)
    return FreeCAD.Rotation(eixo, math.degrees(math.acos(escalar)))


def constroi(destino: Path) -> None:
    import FreeCAD  # noqa: PLC0415

    destino.mkdir(parents=True, exist_ok=True)
    doc = FreeCAD.newDocument("referencia")

    # ---------------------------------------------------------- caixa de calibracao
    # Existe para conferir a cadeia inteira contra solucao analitica conhecida.
    caixa = doc.addObject("Part::Box", "caixa_de_calibracao")
    caixa.Length, caixa.Width, caixa.Height = CAIXA
    caixa.Placement.Base = FreeCAD.Vector(-1500.0, 0.0, 0.0)  # longe, para nao atrapalhar

    # ---------------------------------------------------------- os sete propulsores
    for nome, saida, direcao in BOCAIS:
        cil = doc.addObject("Part::Cylinder", f"turbina_{nome}")
        cil.Radius = TURBINA_DIAMETRO_MM / 2.0
        cil.Height = TURBINA_COMPRIMENTO_MM

        # ⚠ A base do cilindro fica NA SAIDA do bocal, e ele cresce no sentido do
        # empuxo, ou seja para montante. O corpo da turbina fica acima da saida num
        # bocal de sustentacao, porque o jato sai para baixo.
        cil.Placement = FreeCAD.Placement(
            FreeCAD.Vector(*saida),
            _rotacao_para(direcao, FreeCAD),
        )

    doc.recompute()
    caminho = destino / "referencia.FCStd"
    doc.saveAs(str(caminho))
    print(f"documento escrito: {caminho}")

    # ---------------------------------------------------------- arquivo de massas
    densidades = {"caixa_de_calibracao": {"mass_kg": CAIXA_MASSA_KG, "material": "ficticio"}}
    for nome, _, _ in BOCAIS:
        densidades[f"turbina_{nome}"] = {
            "mass_kg": TURBINA_MASSA_KG,
            "material": "Kingtech K-260G4",
        }
    caminho_dens = destino / "densidades.json"
    caminho_dens.write_text(json.dumps(densidades, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"densidades escritas: {caminho_dens}")

    # ---------------------------------------------------------- conferencia na tela
    print()
    print("CENTRO DE CADA CILINDRO, para conferir a mao:")
    for nome, saida, direcao in BOCAIS:
        meio = tuple(
            s + (TURBINA_COMPRIMENTO_MM / 2.0) * d for s, d in zip(saida, direcao, strict=True)
        )
        print(
            f"  {nome:10} saida {saida} -> centro ({meio[0]:7.1f}, {meio[1]:7.1f}, {meio[2]:7.1f})"
        )
    print()
    print("ATENCAO: Repare que o centro fica com z MAIS NEGATIVO que a saida nos bocais de")
    print("  sustentacao, ou seja ACIMA dela. O jato sai para baixo; a turbina fica em cima.")
    print()
    print("CAIXA DE CALIBRACAO, inercia esperada para 1 kg:")
    a, b, c = (v / 1000.0 for v in CAIXA)
    print(f"  I_xx = {(b**2 + c**2) / 12:.7f} kg m2")
    print(f"  I_yy = {(a**2 + c**2) / 12:.7f} kg m2")
    print(f"  I_zz = {(a**2 + b**2) / 12:.7f} kg m2")


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/decks/referencia")
    constroi(destino)
    print()
    print("Proximo passo, exportar o deck:")
    print(
        f'  "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_export.py '
        f"{destino}/referencia.FCStd {destino}/referencia.json "
        f"--z-para-baixo --densidades {destino}/densidades.json"
    )


if __name__ == "__main__":
    main()
