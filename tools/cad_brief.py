"""Gera o briefing de CAD: o que modelar, com numero, e o que devolver ao simulador.

Roda com::

    ./.venv/Scripts/python.exe tools/cad_brief.py

O CAD conceitual nao existe para "desenhar o traje". Ele existe para fechar cinco
lacunas que nenhum calculo alcanca, e para devolver ao simulador os numeros que hoje
sao estimativa em bloco.

⚠ **O CAD nao valida a arquitetura.** Ele mede a geometria que a arquitetura assume, e
pode **reprovar** essa geometria por envelope: os sete bocais podem simplesmente nao
caber onde o modelo os poe. Essa reprovacao seria um resultado, nao um contratempo.

⚠ Todas as posicoes abaixo sao **saida de modelo**, nao medida antropometrica. Elas
vieram da varredura de geometria, que otimizou autoridade de controle e nunca perguntou
se um corpo humano acomoda o resultado.
"""

from __future__ import annotations

import math
import sys

import numpy as np

sys.path.insert(0, "src")
sys.path.insert(0, "tools")

from delay_sweep import CENTRO_DE_MASSA_M, INERCIA, MASSA_KG, geometria_a  # noqa: E402

from hero_atlas.analysis.trim import TrimObjective, solve_trim  # noqa: E402
from hero_atlas.units import G0  # noqa: E402

PILOTO_KG = 80.0
ESTRUTURA_KG = 12.0
COMBUSTIVEL_KG = 20.0
TURBINA_KG = 2.20
"""Kingtech K-260G4, a que passou a triagem com folga. Registro em docs/sources/."""

TURBINA_DIAMETRO_MM = 120.0
TURBINA_COMPRIMENTO_MM = 299.0


def main() -> None:
    geo = geometria_a()
    trim = solve_trim(
        geo,
        mass_kg=MASSA_KG,
        center_of_mass_body_m=CENTRO_DE_MASSA_M,
        objective=TrimObjective.MAX_MARGIN,
    )

    print()
    print("BRIEFING DE CAD CONCEITUAL")
    print("familia A, sete bocais. O que modelar, e o que devolver ao simulador.")
    print()

    # ---------------------------------------------------------------- referencial
    print("1. REFERENCIAL, e ele precisa ser o mesmo dos dois lados")
    print("   origem: ponto de referencia estrutural fixo no corpo, ADR-001.")
    print("           NAO e o centro de massa, que migra com pose e combustivel.")
    print("   +x  para a FRENTE do piloto")
    print("   +y  para a DIREITA do piloto")
    print("   +z  para BAIXO")
    print()
    print("   ⚠ O eixo z para baixo e convencao aeronautica e contraria a de quase todo")
    print("     CAD, que usa z para cima. Modelar com z para cima e depois espelhar na")
    print("     exportacao e a fonte de erro de sinal mais provavel deste passo.")
    print()

    # ---------------------------------------------------------------- bocais
    print("2. POSICAO E DIRECAO DE CADA BOCAL, em milimetros")
    print("   A direcao e para onde a FORCA aponta, ou seja o contrario do jato.")
    print()
    cab = (
        f"   {'bocal':12} {'x':>8} {'y':>8} {'z':>8} | "
        f"{'inclin. lateral':>16} {'inclin. long.':>14}"
    )
    print(cab)
    print(f"   {'':12} {'mm':>8} {'mm':>8} {'mm':>8} | {'graus':>16} {'graus':>14}")
    print("   " + "-" * (len(cab) - 3))
    for bocal in geo.nozzles:
        p = bocal.position_body_m * 1000.0
        d = bocal.direction_body
        lateral = math.degrees(math.atan2(abs(d[1]), -d[2]))
        longitudinal = math.degrees(math.asin(np.clip(d[0], -1.0, 1.0)))
        print(
            f"   {bocal.name:12} {p[0]:8.1f} {p[1]:8.1f} {p[2]:8.1f} | "
            f"{lateral:16.1f} {longitudinal:14.1f}"
        )
    print()
    print("   Vetores de direcao normalizados, para conferencia:")
    for bocal in geo.nozzles:
        d = bocal.direction_body
        print(f"   {bocal.name:12} [{d[0]:+.4f}, {d[1]:+.4f}, {d[2]:+.4f}]")
    print()

    # ---------------------------------------------------------------- envelope
    print("3. A PERGUNTA QUE SO O CAD RESPONDE: isto cabe num corpo humano?")
    envergaduras = sorted({abs(float(b.position_body_m[1])) for b in geo.nozzles})
    print(f"   meia envergadura exigida: {[f'{e * 1000:.0f}' for e in envergaduras]} mm")
    print(
        f"   turbina assumida: {TURBINA_DIAMETRO_MM:.0f} mm de diametro por "
        f"{TURBINA_COMPRIMENTO_MM:.0f} mm"
    )
    print()
    print("   Verificar, com o corpo em pose de pairado:")
    for item in (
        "o par mais externo fica a 400 mm do plano medio: e alcance de braco ou de estrutura?",
        "tres turbinas por lado, escalonadas em altura de 150 a 370 mm abaixo da origem",
        "o jato de um bocal atinge a estrutura ou a perna do bocal de baixo?",
        "o bocal dorsal a 100 mm ACIMA da origem passa por cima do ombro ou pelas costas?",
        "sobra caminho para linha de combustivel, cabo e exaustao sem cruzar o corpo",
    ):
        print(f"     - {item}")
    print()
    print("   ⚠ Se nao couber, a geometria morre e o funil precisa rodar de novo com")
    print("     restricao de envelope. Isso seria resultado, nao contratempo.")
    print()

    # ---------------------------------------------------------------- massa
    print("4. ORCAMENTO DE MASSA A FECHAR, hoje estimado em bloco")
    print(f"   {'componente':34} {'alvo':>9} {'estado hoje':>16}")
    linhas = (
        ("piloto com protecao", PILOTO_KG, "estimado"),
        (f"7 turbinas de {TURBINA_KG:.2f} kg", 7 * TURBINA_KG, "de catalogo"),
        ("estrutura, tanques, linhas, aviônica", ESTRUTURA_KG, "ESTIMADO EM BLOCO"),
        ("combustivel", COMBUSTIVEL_KG, "escolha de missao"),
    )
    total = 0.0
    for nome, valor, estado in linhas:
        total += valor
        print(f"   {nome:34} {valor:7.1f} kg {estado:>16}")
    print(f"   {'TOTAL':34} {total:7.1f} kg")
    print()
    print("   ⚠ Os 12 kg de estrutura sao o numero mais fraco do projeto inteiro. Eles")
    print("     precisam virar soma de pecas: berco de turbina, braco, cinto, tanque,")
    print("     bomba, valvula, bateria de aviônica, cabo, protecao termica.")
    print()
    print("   O CAD REPROVA a massa se a soma passar de:")
    folga = geo.total_thrust_max_N / G0 * 0.85 - total
    print(f"     {geo.total_thrust_max_N / G0 * 0.85:.1f} kg  (85 por cento do empuxo instalado)")
    print(f"     folga atual: {folga:.1f} kg")
    print()

    # ---------------------------------------------------------------- contrato
    print("5. O QUE O CAD DEVOLVE AO SIMULADOR, por componente")
    print("   A interface ja existe: hero_atlas.airframe.mass_properties.MassComponent")
    print()
    print("     mass_kg                          massa da peca")
    print("     center_of_mass_body_m            centro da peca, no referencial acima")
    print("     inertia_about_own_cg_kg_m2       tensor 3x3 sobre o centro DA PECA")
    print("     orientation_body_from_component  rotacao da peca para o corpo")
    print()
    print("   ⚠ O tensor precisa ser sobre o centro DA PROPRIA PECA, nao sobre a origem.")
    print("     O agregador faz rotacao e eixos paralelos; se a peca ja vier transladada,")
    print("     a translacao entra duas vezes e a inercia sai maior, sem erro visivel.")
    print()
    print("   O agregador entao calcula, e isso substitui as estimativas de hoje:")
    print(f"     massa total          hoje {MASSA_KG:.1f} kg, estimada")
    print(f"     centro de massa      hoje {(CENTRO_DE_MASSA_M * 1000).tolist()} mm, ESCOLHIDO")
    print(f"     tensor de inercia    hoje diag{np.diag(INERCIA).tolist()}, cilindro equivalente")
    print()
    print("   ⚠ O centro de massa de hoje nao e estimativa: e o MEIO DA JANELA VIAVEL.")
    print("     Foi escolhido para o trim fechar, nao medido. O CAD pode devolver um")
    print("     centro fora dessa janela, e ai a geometria precisa mudar.")
    print("     Janela longitudinal viavel hoje: 105 a 210 mm.")
    print()

    # ---------------------------------------------------------------- estrutura
    print("6. REQUISITOS ESTRUTURAIS JA LEVANTADOS")
    maior_momento = max(
        b.thrust_max_N * float(np.linalg.norm(b.position_body_m - geo.reference_point_body_m))
        for b in geo.nozzles
    )
    print(f"   carga por berco, no TETO do propulsor:   {geo.nozzles[0].thrust_max_N:.0f} N")
    print(f"   maior momento de fixacao, em flexao:     {maior_momento:.0f} N.m")
    print(f"   empuxo no trim, por bocal:               {trim.thrusts_N.mean():.0f} N")
    print()
    print("   ⚠ Dimensionar pelo TETO, nao pelo trim. A alocacao usa o teto em")
    print("     transitorio, e o piloto esta do outro lado da alavanca.")
    print()
    print("   Bandas de excitacao a evitar em modo estrutural, com a turbina assumida:")
    print("     eixo:            550 a 1867 Hz")
    print("     2o harmonico:   1100 a 3733 Hz")
    print("     tique de controle:      100 Hz")
    print()
    print("   ⚠ A faixa do eixo e varrida continuamente em operacao. Nao ha 'passar")
    print("     rapido pela ressonancia' como em partida de motor.")
    print()

    # ---------------------------------------------------------------- ordem
    print("7. ORDEM SUGERIDA DE MODELAGEM")
    for i, passo in enumerate(
        (
            "manequim do piloto em pose de pairado, so para envelope e massa",
            "sete turbinas como cilindros com a massa real de catalogo",
            "posicionar pelas coordenadas da secao 2 e CONFERIR SE CABE",
            "bracos e bercos, so entao, com secao que aguente o momento da secao 6",
            "tanque, linhas e aviônica, para fechar os 12 kg",
            "exportar propriedades por componente e alimentar o agregador",
            "rodar o funil de novo com a massa e inercia reais",
        ),
        start=1,
    ):
        print(f"   {i}. {passo}")
    print()
    print("   ⚠ O passo 3 e um portao. Se nao couber, parar ali e voltar ao funil, em")
    print("     vez de continuar modelando uma geometria impossivel.")


if __name__ == "__main__":
    main()
