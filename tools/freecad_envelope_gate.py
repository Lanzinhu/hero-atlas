"""Portao de envelope: as turbinas cabem ao redor do corpo?

Roda no Python do FreeCAD::

    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_envelope_gate.py
    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_envelope_gate.py \
        docs/decks/corpo/corpo_pairado.stl

Sem argumento, o corpo e o manequim de primitivos em pose de pairado. Com um STL, o
corpo e essa malha, por exemplo a gerada por tools/corpo_anny.py, e o resultado vai
para um arquivo separado.

Para cada turbina:

    folga real          menor distancia do cilindro real, 120 mm, ao corpo
    envelope invade     se o cilindro com folga, 180 mm, intersecta o corpo, e com que volume

E, entre turbinas, se os envelopes com folga se sobrepoem.

ATENCAO: o resultado sai em docs/resultados/, mas este script NAO entra na sessao
'resultados' do nox: ele roda no Python do FreeCAD, versao 3.11, e o nox roda no do
projeto, 3.12. Regenere a mao quando mudar o corpo ou as turbinas.

ATENCAO: nao verifica o cone do jato, so o volume da turbina e sua folga. Um jato que
nao encosta no corpo pode ainda assim atingir a perna ou o bocal de baixo.

ATENCAO, CORPO EM PRIMITIVOS: um tronco em caixa tem as costas planas; costas reais sao
curvas. Contato direto, como folga zero, nao depende desse detalhe.

ATENCAO, CORPO EM MALHA: a malha e convertida em solido de faces planas. A distancia e o
volume sao exatos PARA A MALHA, que e um modelo de forma, nao a pele de uma pessoa medida.
"""

from __future__ import annotations

import datetime as _dt
import sys
import time
from pathlib import Path

RAIO_REAL_MM = 60.0
FOLGA_MM = 30.0
COMPRIMENTO_MM = 299.0
LIMIAR_VOLUME_MM3 = 1.0

MANEQUIM = "docs/decks/manequim/manequim_pairado.FCStd"
TURBINAS = "docs/decks/referencia/referencia.FCStd"
SAIDA_PRIMITIVOS = "docs/resultados/portao-envelope.txt"
SAIDA_MALHA = "docs/resultados/portao-envelope-corpo-realista.txt"


def _corpo_de_malha(caminho: str):
    import Mesh  # noqa: PLC0415
    import Part  # noqa: PLC0415

    malha = Mesh.Mesh(caminho)
    if not malha.isSolid():
        raise RuntimeError(f"{caminho}: a malha nao e fechada, nao da para medir volume")
    forma = Part.Shape()
    forma.makeShapeFromMesh(malha.Topology, 0.05)
    solido = Part.makeSolid(forma)
    if solido.Volume < 0:
        solido.reverse()
    return malha, solido


def main() -> int:
    import FreeCAD as App  # noqa: PLC0415
    import Part  # noqa: PLC0415

    stl = sys.argv[1] if len(sys.argv) > 1 else None
    saida = SAIDA_MALHA if stl else SAIDA_PRIMITIVOS
    linhas: list[str] = []

    def diga(texto: str = "") -> None:
        linhas.append(texto)
        print(texto, flush=True)

    r = App.openDocument(TURBINAS)
    turbinas = [o for o in r.Objects if o.Name.startswith("turbina_")]
    malha = None
    if stl:
        inicio = time.time()
        malha, solido = _corpo_de_malha(stl)
        segmentos = [("corpo", solido)]
        origem = f"malha {stl}, {malha.CountFacets} triangulos, {solido.Volume / 1e6:.2f} litros"
        print(f"(malha convertida em solido em {time.time() - inicio:.0f} s)", flush=True)
    else:
        m = App.openDocument(MANEQUIM)
        segmentos = [
            (o.Name, o.Shape)
            for o in m.Objects
            if getattr(o, "Shape", None) is not None and o.Shape.Solids
        ]
        origem = f"manequim de primitivos {MANEQUIM}"
    raio_envelope = RAIO_REAL_MM + FOLGA_MM

    def envelope(obj):
        eixo = obj.Placement.Rotation.multVec(App.Vector(0, 0, 1))
        return Part.makeCylinder(raio_envelope, COMPRIMENTO_MM, obj.Placement.Base, eixo)

    diga("PORTAO DE ENVELOPE: turbinas contra o corpo em pose de pairado")
    diga(f"corpo: {origem}")
    diga(f"turbinas: {TURBINAS}")
    diga(f"envelope com folga: diametro {2 * raio_envelope:.0f} mm")
    diga()
    diga(f"{'turbina':20} {'folga real':>11}  {'mais proximo':30}  envelope invade")
    diga("-" * 96)

    reprovadas = []
    colisoes = []
    for t in turbinas:
        env = envelope(t)
        menor, perto = float("inf"), "?"
        invasoes = []
        for nome, forma in segmentos:
            distancia, pares, _ = t.Shape.distToShape(forma)
            if distancia < menor:
                menor = distancia
                if stl:
                    p = pares[0][1]
                    perto = f"corpo em ({p.x:+.0f}, {p.y:+.0f}, {p.z:+.0f})"
                else:
                    perto = nome
            comum = env.common(forma)
            if comum.Volume > LIMIAR_VOLUME_MM3:
                invasoes.append(f"{nome} {comum.Volume / 1000:.0f} cm3")
                colisoes.append((t.Name, comum))
        texto = ", ".join(invasoes) if invasoes else "nao"
        if menor < 1e-6 or invasoes:
            reprovadas.append(t.Name)
        diga(f"{t.Name:20} {menor:8.0f} mm  {perto:30}  {texto}")

    diga()
    diga("turbina contra turbina, envelopes com folga:")
    sobreposicoes = 0
    for i, a in enumerate(turbinas):
        ea = envelope(a)
        for b in turbinas[i + 1 :]:
            volume = ea.common(envelope(b)).Volume
            if volume > LIMIAR_VOLUME_MM3:
                sobreposicoes += 1
                diga(f"  {a.Name} x {b.Name}: {volume / 1000:.0f} cm3")
    if not sobreposicoes:
        diga("  nenhuma sobreposicao")

    diga()
    if reprovadas:
        diga(f"REPROVADO: {len(reprovadas)} de {len(turbinas)} turbinas com contato ou invasao")
        for nome in reprovadas:
            diga(f"  {nome}")
    else:
        diga(f"APROVADO: nenhuma das {len(turbinas)} turbinas encosta no corpo")
    diga()
    diga("ATENCAO: nao verifica o cone do jato, so o volume da turbina e sua folga.")
    if stl:
        diga("ATENCAO: corpo em malha de forma, parametrica; nao e a pele de uma pessoa medida.")
    else:
        diga("ATENCAO: corpo em solidos primitivos; folga zero nao depende desse detalhe.")

    cabecalho = [
        "# GERADO por tools/freecad_envelope_gate.py, no Python do FreeCAD.",
        "# NAO entra na sessao 'resultados' do nox: regenere a mao.",
        f"# gerado em {_dt.datetime.now().isoformat(timespec='seconds')}",
        "#",
    ]
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    Path(saida).write_text("\n".join(cabecalho + linhas) + "\n", encoding="utf-8")

    if stl:
        # Documento para abrir e OLHAR: malha translucida, turbinas, colisoes em amarelo.
        # Leve de proposito: guarda a malha, nao o solido de dezenas de milhares de faces.
        visual = App.newDocument("portao_corpo_realista")
        corpo = visual.addObject("Mesh::Feature", "corpo")
        corpo.Mesh = malha
        for t in turbinas:
            copia = visual.addObject("Part::Feature", t.Name)
            copia.Shape = t.Shape.copy()
        for nome, forma in colisoes:
            c = visual.addObject("Part::Feature", f"COLISAO_{nome}")
            c.Shape = forma
        visual.recompute()
        destino = Path(stl).with_name(Path(stl).stem + "_portao.FCStd")
        visual.saveAs(str(destino.resolve()))
        print(f"documento para visualizar: {destino.as_posix()}")
    return 1 if reprovadas else 0


if __name__ == "__main__":
    sys.exit(main())
