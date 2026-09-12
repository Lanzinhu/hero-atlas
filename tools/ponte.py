"""Cliente da ponte: manda codigo para o FreeCAD aberto e traz a resposta.

Roda no Python do projeto. A ponte precisa estar ligada do outro lado, pela macro
``HeroAtlas_Ponte`` no menu Macro do FreeCAD.

Uso::

    ./.venv/Scripts/python.exe tools/ponte.py "print(doc.Name)"
    ./.venv/Scripts/python.exe tools/ponte.py --arquivo script.py
    ./.venv/Scripts/python.exe tools/ponte.py --estado

O escopo do outro lado ja vem com ``App``, ``Gui`` e ``doc``, que e o documento ativo.

⚠ Se a conexao for recusada, a ponte esta desligada. Isso e o padrao: ela so existe
enquanto alguem a liga de proposito.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8765
TEMPO_LIMITE_S = 30.0

ESTADO = """
import FreeCAD as App
doc = App.ActiveDocument
print(f"documento ativo: {doc.Name if doc else '(nenhum)'}")
if doc:
    print(f"arquivo: {doc.FileName or '(nao salvo)'}")
    print(f"{len(doc.Objects)} objetos:")
    for o in doc.Objects:
        forma = getattr(o, 'Shape', None)
        solido = 'solido' if forma is not None and forma.Solids else '---'
        print(f"  {o.Name:28} {o.TypeId:22} {solido}")
print()
print("documentos abertos:", list(App.listDocuments()))
"""


def envia(codigo: str, *, host: str = HOST, porta: int = PORT) -> dict:
    """Manda o codigo e devolve o dicionario de resposta."""
    carga = codigo.encode("utf-8")
    with socket.create_connection((host, porta), timeout=TEMPO_LIMITE_S) as s:
        s.sendall(f"{len(carga)}\n".encode("ascii"))
        s.sendall(carga)
        pedacos = []
        while True:
            pedaco = s.recv(65536)
            if not pedaco:
                break
            pedacos.append(pedaco)
    bruto = b"".join(pedacos)
    if not bruto:
        raise RuntimeError("a ponte fechou sem responder")
    return json.loads(bruto.decode("utf-8"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("codigo", nargs="?", help="codigo Python a executar no FreeCAD")
    p.add_argument("--arquivo", help="le o codigo de um arquivo")
    p.add_argument("--estado", action="store_true", help="mostra o documento aberto")
    p.add_argument("--porta", type=int, default=PORT)
    args = p.parse_args()

    if args.estado:
        codigo = ESTADO
    elif args.arquivo:
        codigo = Path(args.arquivo).read_text(encoding="utf-8")
    elif args.codigo:
        codigo = args.codigo
    else:
        codigo = sys.stdin.read()

    try:
        resposta = envia(codigo, porta=args.porta)
    except ConnectionRefusedError:
        print("Ponte desligada.", file=sys.stderr)
        print("No FreeCAD: Macro > Macros > HeroAtlas_Ponte > Executar.", file=sys.stderr)
        return 2
    except OSError as erro:
        print(f"Falha de conexao: {erro}", file=sys.stderr)
        return 2

    saida = resposta.get("saida", "")
    if saida:
        print(saida, end="" if saida.endswith("\n") else "\n")
    if not resposta.get("ok", False):
        print(resposta.get("erro", "erro desconhecido"), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
