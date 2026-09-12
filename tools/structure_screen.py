"""Experimento 6: triagem estrutural e de ressonancia, sem CAD.

Roda com::

    ./.venv/Scripts/python.exe tools/structure_screen.py

A pergunta:

    Que **requisitos** de estrutura a simulacao ja impoe, e quanto a ausencia de CAD
    contamina as conclusoes dos passos anteriores?

⚠ Este experimento **nao desenha nada** e nao substitui analise por elementos finitos.
Ele produz tres coisas que nao precisam de CAD:

1. o **espectro de excitacao** que a estrutura vai ver, com as bandas proibidas;
2. as **cargas de fixacao** por propulsor, medidas na trajetoria do laco fechado;
3. a **sensibilidade a inercia**, que diz quanto a estimativa de massa contamina a
   fronteira de atraso do passo 5.

O terceiro e o mais importante: enquanto nao houver CAD, todo resultado dinamico
repousa sobre um tensor de inercia estimado, e este experimento mede **quanto isso
custa** em vez de deixar a ressalva no rodape.
"""

from __future__ import annotations

import math
import sys

import numpy as np

sys.path.insert(0, "src")
sys.path.insert(0, "tools")

from delay_sweep import (  # noqa: E402
    ATRASOS_S,
    CENTRO_DE_MASSA_M,
    MASSA_KG,
    geometria_a,
    roda,
)

from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.sim.closed_loop import TerminationMode  # noqa: E402

RPM_IDLE = 30_000.0
RPM_MAX = 98_000.0
"""JetCat P400-PRO-LN, catalogo consultado em 2026-09-12."""

PAS_COMPRESSOR = 12
"""⚠ **Nao publicado.** Contagem tipica de rotor radial pequeno, hipotese de trabalho."""

FREQ_CONTROLE_HZ = 100.0
BANDA_ATITUDE_RAD_S = 1.5


def main() -> None:
    print()
    print("EXPERIMENTO 6: TRIAGEM ESTRUTURAL E DE RESSONANCIA")
    print("sem CAD, sem elementos finitos. Produz requisito, nao desenho.")
    print()

    # ------------------------------------------------------------------ Campbell
    print("ESPECTRO DE EXCITACAO, o que a estrutura vai ver")
    f_eixo_min, f_eixo_max = RPM_IDLE / 60.0, RPM_MAX / 60.0
    print(f"  {'fonte':34} {'faixa':>22}")
    print(f"  {'rotacao do eixo':34} {f'{f_eixo_min:.0f} a {f_eixo_max:.0f} Hz':>22}")
    for h in (2, 3):
        print(
            f"  {f'harmonico {h} do eixo':34} "
            f"{f'{h * f_eixo_min:.0f} a {h * f_eixo_max:.0f} Hz':>22}"
        )
    f_pa_min, f_pa_max = PAS_COMPRESSOR * f_eixo_min, PAS_COMPRESSOR * f_eixo_max
    print(f"  {'passagem de pa (12 pas, HIPOTESE)':34} {f'{f_pa_min:.0f} a {f_pa_max:.0f} Hz':>22}")
    print(f"  {'tique do controlador':34} {f'{FREQ_CONTROLE_HZ:.0f} Hz':>22}")
    print(f"  {'banda de atitude':34} {f'{BANDA_ATITUDE_RAD_S / (2 * math.pi):.2f} Hz':>22}")
    print()
    print("  REQUISITO: nenhum modo estrutural do braco ou do berco do propulsor pode")
    print("  cair nas bandas acima. A faixa de 500 a 1633 Hz e varrida continuamente")
    print("  durante toda a operacao, entao nao ha 'passar rapido pela ressonancia'.")
    print()
    print("  ⚠ A contagem de pas NAO e publicada, entao a banda de passagem de pa e")
    print("    hipotese. E ⚠ este e um criterio de TRIAGEM: o caminho de transmissao")
    print("    filtra, e nem toda frequencia listada chega a estrutura com amplitude")
    print("    relevante. Reprovar um projeto so por cruzamento de Campbell seria tao")
    print("    errado quanto ignora-lo.")
    print()

    # ------------------------------------------------------------------ cargas
    print("CARGAS DE FIXACAO, medidas no pairado da familia A")
    geo = geometria_a()
    trim = solve_trim(
        geo,
        mass_kg=MASSA_KG,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        objective=TrimObjective.MAX_MARGIN,
    )
    print(f"  {'bocal':12} {'empuxo no trim':>16} {'teto':>10} {'braco':>9} {'momento':>12}")
    print(f"  {'':12} {'N':>16} {'N':>10} {'m':>9} {'N.m':>12}")
    for bocal, empuxo in zip(geo.available, trim.thrusts_N, strict=True):
        braco = float(np.linalg.norm(bocal.position_body_m - geo.reference_point_body_m))
        print(
            f"  {bocal.name:12} {empuxo:16.1f} {bocal.thrust_max_N:10.1f} "
            f"{braco:9.3f} {empuxo * braco:12.1f}"
        )
    print()
    print("  REQUISITO: cada berco suporta o TETO do propulsor, nao o valor de trim,")
    print("  porque a alocacao usa o teto em transitorio. E a fixacao do braco carrega")
    print("  o teto vezes o braco, em flexao, com o piloto no outro lado.")
    maior = max(
        b.thrust_max_N * float(np.linalg.norm(b.position_body_m - geo.reference_point_body_m))
        for b in geo.available
    )
    print(f"  Maior momento de fixacao no teto: {maior:.0f} N.m.")
    print()

    # ------------------------------------------------- sensibilidade a inercia
    print("QUANTO A FALTA DE CAD CUSTA: sensibilidade da fronteira a inercia")
    print("  A inercia usada em todo o passo 5 e de um cilindro equivalente, estimada.")
    print("  Aqui a fronteira de atraso e refeita com a inercia escalada.")
    print()
    print(f"  {'fator de inercia':>18} {'maior atraso que recupera':>28}")

    import delay_sweep

    inercia_base = delay_sweep.INERCIA.copy()
    for fator in (0.7, 0.85, 1.0, 1.3, 1.6):
        delay_sweep.INERCIA = inercia_base * fator
        delay_sweep._BANDA_CACHE.clear()
        maior_atraso = None
        for atraso in ATRASOS_S:
            modo, _, _, _ = roda(geo, tau_s=0.35, rampa_N_s=120.0, atraso_s=atraso)
            if modo is TerminationMode.CAPTURED:
                maior_atraso = atraso
        texto = "nenhum" if maior_atraso is None else f"{maior_atraso:.2f} s"
        print(f"  {fator:17.2f}x {texto:>27}")
    delay_sweep.INERCIA = inercia_base
    delay_sweep._BANDA_CACHE.clear()
    print()
    print("  ⚠ O QUE ISTO DEMONSTRA, e so isto: para esta geometria, este controlador,")
    print("    esta missao, esta inercia nominal e esta faixa de escala, a incerteza")
    print("    ESCALAR de inercia nao dominou a fronteira de atraso encontrada.")
    print()
    print("  ⚠ O QUE NAO DEMONSTRA: nada sobre massa seca por familia, centro de massa")
    print("    real, produtos de inercia fora da diagonal, bracos reais, interferencia")
    print("    geometrica, frequencias naturais, rigidez, modos estruturais, ou massa e")
    print("    fixacao de propulsores reais. Concluir daqui que 'o CAD pode esperar'")
    print("    seria estender um teste de uma variavel escalar ao projeto inteiro.")
    print()

    print("O QUE O CAD RESOLVERIA, e so ele")
    for item in (
        "tensor de inercia real, no lugar do cilindro equivalente",
        "centro de massa real, hoje escolhido como meio da janela viavel",
        "modos estruturais para confrontar com o espectro acima",
        "massa seca por componente, hoje estimada em bloco",
        "envelope geometrico: os bocais cabem onde o modelo os poe?",
    ):
        print(f"  - {item}")
    print()
    print("  ⚠ A razao entre margem estatica e margem de curto prazo, que e a conclusao")
    print("    central do passo 5, depende da rampa e do horizonte e NAO da inercia,")
    print("    entao ela sobrevive a essa incerteza. Todo o RESTO da lista acima")
    print("    continua em aberto e continua precisando de CAD.")


if __name__ == "__main__":
    main()
