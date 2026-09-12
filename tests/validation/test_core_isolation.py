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


def _imports_no_nivel_de_import(source: str) -> list[tuple[int, str]]:
    """Modulos importados quando o arquivo e carregado.

    Desce por tudo menos corpo de funcao, porque corpo de classe e bloco ``try``
    executam no import. Import dentro de funcao e lazy e **permitido**.
    """
    import ast

    encontrados: list[tuple[int, str]] = []

    def caminhar(no: ast.AST) -> None:
        for filho in ast.iter_child_nodes(no):
            if isinstance(filho, ast.FunctionDef | ast.AsyncFunctionDef):
                continue  # lazy, permitido
            if isinstance(filho, ast.Import):
                encontrados.extend((filho.lineno, alias.name) for alias in filho.names)
            elif isinstance(filho, ast.ImportFrom) and filho.module and filho.level == 0:
                encontrados.append((filho.lineno, filho.module))
            caminhar(filho)

    caminhar(ast.parse(source))
    return encontrados


@pytest.mark.parametrize("modulo", MODULOS_DO_NUCLEO)
def test_nenhum_import_pesado_no_texto_do_modulo(modulo: str):
    """Varredura estatica, porque a verificacao em tempo de execucao nao basta.

    O caso perigoso e este:

        try:
            import pacote_pesado
        except ImportError:
            pacote_pesado = None

    Ele passa no teste de ``sys.modules`` enquanto a biblioteca **nao** estiver
    instalada, e viola a arquitetura no dia em que estiver. O isolamento tem que
    falhar pelo ato de tentar importar, nao pela indisponibilidade local.

    Sem esta varredura o teste de runtime e vacuo para toda biblioteca que por acaso
    nao esteja no ambiente, que hoje e o caso de pandas, pyarrow e matplotlib.
    """
    mod = importlib.import_module(modulo)
    origem = getattr(mod, "__file__", None)
    if origem is None:  # pragma: no cover
        pytest.skip(f"{modulo} sem arquivo de origem")

    with open(origem, encoding="utf-8") as handle:
        source = handle.read()

    proibidos = set(MODULOS_PESADOS)
    violacoes = [
        (linha, nome)
        for linha, nome in _imports_no_nivel_de_import(source)
        if nome.split(".")[0] in proibidos
    ]

    assert not violacoes, (
        f"{modulo} importa modulo pesado no carregamento: {violacoes}. "
        "Mova para dentro da funcao que precisa dele."
    )


def test_a_varredura_estatica_detecta_o_caso_try_except():
    """Verifica o proprio detector, com o padrao que o teste de runtime deixa passar."""
    fonte = "try:\n    import pandas\nexcept ImportError:\n    pandas = None\n"
    encontrados = [nome for _linha, nome in _imports_no_nivel_de_import(fonte)]
    assert "pandas" in encontrados


def test_a_varredura_estatica_permite_import_lazy():
    """Import dentro de funcao e o padrao correto, e nao pode ser sinalizado."""
    fonte = "def to_dataframe():\n    import pandas as pd\n    return pd.DataFrame()\n"
    encontrados = [nome for _linha, nome in _imports_no_nivel_de_import(fonte)]
    assert encontrados == []
