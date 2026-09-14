"""Manequim articulado do piloto, em duas poses, com massa por segmento.

Roda no Python do FreeCAD::

    "C:/Program Files/FreeCAD 1.1/bin/python.exe" tools/freecad_mannequin.py docs/decks/manequim

Produz, para cada pose, um ``.FCStd``, um ``massas.json`` e um deck ``.json`` no
formato de ``hero_atlas.airframe.cad_deck``.

POR QUE DUAS POSES

    ``anatomica``  em pe, bracos junto ao corpo. Existe so para VALIDAR: e a postura
                   comparavel as medicoes publicadas de inercia do corpo inteiro.
    ``pairado``    bracos a frente, como quem segura guidao. E a pose do projeto.

    Validar direto na pose de pairado nao valeria nada: nao ha medicao publicada de
    inercia com os bracos nessa posicao.

O QUE E MEDIDO, O QUE E ASSUMIDO

    medido      nada. Este e um modelo, nao uma medicao.
    confirmado  a regressao de inercia do corpo inteiro de Matsuo et al. (1995),
                usada so para CONFERIR, com as ressalvas abaixo.
    assumido    tudo o resto: proporcoes, diametros, frações de massa, densidade.

ATENCAO, FRACOES DE MASSA. Os valores abaixo sao os atribuidos a de Leva (1996) para
homens. Eles somam 100 por cento, mas NAO foram conferidos em documento legivel: o PDF
original disponivel e imagem escaneada e todas as copias em texto recusaram conexao.
Estao marcados como nao verificados, e a validacao e feita no corpo inteiro por outra
fonte, independente desta tabela.

ATENCAO, DENSIDADE. Cada segmento e um solido primitivo de densidade uniforme. Tecido
humano nao e uniforme: osso, musculo e gordura diferem. O centro e a inercia de cada
segmento saem da GEOMETRIA do primitivo, nao da anatomia. Um estudo aberto comparou as
previsoes por tabela com densitometria em pessoas reais e achou erro de ate 60 por
cento por individuo. Este manequim nao e melhor que isso.

PARA UM CORPO VISUALMENTE REALISTA

    MakeHuman gera malha humana parametrica e exporta em STL e OBJ sob licenca CC0.
    Serve para o PORTAO DE ENVELOPE, a pergunta de se os propulsores cabem. Nao serve
    para massa: malha nao tem distribuicao de densidade, e costuma nao ser solido
    fechado, entao o FreeCAD nem calcula volume.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import sys
from pathlib import Path

ESTATURA_MM = 1750.0
MASSA_TOTAL_KG = 80.0
ALTURA_ORIGEM_MM = 1250.0
"""Plexo solar acima do chao. Convencao do guia de modelagem, declarada."""

# ---------------------------------------------------------------------------
# Fracoes de massa, de Leva (1996), homens. NAO VERIFICADAS em fonte legivel.
# ---------------------------------------------------------------------------
FRACAO_MASSA = {
    "cabeca_pescoco": 0.0694,
    "tronco": 0.4346,
    "braco": 0.0271,
    "antebraco": 0.0162,
    "mao": 0.0061,
    "coxa": 0.1416,
    "perna": 0.0433,
    "pe": 0.0137,
}

# ---------------------------------------------------------------------------
# Proporcoes, fracao da estatura. Ordem de grandeza, NAO verificadas.
# ---------------------------------------------------------------------------
PROPORCAO = {
    "altura_ombro": 0.818,
    "altura_quadril": 0.530,
    "comprimento_braco": 0.186,
    "comprimento_antebraco": 0.146,
    "comprimento_mao": 0.108,
    "comprimento_coxa": 0.245,
    "comprimento_perna": 0.246,
    "comprimento_pe": 0.152,
}

DIAMETRO_MM = {
    "cabeca_pescoco": 180.0,
    "braco": 100.0,
    "antebraco": 85.0,
    "mao": 70.0,
    "coxa": 150.0,
    "perna": 110.0,
}

TRONCO_LARGURA_MM = 400.0
TRONCO_PROFUNDIDADE_MM = 240.0
MEIA_LARGURA_OMBRO_MM = 200.0
MEIA_LARGURA_QUADRIL_MM = 90.0
PE_LARGURA_MM = 100.0
PE_ALTURA_MM = 68.0

POSES = {
    # flexao do ombro para frente, abducao para fora, flexao do cotovelo, em graus
    "anatomica": {"ombro_flexao": 0.0, "ombro_abducao": 4.0, "cotovelo_flexao": 0.0},
    "pairado": {"ombro_flexao": 55.0, "ombro_abducao": 20.0, "cotovelo_flexao": 35.0},
}


def z_do_chao(altura_acima_do_chao_mm: float) -> float:
    """Converte altura acima do chao para z do projeto, que aponta para BAIXO."""
    return ALTURA_ORIGEM_MM - altura_acima_do_chao_mm


def _rot_y(v, graus):
    """Rotacao em torno de y. Positivo leva +z para +x: pende para frente."""
    a = math.radians(graus)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def _rot_x(v, graus):
    """Rotacao em torno de x."""
    a = math.radians(graus)
    x, y, z = v
    return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))


def _soma(a, b, escala=1.0):
    return tuple(p + escala * q for p, q in zip(a, b, strict=True))


def _cadeia_do_braco(lado: float, pose: dict) -> list[tuple[str, tuple, tuple, float]]:
    """Cinematica direta do braco: ombro, cotovelo, punho, ponta da mao.

    ``lado`` e -1 para esquerda e +1 para direita. Com braco pendente, a direcao de
    cada segmento e +z, para baixo. A flexao do ombro gira para frente, a abducao
    abre para o lado, e a flexao do cotovelo dobra o antebraco para frente.
    """
    ombro = (0.0, lado * MEIA_LARGURA_OMBRO_MM, z_do_chao(PROPORCAO["altura_ombro"] * ESTATURA_MM))

    baixo = (0.0, 0.0, 1.0)
    d_braco = _rot_y(baixo, pose["ombro_flexao"])
    d_braco = _rot_x(d_braco, -lado * pose["ombro_abducao"])

    d_antebraco = _rot_y(baixo, pose["ombro_flexao"] + pose["cotovelo_flexao"])
    d_antebraco = _rot_x(d_antebraco, -lado * pose["ombro_abducao"])

    l_braco = PROPORCAO["comprimento_braco"] * ESTATURA_MM
    l_antebraco = PROPORCAO["comprimento_antebraco"] * ESTATURA_MM
    l_mao = PROPORCAO["comprimento_mao"] * ESTATURA_MM

    cotovelo = _soma(ombro, d_braco, l_braco)
    punho = _soma(cotovelo, d_antebraco, l_antebraco)
    return [
        ("braco", ombro, d_braco, l_braco),
        ("antebraco", cotovelo, d_antebraco, l_antebraco),
        ("mao", punho, d_antebraco, l_mao),
    ]


def _rotacao_para(direcao, App):
    z = App.Vector(0.0, 0.0, 1.0)
    alvo = App.Vector(*direcao).normalize()
    escalar = max(-1.0, min(1.0, z.dot(alvo)))
    if escalar > 1.0 - 1e-12:
        return App.Rotation()
    if escalar < -1.0 + 1e-12:
        return App.Rotation(App.Vector(1.0, 0.0, 0.0), 180.0)
    return App.Rotation(z.cross(alvo), math.degrees(math.acos(escalar)))


def constroi(nome_pose: str, destino: Path) -> dict:
    import FreeCAD as App  # noqa: PLC0415

    pose = POSES[nome_pose]
    doc = App.newDocument(f"manequim_{nome_pose}")
    massas: dict[str, dict] = {}

    def cilindro(nome, base, direcao, comprimento, diametro, fracao):
        c = doc.addObject("Part::Cylinder", nome)
        c.Radius = diametro / 2.0
        c.Height = comprimento
        c.Placement = App.Placement(App.Vector(*base), _rotacao_para(direcao, App))
        massas[nome] = {
            "mass_kg": round(fracao * MASSA_TOTAL_KG, 6),
            "material": "segmento humano, densidade uniforme ASSUMIDA",
        }

    z_topo = z_do_chao(ESTATURA_MM)
    z_ombro = z_do_chao(PROPORCAO["altura_ombro"] * ESTATURA_MM)
    z_quadril = z_do_chao(PROPORCAO["altura_quadril"] * ESTATURA_MM)
    z_chao = z_do_chao(0.0)

    # cabeca e pescoco: do vertice ate a linha do ombro
    cilindro(
        "cabeca_pescoco",
        (0.0, 0.0, z_topo),
        (0.0, 0.0, 1.0),
        z_ombro - z_topo,
        DIAMETRO_MM["cabeca_pescoco"],
        FRACAO_MASSA["cabeca_pescoco"],
    )

    # tronco: caixa do ombro ao quadril
    tronco = doc.addObject("Part::Box", "tronco")
    tronco.Length = TRONCO_PROFUNDIDADE_MM
    tronco.Width = TRONCO_LARGURA_MM
    tronco.Height = z_quadril - z_ombro
    tronco.Placement.Base = App.Vector(
        -TRONCO_PROFUNDIDADE_MM / 2.0, -TRONCO_LARGURA_MM / 2.0, z_ombro
    )
    massas["tronco"] = {
        "mass_kg": round(FRACAO_MASSA["tronco"] * MASSA_TOTAL_KG, 6),
        "material": "segmento humano, densidade uniforme ASSUMIDA",
    }

    # bracos, por cinematica direta
    for lado, sufixo in ((-1.0, "esq"), (+1.0, "dir")):
        for seg, base, direcao, comp in _cadeia_do_braco(lado, pose):
            cilindro(f"{seg}_{sufixo}", base, direcao, comp, DIAMETRO_MM[seg], FRACAO_MASSA[seg])

    # pernas, retas
    for lado, sufixo in ((-1.0, "esq"), (+1.0, "dir")):
        y = lado * MEIA_LARGURA_QUADRIL_MM
        l_coxa = PROPORCAO["comprimento_coxa"] * ESTATURA_MM
        l_perna = PROPORCAO["comprimento_perna"] * ESTATURA_MM
        cilindro(
            f"coxa_{sufixo}",
            (0.0, y, z_quadril),
            (0.0, 0.0, 1.0),
            l_coxa,
            DIAMETRO_MM["coxa"],
            FRACAO_MASSA["coxa"],
        )
        cilindro(
            f"perna_{sufixo}",
            (0.0, y, z_quadril + l_coxa),
            (0.0, 0.0, 1.0),
            l_perna,
            DIAMETRO_MM["perna"],
            FRACAO_MASSA["perna"],
        )
        pe = doc.addObject("Part::Box", f"pe_{sufixo}")
        pe.Length = PROPORCAO["comprimento_pe"] * ESTATURA_MM
        pe.Width = PE_LARGURA_MM
        pe.Height = PE_ALTURA_MM
        pe.Placement.Base = App.Vector(-60.0, y - PE_LARGURA_MM / 2.0, z_chao - PE_ALTURA_MM)
        massas[f"pe_{sufixo}"] = {
            "mass_kg": round(FRACAO_MASSA["pe"] * MASSA_TOTAL_KG, 6),
            "material": "segmento humano, densidade uniforme ASSUMIDA",
        }

    doc.recompute()

    destino.mkdir(parents=True, exist_ok=True)
    fcstd = destino / f"manequim_{nome_pose}.FCStd"
    doc.saveAs(str(fcstd))

    componentes = []
    for obj in doc.Objects:
        forma = getattr(obj, "Shape", None)
        if forma is None or not forma.Solids:
            continue
        m = forma.MatrixOfInertia
        componentes.append(
            {
                "name": obj.Name,
                "mass_kg": massas[obj.Name]["mass_kg"],
                "material": massas[obj.Name]["material"],
                "volume_mm3": float(forma.Volume),
                "center_of_mass_mm": [float(c) for c in tuple(forma.CenterOfMass)],
                "inertia_matrix": [
                    [m.A11, m.A12, m.A13],
                    [m.A21, m.A22, m.A23],
                    [m.A31, m.A32, m.A33],
                ],
                "orientation": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            }
        )

    deck = {
        "schema_version": 1,
        "source_document": fcstd.name,
        "exported_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "z_axis_down": True,
        "components": componentes,
    }
    (destino / f"manequim_{nome_pose}.json").write_text(
        json.dumps(deck, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (destino / f"massas_{nome_pose}.json").write_text(
        json.dumps(massas, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    total = sum(c["mass_kg"] for c in componentes)
    print(f"pose {nome_pose}: {len(componentes)} segmentos, {total:.3f} kg -> {fcstd}")
    return {"pose": nome_pose, "segmentos": len(componentes), "massa_kg": total}


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/decks/manequim")
    soma = sum(FRACAO_MASSA.values()) + (
        FRACAO_MASSA["braco"]
        + FRACAO_MASSA["antebraco"]
        + FRACAO_MASSA["mao"]
        + FRACAO_MASSA["coxa"]
        + FRACAO_MASSA["perna"]
        + FRACAO_MASSA["pe"]
    )
    print(f"soma das fracoes, contando os dois lados: {soma:.4f}")
    if abs(soma - 1.0) > 1e-3:
        raise SystemExit("ATENCAO: fracoes de massa nao somam 1. Recusando construir.")
    for nome in POSES:
        constroi(nome, destino)


if __name__ == "__main__":
    main()
