"""Portao de envelope: as turbinas cabem ao redor do corpo?

Roda no Python do FreeCAD::

    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_envelope_gate.py

Le o manequim em pose de pairado e o modelo de referencia das turbinas, e responde a
pergunta que a varredura de geometria nunca fez: onde esta o corpo.

Para cada turbina:

    folga real          menor distancia do cilindro real, 120 mm, ao corpo
    envelope invade     se o cilindro com folga, 180 mm, intersecta algum segmento,
                        e com que volume

E, entre turbinas, se os envelopes com folga se sobrepoem.

ATENCAO: o resultado sai em docs/resultados/portao-envelope.txt, mas este script NAO
entra na sessao 'resultados' do nox: ele roda no Python do FreeCAD, versao 3.11, e o
nox roda no do projeto, 3.12. Regenere a mao quando mudar o manequim ou as turbinas.

ATENCAO: nao verifica o cone do jato, so o volume da turbina e sua folga. Um jato que
nao encosta no corpo pode ainda assim atingir a perna ou o bocal de baixo.

ATENCAO: o manequim e feito de solidos primitivos. Um tronco em caixa tem as costas
planas; costas reais sao curvas. A folga medida aqui e aproximada, e um resultado de
contato direto, como folga zero, nao depende desse detalhe.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

RAIO_REAL_MM = 60.0
FOLGA_MM = 30.0
COMPRIMENTO_MM = 299.0
LIMIAR_VOLUME_MM3 = 1.0

MANEQUIM = "docs/decks/manequim/manequim_pairado.FCStd"
TURBINAS = "docs/decks/referencia/referencia.FCStd"
SAIDA = "docs/resultados/portao-envelope.txt"


def main() -> int:
    import FreeCAD as App  # noqa: PLC0415
    import Part  # noqa: PLC0415

    linhas: list[str] = []

    def diga(texto: str = "") -> None:
        linhas.append(texto)
        print(texto)

    m = App.openDocument(MANEQUIM)
    r = App.openDocument(TURBINAS)
    segmentos = [o for o in m.Objects if getattr(o, "Shape", None) is not None and o.Shape.Solids]
    turbinas = [o for o in r.Objects if o.Name.startswith("turbina_")]
    raio_envelope = RAIO_REAL_MM + FOLGA_MM

    def envelope(obj):
        eixo = obj.Placement.Rotation.multVec(App.Vector(0, 0, 1))
        return Part.makeCylinder(raio_envelope, COMPRIMENTO_MM, obj.Placement.Base, eixo)

    diga("PORTAO DE ENVELOPE: turbinas contra o corpo em pose de pairado")
    diga(f"manequim: {MANEQUIM}")
    diga(f"turbinas: {TURBINAS}")
    diga(f"envelope com folga: diametro {2 * raio_envelope:.0f} mm")
    diga()
    diga(f"{'turbina':20} {'folga real':>11}  {'segmento mais proximo':22}  envelope invade")
    diga("-" * 86)

    reprovadas = []
    for t in turbinas:
        env = envelope(t)
        menor, perto = float("inf"), "?"
        invasoes = []
        for s in segmentos:
            distancia = t.Shape.distToShape(s.Shape)[0]
            if distancia < menor:
                menor, perto = distancia, s.Name
            volume = env.common(s.Shape).Volume
            if volume > LIMIAR_VOLUME_MM3:
                invasoes.append(f"{s.Name} {volume / 1000:.0f} cm3")
        texto = ", ".join(invasoes) if invasoes else "nao"
        if menor < 1e-6 or invasoes:
            reprovadas.append(t.Name)
        diga(f"{t.Name:20} {menor:8.0f} mm  {perto:22}  {texto}")

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
    diga("ATENCAO: corpo em solidos primitivos; folga zero nao depende desse detalhe.")

    cabecalho = [
        "# GERADO por tools/freecad_envelope_gate.py, no Python do FreeCAD.",
        "# NAO entra na sessao 'resultados' do nox: regenere a mao.",
        f"# gerado em {_dt.datetime.now().isoformat(timespec='seconds')}",
        "#",
    ]
    Path(SAIDA).parent.mkdir(parents=True, exist_ok=True)
    Path(SAIDA).write_text("\n".join(cabecalho + linhas) + "\n", encoding="utf-8")
    return 1 if reprovadas else 0


if __name__ == "__main__":
    sys.exit(main())
