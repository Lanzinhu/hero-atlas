"""Regenera as saidas dos experimentos em ``docs/resultados/``.

Roda com::

    ./.venv/Scripts/python.exe tools/refresh_results.py

Existe por um motivo concreto: quem revisa este projeto le o repositorio e **nao
executa o codigo**. Enquanto as tabelas viviam so no terminal de quem rodou, a revisao
tinha que confiar na transcricao, que e exatamente o ponto onde numero errado passa.

As saidas ficam versionadas. Uma mudanca de resultado aparece no diff, junto da
mudanca de codigo que a causou, e isso e a metade do valor: **resultado que muda sem
motivo declarado vira conflito visivel**, nao surpresa silenciosa.

⚠ Estes arquivos sao **gerados**. Nao edite a mao: rode este script.
"""

from __future__ import annotations

import contextlib
import io
import pathlib
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "tools")

import cad_brief  # noqa: E402
import compare_energy_architectures  # noqa: E402
import delay_sweep  # noqa: E402
import dump_geometry_detail  # noqa: E402
import funnel  # noqa: E402
import structure_screen  # noqa: E402
import sweep_geometry  # noqa: E402
import turbine_match  # noqa: E402

DESTINO = pathlib.Path("docs/resultados")

CABECALHO = """\
# GERADO AUTOMATICAMENTE por tools/refresh_results.py
# Nao edite a mao. Rode:  ./.venv/Scripts/python.exe tools/refresh_results.py
#
# Todos os numeros abaixo sao CONDICIONAIS a geometria plausivel e nao medida, a
# consumo especifico de catalogo extrapolado para pairado, e a parametros de energia
# declarados sem copia arquivada. Nada aqui representa hardware.
"""

EXPERIMENTOS = (
    ("experimento-1-geometria.txt", sweep_geometry.main),
    ("experimento-2-energia.txt", compare_energy_architectures.main),
    ("geometria-detalhe.txt", dump_geometry_detail.main),
    ("experimento-3-funil.txt", funnel.main),
    ("experimento-4-atraso.txt", delay_sweep.main),
    ("experimento-5-turbinas.txt", turbine_match.main),
    ("experimento-6-estrutura.txt", structure_screen.main),
    ("briefing-cad.txt", cad_brief.main),
)


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    for nome, rodar in EXPERIMENTOS:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            rodar()
        destino = DESTINO / nome
        destino.write_text(CABECALHO + buffer.getvalue(), encoding="utf-8")
        linhas = buffer.getvalue().count("\n")
        print(f"  {destino}  ({linhas} linhas)")


if __name__ == "__main__":
    main()
