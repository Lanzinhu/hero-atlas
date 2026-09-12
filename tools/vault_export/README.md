# vault_export

Leva o vault inteiro para um chat externo (Inner AI, ChatGPT, etc.) quando o
objetivo e pedir uma avaliacao de fora. Chat web nao aceita 120 mil caracteres
numa mensagem, entao o vault vai fatiado, em texto, uma parte por mensagem.

Nao faz parte do nucleo: so stdlib, nenhum import de `hero_atlas`.
Ver `vault/01 - Visao/Escopo e nao-escopo.md`.

## Fluxo

```bash
# 1. fatiar o vault  ->  _build/vault-export/parte-NN.md + manifest.json
python tools/vault_export/split_vault.py

# 2. servir as partes (fica em primeiro plano; 127.0.0.1 apenas)
python tools/vault_export/serve_chunks.py
```

3. Com o chat aberto no browser controlado pelo Playwright MCP, rodar
   `send_to_chat.js` via `browser_run_code_unsafe` (parametro `filename`).
   Repetir a chamada ate o log dizer que nao ha pendencias — cada chamada
   envia `BATCH` partes (padrao 8, ~15 s por parte).

O envio e retomavel: o progresso vive em `_build/vault-export/state.json`, no
servidor. Se a sessao cair, rode o script de novo que ele continua de onde parou.
Para recomecar do zero, `serve_chunks.py --reset` ou `POST /reset`.

## Por que um servidor local

O sandbox do `browser_run_code_unsafe` nao tem `require` nem `import`, logo nao
le disco. Servir por HTTP e busca-lo com `page.request.get` resolve isso sem
passar 120 mil caracteres pelo contexto do agente — e `page.request` nao esbarra
na CSP da pagina, ao contrario de um `fetch` de dentro dela.

## O que quebra quando a interface muda

`send_to_chat.js` depende de dois seletores da Inner AI, declarados no topo do
arquivo: `#messagebox-input` (o contenteditable) e `.messagebox-send-button`.
Se a Inner AI mudar o layout, e ali que conserta.

Detalhe nao obvio: `locator.fill()` estoura timeout num contenteditable deste
tamanho, mesmo tendo inserido o texto. Por isso a insercao usa
`document.execCommand('insertText')`, que dispara os eventos que o editor React
escuta. O script confere o tamanho inserido antes de enviar, para nunca mandar
uma parte truncada.

## Parametros

| Script | Opcao | Padrao |
|---|---|---|
| `split_vault.py` | `--vault` | `vault/` |
| | `--out` | `_build/vault-export/` |
| | `--max-chars` | `11000` |
| `serve_chunks.py` | `--dir` | `_build/vault-export/` |
| | `--port` | `8731` |
| | `--reset` | desligado |
| `send_to_chat.js` | `BATCH` (no topo do arquivo) | `8` |
