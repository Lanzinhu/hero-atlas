"""Sessoes de automacao do Hero Atlas."""

import nox

nox.options.default_venv_backend = "venv"
nox.options.sessions = ["lint", "test", "resultados"]

PY = "3.12"


@nox.session(python=PY)
def lint(session: nox.Session) -> None:
    """Ruff: lint e formatacao."""
    session.install("ruff")
    # ⚠ `tools/` entra no portao. Scripts de experimento produzem exatamente os
    # numeros que vao para relatorio, entao deixa-los fora do lint criava uma pasta
    # onde resultado publicado nascia sem verificacao nenhuma.
    session.run("ruff", "check", "src", "tests", "tools", "noxfile.py")
    session.run("ruff", "format", "--check", "src", "tests", "tools", "noxfile.py")


@nox.session(python=PY)
def test(session: nox.Session) -> None:
    """Suite completa."""
    session.install("-e", ".[dev]")
    session.run("pytest", *session.posargs)


@nox.session(python=PY)
def smoke(session: nox.Session) -> None:
    """Teste de fumaca: o nucleo roda sem nenhum extra instalado, em menos de 30 s.

    Protege o principio de isolamento do nucleo. Se esta sessao quebrar, alguma coisa
    pesada entrou no caminho de import.
    """
    session.install("-e", ".")
    session.install("pytest")
    session.run("pytest", "tests/validation", "-q")


@nox.session(python=PY)
def resultados(session: nox.Session) -> None:
    """Os resultados versionados estao atualizados em relacao ao codigo?

    Regenera ``docs/resultados/`` e **falha se o Git acusar diferenca**.

    O motivo e concreto. As saidas dos experimentos sao lidas por quem revisa o
    projeto sem executar nada, e uma mudanca de codigo que altere um numero sem
    atualizar o artefato publicado deixaria o repositorio afirmando uma coisa e
    calculando outra. Com esta sessao, alterar o resultado passa a **exigir**
    regenerar e revisar o diff, que e onde a mudanca fica visivel.

    ⚠ Depende de as saidas serem deterministicas. Sao: nenhuma delas imprime data,
    tempo de execucao ou valor aleatorio. Se alguma passar a imprimir, esta sessao
    comeca a falhar sem motivo real, e a correcao e tirar o campo instavel da saida,
    nunca relaxar a verificacao.
    """
    session.install("-e", ".")
    session.run("python", "tools/refresh_results.py")
    session.run(
        "git",
        "diff",
        "--exit-code",
        "--",
        "docs/resultados/",
        external=True,
        success_codes=[0],
    )
