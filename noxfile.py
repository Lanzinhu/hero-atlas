"""Sessoes de automacao do Hero Atlas."""

import nox

nox.options.default_venv_backend = "venv"
nox.options.sessions = ["lint", "test"]

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
