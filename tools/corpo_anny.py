"""Corpo humano realista para o portao de envelope, gerado pelo modelo Anny.

Roda num ambiente SEPARADO, porque o Anny precisa de PyTorch e o nucleo nao pode::

    py -3.12 -m venv .venv-corpo
    ./.venv-corpo/Scripts/python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
    ./.venv-corpo/Scripts/python.exe -m pip install "anny[examples]@git+https://github.com/naver/anny.git"
    ./.venv-corpo/Scripts/python.exe tools/corpo_anny.py docs/decks/corpo

A primeira execucao demora cerca de dois minutos: o Anny processa os arquivos do
MakeHuman e guarda em cache.

O QUE E O ANNY

    Modelo parametrico de corpo humano da NAVER Labs, 2025, construido sobre a malha do
    MakeHuman. Codigo Apache 2.0, malha CC0. Artigo: arXiv 2511.03589.
    Tem esqueleto de 104 ossos, entao a pose do braco e aplicada no proprio esqueleto,
    com a pele deformando junto, e nao por cilindros soltos.

O QUE ESTE SCRIPT FAZ

    1. Calibra os parametros de altura e composicao do Anny ate a estatura do manequim
       de primitivos, 1750 mm, e a massa mais proxima de 80 kg que o Anny alcanca.
       Hoje sao 78,7 kg: o Anny satura antes. O script avisa em vez de falhar.
    2. Posa os bracos nas MESMAS duas poses de tools/freecad_mannequin.py.
    3. Converte para o referencial do projeto: x frente, y direita, z para BAIXO, mm,
       origem no plexo solar a 1250 mm do chao, ombros em x = 0.
    4. Salva STL, imagem de frente e de lado, e um JSON com medidas e conferencias.

O QUE E ASSUMIDO

    idade        parametro 0,5 do MakeHuman, que la corresponde a 25 anos.
    composicao   peso e musculo sobem JUNTOS, um parametro so. Com musculo no padrao
                 o Anny satura em cerca de 63 kg a 1,75 m, abaixo dos 80 kg pedidos.
                 Proporcoes 0,5, o padrao.
    massa        o Anny estima massa por VOLUME vezes 980 kg/m3, constante no codigo
                 dele, anny/anthropometry.py. Densidade uniforme.
    torcao       a pose gira cada segmento pelo menor angulo ate a direcao pedida. A
                 torcao do antebraco, e portanto a direcao da palma, nao e controlada.

ATENCAO: os parametros do Anny sao, nas palavras dos autores, baseados em
preconceitos de artistas do MakeHuman sobre tracos humanos. A malha e realista na
FORMA, nao e medicao de uma populacao.

ATENCAO: serve para o portao de envelope, a pergunta de se as turbinas cabem. As
propriedades de massa impressas aqui usam densidade UNIFORME e existem so para
CONFERIR o manequim de segmentos, nao para substitui-lo.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import anny
import anny.anthropometry
import numpy as np
import torch
import trimesh

ESTATURA_M = 1.750
MASSA_KG = 80.0
GENERO = 0.0
"""0 e masculino NO ANNY. Conferido por sondagem: 0 sai mais alto e mais pesado.
O tutorial do Anny chama gender 1 de mulher; o MakeHuman original usa o oposto."""
IDADE = 0.5
ALTURA_ORIGEM_MM = 1250.0

POSES = {
    "anatomica": {"ombro_flexao": 0.0, "ombro_abducao": 4.0, "cotovelo_flexao": 0.0},
    "pairado": {"ombro_flexao": 55.0, "ombro_abducao": 20.0, "cotovelo_flexao": 35.0},
}

# Anny: x para a esquerda do sujeito, y para tras, z para cima, metros.
# Projeto: x para frente, y para a direita, z para baixo. Rotacao propria, det = +1.
ANNY_PARA_PROJETO = np.array([[0.0, -1.0, 0.0], [-1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])

TOLERANCIA_POSE_GRAUS = 2.0


def _rot_y(v, graus):
    a = math.radians(graus)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


def _rot_x(v, graus):
    a = math.radians(graus)
    x, y, z = v
    return (x, y * math.cos(a) - z * math.sin(a), y * math.sin(a) + z * math.cos(a))


def direcoes_alvo_projeto(lado: float, pose: dict) -> tuple[np.ndarray, np.ndarray]:
    """Mesma cinematica de tools/freecad_mannequin.py. lado -1 esquerda, +1 direita."""
    baixo = (0.0, 0.0, 1.0)
    braco = _rot_x(_rot_y(baixo, pose["ombro_flexao"]), -lado * pose["ombro_abducao"])
    antebraco = _rot_x(
        _rot_y(baixo, pose["ombro_flexao"] + pose["cotovelo_flexao"]),
        -lado * pose["ombro_abducao"],
    )
    return np.array(braco), np.array(antebraco)


def _rotacao_minima(de: np.ndarray, para: np.ndarray) -> np.ndarray:
    a = de / np.linalg.norm(de)
    b = para / np.linalg.norm(para)
    eixo = np.cross(a, b)
    s, c = np.linalg.norm(eixo), float(np.dot(a, b))
    if s < 1e-12:
        return np.eye(3)
    k = eixo / s
    kx = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + s * kx + (1.0 - c) * kx @ kx


class Corpo:
    def __init__(self) -> None:
        self.modelo = anny.Anny().to(dtype=torch.float32)
        self.medidor = anny.anthropometry.Anthropometry(self.modelo)
        self.fenotipo = {k: 0.5 for k in self.modelo.phenotype_labels}
        self.fenotipo["gender"] = GENERO
        self.fenotipo["age"] = IDADE
        self.id = self.modelo.bone_labels.index

    def medidas(self) -> dict[str, float]:
        saida = self.modelo(phenotype_kwargs=self.fenotipo)
        bruto = self.medidor(saida["rest_vertices"])
        return {k: float(v.reshape(-1)[0]) for k, v in bruto.items()}

    def calibra(self) -> dict[str, float]:
        """Ajusta altura e peso, alternando bissecoes, ate estatura e massa baterem."""

        def bissecao(chave: str, medida: str, alvo: float) -> None:
            baixo, alto = 0.0, 1.0
            for _ in range(22):
                self.fenotipo[chave] = 0.5 * (baixo + alto)
                if self.medidas()[medida] < alvo:
                    baixo = self.fenotipo[chave]
                else:
                    alto = self.fenotipo[chave]

        def composicao(u: float) -> None:
            self.fenotipo["weight"] = u
            self.fenotipo["muscle"] = u

        def bissecao_composicao() -> None:
            baixo, alto = 0.5, 1.0
            for _ in range(22):
                composicao(0.5 * (baixo + alto))
                if self.medidas()["mass"] < MASSA_KG:
                    baixo = self.fenotipo["weight"]
                else:
                    alto = self.fenotipo["weight"]

        for _ in range(4):
            bissecao("height", "height", ESTATURA_M)
            bissecao_composicao()
        final = self.medidas()
        if abs(final["height"] - ESTATURA_M) > 0.002:
            raise RuntimeError(f"calibracao de estatura nao convergiu: {final}")
        if abs(final["mass"] - MASSA_KG) > 0.2:
            print(f"  ATENCAO: massa maxima alcancavel {final['mass']:.2f} kg, alvo {MASSA_KG} kg")
        return final

    def posado(self, pose: dict) -> tuple[np.ndarray, dict[str, float]]:
        """Vertices em metros, referencial do Anny, e o erro angular de cada segmento."""
        m = self.modelo
        repouso = m(phenotype_kwargs=self.fenotipo, pose_parameterization="local-bone")
        cabecas = repouso["bone_poses"][0, :, :3, 3].numpy().astype(float)
        parametros = m.get_pose_parameterization(repouso, pose_parameterization="world-orient")

        erros = {}
        alvos = {}
        for sufixo, lado in (("L", -1.0), ("R", +1.0)):
            ombro, cotovelo, punho = (
                self.id(f"upperarm01.{sufixo}"),
                self.id(f"lowerarm01.{sufixo}"),
                self.id(f"wrist.{sufixo}"),
            )
            braco_p, antebraco_p = direcoes_alvo_projeto(lado, pose)
            braco_a = ANNY_PARA_PROJETO.T @ braco_p
            antebraco_a = ANNY_PARA_PROJETO.T @ antebraco_p
            r_braco = _rotacao_minima(cabecas[cotovelo] - cabecas[ombro], braco_a)
            r_antebraco = _rotacao_minima(cabecas[punho] - cabecas[cotovelo], antebraco_a)
            alvos[sufixo] = (ombro, cotovelo, punho, braco_a, antebraco_a)

            antebraco_e_mao = [
                i
                for i, nome in enumerate(m.bone_labels)
                if nome.endswith(f".{sufixo}")
                and nome.startswith(("lowerarm", "wrist", "finger", "metacarpal"))
            ]
            for i, rot in [(self.id(f"upperarm0{n}.{sufixo}"), r_braco) for n in (1, 2)] + [
                (i, r_antebraco) for i in antebraco_e_mao
            ]:
                atual = parametros[0, i, :3, :3].numpy().astype(float)
                parametros[0, i, :3, :3] = torch.as_tensor(rot @ atual, dtype=parametros.dtype)

        saida = m(
            pose_parameters=parametros,
            phenotype_kwargs=self.fenotipo,
            pose_parameterization="world-orient",
        )
        novas = saida["bone_poses"][0, :, :3, 3].numpy().astype(float)
        for sufixo, (ombro, cotovelo, punho, braco_a, antebraco_a) in alvos.items():
            for nome, a, b, alvo in (
                ("braco", ombro, cotovelo, braco_a),
                ("antebraco", cotovelo, punho, antebraco_a),
            ):
                d = novas[b] - novas[a]
                cos = np.dot(d, alvo) / (np.linalg.norm(d) * np.linalg.norm(alvo))
                erros[f"{nome}_{sufixo}"] = math.degrees(math.acos(min(1.0, max(-1.0, cos))))
        return saida["vertices"][0].numpy().astype(float), erros

    def ombros_repouso_m(self) -> np.ndarray:
        saida = self.modelo(phenotype_kwargs=self.fenotipo, pose_parameterization="local-bone")
        cabecas = saida["bone_poses"][0, :, :3, 3].numpy().astype(float)
        return np.array([cabecas[self.id("upperarm01.L")], cabecas[self.id("upperarm01.R")]])


def _imagem(malha_mm: trimesh.Trimesh, caminho: Path, titulo: str) -> None:
    import matplotlib  # noqa: PLC0415

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # noqa: PLC0415
    from matplotlib.collections import PolyCollection  # noqa: PLC0415

    v = malha_mm.vertices
    f = malha_mm.faces
    normais = malha_mm.face_normals
    figura, eixos = plt.subplots(1, 2, figsize=(9, 8))
    # frente: olhando de +x para tras; lado: olhando da direita, +y
    for eixo, (h, profundidade, rotulo) in zip(
        eixos,
        ((1, 0, "frente (y para a direita)"), (0, 1, "lado direito (x para frente)")),
        strict=True,
    ):
        luz = normais[:, profundidade] if profundidade == 0 else -normais[:, 1]
        visiveis = luz > 0
        ordem = np.argsort(v[f[visiveis]][:, :, profundidade].mean(axis=1))
        if profundidade == 1:
            ordem = ordem[::-1]
        tri = v[f[visiveis]][ordem]
        poligonos = np.stack([tri[:, :, h], -tri[:, :, 2]], axis=-1)
        tons = 0.25 + 0.7 * luz[visiveis][ordem]
        cores = np.stack([tons * 0.80, tons * 0.82, tons * 0.88, np.ones_like(tons)], axis=1)
        eixo.add_collection(PolyCollection(poligonos, facecolors=cores, edgecolors="none"))
        eixo.autoscale()
        eixo.set_aspect("equal")
        eixo.axhline(-ALTURA_ORIGEM_MM, color="0.6", lw=0.8)
        eixo.axhline(0.0, color="tab:red", lw=0.6, ls="--")
        eixo.set_title(rotulo, fontsize=10)
        eixo.set_xlabel("mm")
    eixos[0].set_ylabel("-z do projeto, mm (tracejado: origem; cinza: chao)")
    figura.suptitle(titulo, fontsize=11)
    figura.tight_layout()
    figura.savefig(caminho, dpi=110)
    plt.close(figura)


def main() -> int:
    destino = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/decks/corpo")
    destino.mkdir(parents=True, exist_ok=True)

    corpo = Corpo()
    print("calibrando estatura e massa...")
    medidas = corpo.calibra()
    print(f"  altura {medidas['height'] * 1000:.1f} mm, massa {medidas['mass']:.2f} kg")
    fen = corpo.fenotipo
    print(f"  parametros: height {fen['height']:.4f}, weight = muscle {fen['weight']:.4f}")
    densidade = medidas["mass"] / medidas["volume"]

    ombros = corpo.ombros_repouso_m() @ ANNY_PARA_PROJETO.T * 1000.0
    relatorio = {
        "gerado_por": "tools/corpo_anny.py",
        "modelo": "Anny, NAVER Labs, rig 'anny', topologia 'anny'. arXiv 2511.03589",
        "licenca": "codigo Apache 2.0; malha MakeHuman/MPFB2 CC0 1.0",
        "anny_versao": getattr(anny, "__version__", "desconhecida"),
        "referencial": "projeto: x frente, y direita, z para baixo, mm",
        "alinhamento": "sola no chao z = +1250 mm; ombros (upperarm01) centrados em x = 0, y = 0",
        "fenotipo": {k: round(float(v), 6) for k, v in corpo.fenotipo.items()},
        "medidas_anny": {k: round(v, 6) for k, v in medidas.items()},
        "densidade_uniforme_kg_m3": round(densidade, 2),
        "poses": {},
    }

    translacao = None
    for nome, pose in POSES.items():
        vertices_a, erros = corpo.posado(pose)
        pior = max(erros.values())
        if pior > TOLERANCIA_POSE_GRAUS:
            raise RuntimeError(f"pose {nome}: erro de {pior:.2f} graus, {erros}")
        vertices = vertices_a @ ANNY_PARA_PROJETO.T * 1000.0
        if translacao is None:
            translacao = np.array(
                [
                    -ombros[:, 0].mean(),
                    -ombros[:, 1].mean(),
                    ALTURA_ORIGEM_MM - vertices[:, 2].max(),
                ]
            )
        vertices = vertices + translacao
        malha = trimesh.Trimesh(vertices=vertices, faces=corpo.modelo.faces.numpy(), process=False)

        malha_m = trimesh.Trimesh(vertices=vertices / 1000.0, faces=malha.faces, process=False)
        malha_m.density = densidade
        estanque = bool(malha_m.is_watertight)
        tensor = malha_m.moment_inertia
        centro = malha_m.center_mass * 1000.0

        stl = destino / f"corpo_{nome}.stl"
        malha.export(stl)
        _imagem(
            malha,
            destino / f"corpo_{nome}.png",
            f"Anny calibrado, {medidas['height'] * 1000:.0f} mm, "
            f"{medidas['mass']:.1f} kg, pose {nome}",
        )

        relatorio["poses"][nome] = {
            "angulos_graus": pose,
            "erro_angular_segmentos_graus": {k: round(v, 3) for k, v in erros.items()},
            "stl": stl.as_posix(),
            "vertices": int(len(malha.vertices)),
            "triangulos": int(len(malha.faces)),
            "malha_fechada": estanque,
            "limites_mm": {
                "min": [round(x, 1) for x in vertices.min(axis=0)],
                "max": [round(x, 1) for x in vertices.max(axis=0)],
            },
            "densidade_uniforme": {
                "massa_kg": round(float(malha_m.mass), 3),
                "centro_mm": [round(float(x), 1) for x in centro],
                "inercia_no_centro_kg_m2": [
                    [round(float(x), 4) for x in linha] for linha in tensor
                ],
            },
        }
        print(
            f"  {nome:10} fechada={estanque}  massa {malha_m.mass:.2f} kg  "
            f"centro ({centro[0]:+.1f}, {centro[1]:+.1f}, {centro[2]:+.1f}) mm  "
            f"Ixx {tensor[0, 0]:.2f} Iyy {tensor[1, 1]:.2f} Izz {tensor[2, 2]:.2f} "
            f"Ixz {tensor[0, 2]:+.2f}"
            f"  pior erro de pose {pior:.2f} graus"
        )

    ombros_final = ombros + translacao
    relatorio["ombros_mm"] = {
        "esquerdo": [round(float(x), 1) for x in ombros_final[0]],
        "direito": [round(float(x), 1) for x in ombros_final[1]],
        "manequim_de_primitivos": "(0, -/+200, -181.5)",
    }
    (destino / "corpo.json").write_text(
        json.dumps(relatorio, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    ombros_mm = relatorio["ombros_mm"]
    print(f"ombros: esquerdo {ombros_mm['esquerdo']}, direito {ombros_mm['direito']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
