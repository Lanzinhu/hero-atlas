---
name: chat-externo
description: Conversar com um chat de IA no browser (Inner AI, ChatGPT) para submeter o vault ou trechos do projeto a avaliacao externa. Use quando o pedido for mandar o vault, uma nota ou uma pergunta para o GPT, continuar uma conversa ja aberta no navegador, ou ler o que o outro modelo respondeu.
---

# Conversar com um chat externo pelo browser

Controla um chat web ja logado, pelo Playwright MCP, para submeter material do
projeto a avaliacao de outro modelo e trazer a resposta de volta.

## Antes de comecar

O Playwright MCP roda um Chrome com perfil proprio e persistente em
`C:\Users\alanl\.claude\playwright-profile`. O login fica salvo nesse perfil.
Nao da para reaproveitar a sessao do Chrome pessoal do usuario: desde o Chrome
136, `--remote-debugging-port` e bloqueado no perfil padrao.

Se cair na tela de login, **peca ao usuario que logue na janela aberta**. Nunca
digite credenciais.

## Seletores da Inner AI

Validados em setembro de 2026. Se a interface mudar, e o primeiro lugar a olhar.

| O que | Seletor |
|---|---|
| Campo de mensagem (contenteditable) | `#messagebox-input` |
| Botao de enviar | `#messagebox-button-send` |
| Icone que aparece enquanto o modelo responde | `img.animate__heartBeat` |

## Tres armadilhas que ja custaram tempo

**1. Nao use `locator.fill()` em texto longo.** Ele insere o texto e depois
estoura timeout revalidando o contenteditable — parece falha, mas o texto entrou.
Insira com `execCommand`, que dispara os eventos que o editor React escuta:

```js
await page.evaluate((t) => {
  const el = document.querySelector('#messagebox-input');
  el.focus();
  const sel = window.getSelection();
  sel.removeAllRanges();
  const r = document.createRange();
  r.selectNodeContents(el);
  sel.addRange(r);
  document.execCommand('insertText', false, t);
  return el.innerText.length;
}, texto);
```

Confira o tamanho inserido antes de mandar. Enviar meia mensagem e pior que falhar.

**2. Para saber se terminou de responder, olhe o DOM, nao o texto.** Enquanto
gera, o botao de enviar some e entra `img.animate__heartBeat`. Esperar "o texto
parar de crescer" funciona, mas desperdica ~9 s por mensagem e erra quando o
modelo pensa em silencio.

**3. Interromper no Claude Code nao mata o script no servidor Playwright.** Uma
execucao interrompida continua enviando mensagens em background. Antes de
reenviar qualquer coisa, **verifique o que a pagina ja recebeu** — o estado real
esta no DOM, nao no seu registro:

```js
[...document.body.innerText.matchAll(/## ARQUIVO: (.+)/g)].map((m) => m[1].trim())
```

## Mandar o vault inteiro

Chat web nao aceita 120 mil caracteres numa mensagem. Use `tools/vault_export/`,
que fatia o vault e envia parte por parte de forma retomavel. O README de la tem
o fluxo completo:

```bash
python tools/vault_export/split_vault.py
python tools/vault_export/serve_chunks.py     # deixa rodando
# depois: browser_run_code_unsafe com filename=tools/vault_export/send_to_chat.js
```

O caminho passado para `browser_run_code_unsafe` precisa comecar com `c:`
minusculo — a checagem de raiz permitida compara a string do drive.

## Como conduzir a conversa

Preferencia explicita do usuario, registrada em 12/09/2026:

- **Nao limite o outro modelo.** Nada de "nao pesquise na web" ou de formato
  rigido demais. Deixe ele buscar onde quiser.
- **Converse de igual para igual.** O objetivo nao e extrair um laudo: e discutir.
  Diga onde concorda, onde discorda e por que, e peca que ele rebata.
- Peca que cite a nota pelo nome ao apontar um problema, para a critica ser
  rastreavel de volta ao vault.

## Trazer a resposta de volta

Extraia o texto da pagina cortando a partir do fim do seu proprio pedido, e salve
em arquivo antes de analisar — as respostas passam de 30 mil caracteres:

```js
const t = document.body.innerText;
const i = t.lastIndexOf(ULTIMA_LINHA_DO_MEU_PEDIDO);
return { resposta: t.slice(i).trim() };
```

`browser_evaluate` com `filename` salva o resultado, mas **grava na raiz do
projeto**. Mova para `_build/` em seguida: a raiz fica limpa e `_build/` ja esta
no `.gitignore`.
