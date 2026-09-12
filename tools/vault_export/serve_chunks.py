"""Serve as partes geradas por split_vault.py para o script de browser.

Escuta apenas em 127.0.0.1. Guarda quais partes ja foram enviadas, de modo que
o envio e retomavel: se a sessao cair no meio, basta rodar o script de novo que
ele continua da proxima pendente.

Uso:
    python tools/vault_export/serve_chunks.py
    python tools/vault_export/serve_chunks.py --reset --port 8731

Endpoints:
    GET  /manifest.json   manifesto gerado pelo split
    GET  /parte-NN.md     texto de uma parte
    GET  /next            proxima parte pendente: {"n":5,"name":...,"total":13}
    POST /sent/5          marca a parte 5 como enviada
    POST /reset           esquece o progresso
"""

from __future__ import annotations

import argparse
import json
import re
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO_ROOT / "_build" / "vault-export"
DEFAULT_PORT = 8731

PART_RE = re.compile(r"^/parte-(\d+)\.md$")
SENT_RE = re.compile(r"^/sent/(\d+)$")


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, root: Path, **kwargs):
        self.root = root
        self.state_file = root / "state.json"
        super().__init__(*args, **kwargs)

    # --- estado -----------------------------------------------------------
    def load_sent(self) -> set[int]:
        if not self.state_file.exists():
            return set()
        return set(json.loads(self.state_file.read_text(encoding="utf-8"))["sent"])

    def save_sent(self, sent: set[int]) -> None:
        self.state_file.write_text(json.dumps({"sent": sorted(sent)}, indent=2), encoding="utf-8")

    def manifest(self) -> dict:
        return json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))

    # --- respostas --------------------------------------------------------
    def send(self, code: int, body: bytes, ctype: str = "text/plain; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("content-type", ctype)
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict, code: int = 200) -> None:
        self.send(
            code,
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    # --- rotas ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802  (assinatura da stdlib)
        if self.path == "/manifest.json":
            self.send_json(self.manifest())
            return

        if self.path == "/next":
            manifest = self.manifest()
            sent = self.load_sent()
            pending = [p for p in manifest["parts"] if p["n"] not in sent]
            self.send_json(
                {
                    "n": pending[0]["n"] if pending else None,
                    "name": pending[0]["name"] if pending else None,
                    "total": manifest["total"],
                    "restantes": len(pending),
                }
            )
            return

        match = PART_RE.match(self.path)
        if match:
            file = self.root / f"parte-{int(match.group(1)):02d}.md"
            if not file.exists():
                self.send_json({"erro": "parte inexistente"}, 404)
                return
            self.send(200, file.read_bytes(), "text/markdown; charset=utf-8")
            return

        self.send_json({"erro": "rota desconhecida"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/reset":
            self.save_sent(set())
            self.send_json({"ok": True, "sent": []})
            return

        match = SENT_RE.match(self.path)
        if match:
            sent = self.load_sent() | {int(match.group(1))}
            self.save_sent(sent)
            self.send_json({"ok": True, "sent": sorted(sent)})
            return

        self.send_json({"erro": "rota desconhecida"}, 404)

    def log_message(self, fmt: str, *args) -> None:
        print(f"  {self.address_string()} {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--reset", action="store_true", help="esquece o progresso ao subir")
    args = parser.parse_args()

    if not (args.dir / "manifest.json").exists():
        raise SystemExit(f"rode split_vault.py primeiro: sem manifest em {args.dir}")

    if args.reset:
        (args.dir / "state.json").unlink(missing_ok=True)

    handler = partial(Handler, root=args.dir)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    total = json.loads((args.dir / "manifest.json").read_text(encoding="utf-8"))["total"]
    print(f"servindo {total} partes de {args.dir} em http://127.0.0.1:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
