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

import ast
import dataclasses
import importlib
import subprocess
import sys

import pytest

pytestmark = pytest.mark.validation

MODULOS_DO_NUCLEO = [
    "hero_atlas",
    "hero_atlas.units",
    "hero_atlas.verdict",
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
        "import hero_atlas.model_status, hero_atlas.analysis, hero_atlas.verdict\n"
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


# --------------------------------------------------------------------------- #
# Varredura estatica: o que o teste de runtime nao consegue provar
# --------------------------------------------------------------------------- #


@dataclasses.dataclass(frozen=True)
class ImportSite:
    """Um ponto do codigo que causa importacao quando o arquivo e carregado.

    Attributes:
        lineno: linha.
        module: nome do modulo, ou ``None`` quando o nome e computado e nao da para
            decidir estaticamente.
        form: como a importacao acontece.
    """

    lineno: int
    module: str | None
    form: str  # "import" | "from" | "importlib" | "__import__"

    @property
    def is_resolved(self) -> bool:
        return self.module is not None


def _sites_de_import_no_carregamento(source: str) -> list[ImportSite]:
    """Tudo que importa quando o arquivo e carregado.

    Desce por todo no **menos** corpo de funcao, de funcao assincrona e de lambda,
    porque esses sao preguicosos. Corpo de classe, bloco ``try`` e ``if`` de modulo
    executam no import e portanto contam.

    Cobre quatro formas:

    - ``import x``
    - ``from x import y``
    - ``importlib.import_module("x")``
    - ``__import__("x")``

    As duas ultimas existem no detector nao porque sejam desejaveis, mas porque
    alguem contornando a regra por plugin, compatibilidade ou carregamento opcional
    chegaria nelas sem ma fe. Nome computado devolve ``module=None``, para o teste
    poder falhar de forma conservadora em vez de aprovar por nao conseguir decidir.
    """
    sites: list[ImportSite] = []

    def nome_do_alvo(call: ast.Call) -> str | None:
        if call.args and isinstance(call.args[0], ast.Constant):
            valor = call.args[0].value
            if isinstance(valor, str):
                return valor
        return None

    def caminhar(no: ast.AST) -> None:
        for filho in ast.iter_child_nodes(no):
            if isinstance(filho, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
                continue  # preguicoso, permitido
            if isinstance(filho, ast.Import):
                sites.extend(
                    ImportSite(filho.lineno, alias.name, "import") for alias in filho.names
                )
            elif isinstance(filho, ast.ImportFrom) and filho.module and filho.level == 0:
                sites.append(ImportSite(filho.lineno, filho.module, "from"))
            elif isinstance(filho, ast.Call):
                func = filho.func
                if isinstance(func, ast.Attribute) and func.attr == "import_module":
                    sites.append(ImportSite(filho.lineno, nome_do_alvo(filho), "importlib"))
                elif isinstance(func, ast.Name) and func.id == "__import__":
                    sites.append(ImportSite(filho.lineno, nome_do_alvo(filho), "__import__"))
            caminhar(filho)

    caminhar(ast.parse(source))
    return sites


def _fonte_do_modulo(modulo: str) -> str:
    mod = importlib.import_module(modulo)
    origem = getattr(mod, "__file__", None)
    if origem is None:  # pragma: no cover
        pytest.skip(f"{modulo} sem arquivo de origem")
    with open(origem, encoding="utf-8") as handle:
        return handle.read()


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
    proibidos = set(MODULOS_PESADOS)
    violacoes = [
        (s.lineno, s.module, s.form)
        for s in _sites_de_import_no_carregamento(_fonte_do_modulo(modulo))
        if s.module is not None and s.module.split(".")[0] in proibidos
    ]

    assert not violacoes, (
        f"{modulo} importa modulo pesado no carregamento: {violacoes}. "
        "Mova para dentro da funcao que precisa dele."
    )


@pytest.mark.parametrize("modulo", MODULOS_DO_NUCLEO)
def test_nenhum_import_dinamico_indecidivel_no_nucleo(modulo: str):
    """Falha conservadora quando o nome do modulo e computado.

    O nucleo e pequeno e nao tem necessidade legitima de importacao dinamica em
    escopo de modulo. Quando o alvo nao e decidivel estaticamente, o detector nao
    pode aprovar por nao conseguir decidir: seria o mesmo erro de categoria que o
    projeto corrigiu em outros lugares, ausencia de evidencia virando aprovacao.
    """
    indecidiveis = [
        (s.lineno, s.form)
        for s in _sites_de_import_no_carregamento(_fonte_do_modulo(modulo))
        if not s.is_resolved
    ]

    assert not indecidiveis, (
        f"{modulo} tem importacao dinamica com nome computado no carregamento: "
        f"{indecidiveis}. Torne o nome literal, ou mova para dentro de uma funcao."
    )


# --------------------------------------------------------------------------- #
# Testes do proprio detector
# --------------------------------------------------------------------------- #


def _modulos(fonte: str) -> list[str | None]:
    return [s.module for s in _sites_de_import_no_carregamento(fonte)]


def test_detector_pega_o_caso_try_except():
    """O padrao que o teste de runtime deixa passar quando a lib nao esta instalada."""
    fonte = "try:\n    import pandas\nexcept ImportError:\n    pandas = None\n"
    assert "pandas" in _modulos(fonte)


def test_detector_pega_importlib_com_nome_literal():
    fonte = 'import importlib\nmod = importlib.import_module("pandas")\n'
    assert "pandas" in _modulos(fonte)


def test_detector_pega_dunder_import():
    fonte = 'mod = __import__("pandas")\n'
    assert "pandas" in _modulos(fonte)


def test_detector_pega_import_em_corpo_de_classe():
    """Corpo de classe executa no import."""
    fonte = "class C:\n    import pandas\n"
    assert "pandas" in _modulos(fonte)


def test_detector_pega_import_sob_if_de_modulo():
    fonte = "import sys\nif sys.version_info >= (3, 12):\n    import pandas\n"
    assert "pandas" in _modulos(fonte)


def test_detector_marca_nome_computado_como_indecidivel():
    fonte = 'import importlib\nnome = "pan" + "das"\nmod = importlib.import_module(nome)\n'
    dinamicos = [s for s in _sites_de_import_no_carregamento(fonte) if s.form == "importlib"]

    assert len(dinamicos) == 1
    assert dinamicos[0].is_resolved is False
    assert dinamicos[0].module is None


def test_detector_permite_import_lazy_em_funcao():
    """Import dentro de funcao e o padrao correto e nao pode ser sinalizado."""
    fonte = "def to_dataframe():\n    import pandas as pd\n    return pd.DataFrame()\n"
    assert _modulos(fonte) == []


def test_detector_permite_import_lazy_em_lambda():
    """Lambda tambem e preguicoso."""
    fonte = 'f = lambda: __import__("pandas")\n'
    assert _modulos(fonte) == []


def test_detector_permite_import_lazy_em_funcao_assincrona():
    fonte = "async def carregar():\n    import pandas\n    return pandas\n"
    assert _modulos(fonte) == []
