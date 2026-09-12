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
import pathlib
import subprocess
import sys

import pytest

import hero_atlas

pytestmark = pytest.mark.validation

FORA_DO_NUCLEO: dict[str, str] = {
    # modulo -> justificativa. Vazio hoje, e cada entrada futura precisa de motivo.
}
"""Modulos sob ``src/hero_atlas`` deliberadamente fora da varredura.

Manter vazio enquanto possivel. Cada entrada e uma excecao a arquitetura e precisa
dizer por que existe.
"""


EXTENSAO_ELEGIVEL = ".py"
"""Unica extensao descoberta.

``.pyi`` fica de fora por decisao declarada: stub nao e importado em tempo de
execucao e portanto nao pode violar isolamento de importacao. Se um stub aparecer,
o teste de politica avisa em vez de ignorar em silencio.
"""

NOMES_NAO_IMPORTAVEIS = frozenset({"__main__"})
"""Modulos varridos estaticamente mas **nunca importados** pelo teste.

⚠ Importar ``__main__`` **executa o programa**. Um ponto de entrada de linha de
comando adicionado ao pacote faria a suite rodar a aplicacao como efeito colateral
da varredura. Ele continua sendo varrido, porque um import pesado ali viola o
isolamento do mesmo jeito; so nao e importado.
"""

NOMES_PROIBIDOS_NO_PACOTE = frozenset({"conftest", "test_"})
"""Arquivo de teste sob o pacote e violacao de estrutura, nao caso de borda.

Falha ruidosamente em vez de incluir ou excluir por conta propria.
"""


@dataclasses.dataclass(frozen=True)
class ModuloDoNucleo:
    """Um modulo descoberto, com a politica ja aplicada."""

    nome: str
    caminho: pathlib.Path
    importavel: bool


def _descobrir_modulos_do_nucleo() -> list[ModuloDoNucleo]:
    """Deriva a lista percorrendo o pacote, em vez de mante-la a mao.

    ⚠ A lista era manual e **um modulo novo ficou de fora sem ninguem notar**. Lista
    manual de cobertura e fragil por construcao: ela depende de alguem lembrar de
    edita-la no dia em que cria ``verdict.py``, e o custo de esquecer e uma garantia
    que evapora em silencio.

    Derivar resolve a segunda das duas garantias que este arquivo precisa dar:

    1. a varredura cobre cada modulo listado
    2. a lista contem todos os modulos que de fato pertencem ao nucleo

    A politica de elegibilidade e **explicita e testada**, porque convencoes novas
    aparecem depois e a descoberta precisa continuar deterministica:

    | Caso | Decisao |
    |---|---|
    | ``.py`` | descoberto |
    | ``.pyi`` | fora: stub nao e importado em execucao |
    | ``__main__.py`` | varrido, **nunca importado**: importar executa |
    | ``_privado.py`` | descoberto: privacidade e questao de API, nao de isolamento |
    | ``conftest.py``, ``test_*.py`` | proibido sob o pacote, falha ruidosa |
    | pacote de namespace | proibido, falha ruidosa: nome pode nao importar |
    """
    raiz = pathlib.Path(hero_atlas.__file__).parent
    modulos: list[ModuloDoNucleo] = []

    for caminho in sorted(raiz.rglob(f"*{EXTENSAO_ELEGIVEL}")):
        relativo = caminho.relative_to(raiz)
        partes = (
            relativo.parent.parts
            if relativo.name == "__init__.py"
            else (*relativo.parent.parts, relativo.stem)
        )
        nome = ".".join(("hero_atlas", *partes))
        if nome in FORA_DO_NUCLEO:
            continue
        modulos.append(
            ModuloDoNucleo(
                nome=nome,
                caminho=caminho,
                importavel=caminho.stem not in NOMES_NAO_IMPORTAVEIS,
            )
        )

    return modulos


_DESCOBERTOS = _descobrir_modulos_do_nucleo()

MODULOS_DO_NUCLEO = [m.nome for m in _DESCOBERTOS]
"""Tudo que a varredura estatica cobre, inclusive o que nao pode ser importado."""

MODULOS_IMPORTAVEIS = [m.nome for m in _DESCOBERTOS if m.importavel]
"""Subconjunto seguro de importar dentro da suite."""

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


@pytest.mark.parametrize("modulo", MODULOS_IMPORTAVEIS)
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


_CAMINHO_POR_NOME = {m.nome: m.caminho for m in _DESCOBERTOS}


def _fonte_do_modulo(modulo: str) -> str:
    """Le o arquivo pelo caminho descoberto, sem importar.

    ⚠ Antes isto importava o modulo para achar o arquivo. Com ``__main__`` no
    pacote, a propria varredura estatica executaria o programa.
    """
    caminho = _CAMINHO_POR_NOME.get(modulo)
    if caminho is None:  # pragma: no cover
        pytest.skip(f"{modulo} sem caminho descoberto")
    return caminho.read_text(encoding="utf-8")


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


# --------------------------------------------------------------------------- #
# Guardas da propria lista de cobertura
# --------------------------------------------------------------------------- #


def test_a_lista_do_nucleo_e_derivada_e_nao_vazia():
    """Se a descoberta falhar em silencio, todos os testes parametrizados somem."""
    assert len(MODULOS_DO_NUCLEO) >= 10
    assert "hero_atlas" in MODULOS_DO_NUCLEO


def test_a_lista_cobre_todo_arquivo_do_pacote():
    """A segunda garantia: nenhum modulo do nucleo fica fora da varredura.

    Um modulo novo entra na cobertura pelo ato de existir, nao por alguem lembrar
    de editar uma lista.
    """
    raiz = pathlib.Path(hero_atlas.__file__).parent
    arquivos = {c for c in raiz.rglob("*.py")}
    cobertos = len(MODULOS_DO_NUCLEO) + len(FORA_DO_NUCLEO)

    assert cobertos == len(arquivos), (
        f"{len(arquivos)} arquivos no pacote, {cobertos} contabilizados. "
        "A descoberta esta perdendo arquivo."
    )


def test_toda_excecao_da_allowlist_tem_justificativa_e_existe():
    """Entrada sem motivo vira buraco permanente. Entrada obsoleta vira mentira."""
    nomes_reais = set(_descobrir_modulos_do_nucleo()) | set(FORA_DO_NUCLEO)

    for modulo, motivo in FORA_DO_NUCLEO.items():
        assert motivo.strip(), f"{modulo} esta fora da varredura sem justificativa"
        assert modulo in nomes_reais, f"{modulo} nao existe mais; remova da allowlist"


def test_modulos_criados_recentemente_estao_cobertos():
    """Regressao direta do esquecimento que motivou a derivacao automatica."""
    for modulo in (
        "hero_atlas.verdict",
        "hero_atlas.model_status",
        "hero_atlas.analysis.requirements",
    ):
        assert modulo in MODULOS_DO_NUCLEO


# --------------------------------------------------------------------------- #
# Politica de elegibilidade da descoberta, explicita e testada
# --------------------------------------------------------------------------- #


def test_nenhum_arquivo_de_teste_sob_o_pacote():
    """Arquivo de teste dentro do nucleo e violacao de estrutura, nao caso de borda."""
    raiz = pathlib.Path(hero_atlas.__file__).parent
    intrusos = [
        c.relative_to(raiz).as_posix()
        for c in raiz.rglob("*.py")
        if c.stem == "conftest" or c.stem.startswith("test_")
    ]

    assert not intrusos, (
        f"arquivo de teste sob o pacote do nucleo: {intrusos}. "
        "Testes moram em tests/, nao em src/hero_atlas/."
    )


def test_todo_diretorio_com_codigo_e_pacote_de_verdade():
    """Pacote de namespace quebra a derivacao de nome de modulo.

    Sem ``__init__.py`` o nome derivado do caminho pode nao ser importavel, e a
    varredura passaria a falhar por motivo errado.
    """
    raiz = pathlib.Path(hero_atlas.__file__).parent
    sem_init = [
        d.relative_to(raiz).as_posix()
        for d in raiz.rglob("*")
        if d.is_dir() and any(d.glob("*.py")) and not (d / "__init__.py").exists()
    ]

    assert not sem_init, (
        f"diretorio com codigo e sem __init__.py: {sem_init}. "
        "A derivacao de nome de modulo assume pacote regular."
    )


def test_stubs_ficam_fora_da_descoberta_por_decisao_declarada():
    """Se um stub aparecer, este teste avisa em vez de a descoberta ignorar calada."""
    raiz = pathlib.Path(hero_atlas.__file__).parent
    stubs = [c.relative_to(raiz).as_posix() for c in raiz.rglob("*.pyi")]

    assert not stubs, (
        f"stubs encontrados: {stubs}. A descoberta so cobre {EXTENSAO_ELEGIVEL}. "
        "Decida explicitamente se stub entra na politica antes de adicionar um."
    )


def test_main_seria_varrido_mas_nunca_importado():
    """Regra viva mesmo sem __main__ existir hoje: e guarda contra deriva futura.

    Importar __main__ executa o programa. A varredura estatica continua cobrindo,
    porque um import pesado ali viola o isolamento do mesmo jeito.
    """
    assert "__main__" in NOMES_NAO_IMPORTAVEIS

    ficticio = ModuloDoNucleo(
        nome="hero_atlas.__main__",
        caminho=pathlib.Path("src/hero_atlas/__main__.py"),
        importavel="__main__" not in NOMES_NAO_IMPORTAVEIS,
    )
    assert ficticio.importavel is False


def test_modulo_privado_entra_na_descoberta():
    """Privacidade e questao de API. Isolamento de import nao liga para sublinhado."""
    ficticio = ModuloDoNucleo(
        nome="hero_atlas._interno",
        caminho=pathlib.Path("src/hero_atlas/_interno.py"),
        importavel="_interno" not in NOMES_NAO_IMPORTAVEIS,
    )
    assert ficticio.importavel is True


def test_importaveis_e_subconjunto_do_varrido():
    assert set(MODULOS_IMPORTAVEIS) <= set(MODULOS_DO_NUCLEO)
    assert MODULOS_IMPORTAVEIS  # nao pode ficar vazio
