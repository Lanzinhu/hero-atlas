"""O nucleo importa apenas numpy, scipy e pydantic.

Ver vault/01 - Visao/Escopo e nao-escopo.md

    Ferramentas pesadas produzem decks que o nucleo consome por interface, e nunca
    sao importadas por ele. O simulador roda no primeiro dia e continua rodando se
    nada pesado for instalado.

Este e o teste que protege o principio contra erosao. Um ``import pandas`` no topo de
um modulo do nucleo passa despercebido em revisao e transforma o projeto em refem de
uma arvore de dependencias que ele nao precisa.
"""

from __future__ import annotations

import importlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.validation

MODULOS_DO_NUCLEO = [
    "hero_atlas",
    "hero_atlas.units",
    "hero_atlas.provenance",
    "hero_atlas.airframe",
    "hero_atlas.airframe.mass_properties",
    "hero_atlas.sim",
    "hero_atlas.sim.events",
    "hero_atlas.io",
    "hero_atlas.io.telemetry",
    "hero_atlas.model_status",
    "hero_atlas.analysis",
    "hero_atlas.analysis.requirements",
]

MODULOS_PESADOS = [
    "pandas",
    "pyarrow",
    "matplotlib",
    "casadi",
    "control",
    "openmdao",
    "pycycle",
    "jsbsim",
    "osqp",
]


@pytest.mark.parametrize("modulo", MODULOS_DO_NUCLEO)
def test_modulo_do_nucleo_importa(modulo: str):
    importlib.import_module(modulo)


def test_nenhum_modulo_pesado_entra_no_caminho_de_import():
    """Roda num processo limpo, senao a propria suite ja teria carregado tudo."""
    script = (
        "import sys\n"
        "import hero_atlas, hero_atlas.units, hero_atlas.provenance\n"
        "import hero_atlas.airframe, hero_atlas.sim, hero_atlas.io\n"
        "import hero_atlas.model_status, hero_atlas.analysis\n"
        f"pesados = [m for m in {MODULOS_PESADOS!r} if m in sys.modules]\n"
        "print(','.join(pesados))\n"
    )
    resultado = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    carregados = [m for m in resultado.stdout.strip().split(",") if m]

    assert not carregados, (
        f"o nucleo carregou modulos pesados: {carregados}. "
        "Mova o import para dentro da funcao que precisa dele."
    )


def test_pandas_e_importado_sob_demanda_na_telemetria():
    """``to_dataframe`` pode usar pandas, mas so quando chamado."""
    import hero_atlas.io.telemetry as telemetria

    fonte = (telemetria.__file__ or "").strip()
    assert fonte

    with open(fonte, encoding="utf-8") as handle:
        linhas = handle.readlines()

    importa_no_topo = [
        n
        for n, linha in enumerate(linhas, start=1)
        if linha.startswith(("import pandas", "from pandas"))
    ]
    assert not importa_no_topo, (
        f"pandas importado no topo, linhas {importa_no_topo}. "
        "O import tem que estar dentro de to_dataframe."
    )
