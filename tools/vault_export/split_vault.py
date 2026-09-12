"""Fatia o vault em partes de texto coláveis num chat externo.

Agrupa notas inteiras ate um limite de caracteres, sem quebrar uma nota no meio
salvo quando ela sozinha ja excede o limite. A ordem e deterministica (caminho
relativo POSIX, ordenado), de forma que rodar duas vezes produz as mesmas partes.

Uso:
    python tools/vault_export/split_vault.py
    python tools/vault_export/split_vault.py --max-chars 8000 --out _build/outro

Nao importa nada fora da stdlib: nao e nucleo, nao entra no caminho de import
de hero_atlas. Ver vault/01 - Visao/Escopo e nao-escopo.md
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VAULT = REPO_ROOT / "vault"
DEFAULT_OUT = REPO_ROOT / "_build" / "vault-export"
DEFAULT_MAX_CHARS = 11_000

# Pastas do vault que nao sao conteudo.
SKIP_DIRS = {".obsidian", ".trash"}


@dataclass
class Part:
    """Uma parte: um ou mais blocos de texto que cabem num limite de caracteres."""

    blocks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.blocks)

    def __len__(self) -> int:
        return len(self.text)


def collect_notes(vault: Path) -> list[Path]:
    """Todas as notas .md do vault, em ordem estavel."""
    notes = [
        p
        for p in vault.rglob("*.md")
        if not any(part in SKIP_DIRS for part in p.relative_to(vault).parts)
    ]
    return sorted(notes, key=lambda p: p.relative_to(vault).as_posix())


def split_oversized(header: str, body: str, max_chars: int) -> list[str]:
    """Fatia uma nota que sozinha excede o limite, quebrando entre linhas."""
    budget = max_chars - len(header) - 40  # folga para o marcador de continuacao
    pieces: list[str] = []
    current: list[str] = []
    size = 0
    for line in body.splitlines(keepends=True):
        if size + len(line) > budget and current:
            pieces.append("".join(current))
            current, size = [], 0
        current.append(line)
        size += len(line)
    if current:
        pieces.append("".join(current))

    total = len(pieces)
    return [
        f"{header} (trecho {i + 1}/{total})\n\n{piece.strip()}\n" for i, piece in enumerate(pieces)
    ]


def build_parts(vault: Path, max_chars: int) -> list[Part]:
    parts: list[Part] = []
    current = Part()

    for note in collect_notes(vault):
        rel = note.relative_to(vault).as_posix()
        header = f"## ARQUIVO: {rel}"
        body = note.read_text(encoding="utf-8").strip()
        blocks = (
            split_oversized(header, body, max_chars)
            if len(header) + len(body) + 4 > max_chars
            else [f"{header}\n\n{body}\n"]
        )

        for block in blocks:
            if current.blocks and len(current) + len(block) > max_chars:
                parts.append(current)
                current = Part()
            current.blocks.append(block)
            current.notes.append(rel)

    if current.blocks:
        parts.append(current)
    return parts


def write_parts(parts: list[Part], out: Path, vault: Path, max_chars: int) -> dict:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    entries = []
    for i, part in enumerate(parts, start=1):
        name = f"parte-{i:02d}.md"
        (out / name).write_text(part.text, encoding="utf-8")
        entries.append(
            {
                "n": i,
                "name": name,
                "chars": len(part),
                "notes": sorted(set(part.notes)),
            }
        )

    manifest = {
        "vault": vault.relative_to(REPO_ROOT).as_posix(),
        "max_chars": max_chars,
        "total": len(parts),
        "total_chars": sum(e["chars"] for e in entries),
        "parts": entries,
    }
    (out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS)
    args = parser.parse_args()

    if not args.vault.is_dir():
        raise SystemExit(f"vault nao encontrado: {args.vault}")

    parts = build_parts(args.vault, args.max_chars)
    manifest = write_parts(parts, args.out, args.vault, args.max_chars)

    print(f"{manifest['total']} partes, {manifest['total_chars']} chars -> {args.out}")
    for entry in manifest["parts"]:
        print(f"  {entry['name']}  {entry['chars']:>6} chars  {len(entry['notes'])} notas")


if __name__ == "__main__":
    main()
