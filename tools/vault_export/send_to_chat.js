// Cola as partes do vault, uma a uma, num chat web aberto no browser.
//
// Rodar pelo Playwright MCP (browser_run_code_unsafe, parametro filename), com
// serve_chunks.py no ar. O script nao guarda estado: pergunta ao servidor qual e
// a proxima parte pendente e marca como enviada depois de cada resposta, entao
// pode ser chamado varias vezes ate acabar.
//
// Ajuste BATCH conforme o timeout da chamada: cada parte leva o tempo da
// resposta do modelo, tipicamente 5 a 10 s para um "ok N/13".
//
// Seletores validados na Inner AI (set/2026). Se a interface mudar, e aqui que quebra.

async (page) => {
  const BATCH = 9;
  const BASE = 'http://127.0.0.1:8731';
  const INPUT = '#messagebox-input';
  const SEND_BUTTON = '#messagebox-button-send';
  // Icone que substitui o botao de enviar enquanto o modelo responde.
  const BUSY = 'img.animate__heartBeat';

  const sleep = (ms) => page.waitForTimeout(ms);
  const bodyLen = () => page.evaluate(() => document.body.innerText.length);
  const log = [];
  const generating = () =>
    page.evaluate(
      ({ busy, send }) =>
        !!document.querySelector(busy) || !document.querySelector(send),
      { busy: BUSY, send: SEND_BUTTON }
    );

  for (let k = 0; k < BATCH; k++) {
    const next = await (await page.request.get(BASE + '/next')).json();
    if (next.n === null) {
      log.push('nada pendente: todas as ' + next.total + ' partes ja foram enviadas');
      break;
    }

    const { n, total } = next;
    const resp = await page.request.get(BASE + '/' + next.name);
    if (!resp.ok()) {
      log.push('FALHA ao buscar ' + next.name + ' (' + resp.status() + ')');
      break;
    }

    const header =
      n < total
        ? 'PARTE ' + n + '/' + total + ' — não avalie ainda, responda só "ok ' + n + '/' + total + '".'
        : 'PARTE ' + n + '/' + total + ' — última parte.';
    const text = header + '\n\n' + (await resp.text());

    const before = await bodyLen();

    // Insercao nativa. fill() do Playwright estoura timeout revalidando um
    // contenteditable deste tamanho; execCommand dispara beforeinput/input,
    // que e o que o editor React escuta.
    const inserted = await page.evaluate(
      ({ sel, t }) => {
        const el = document.querySelector(sel);
        if (!el) return -1;
        el.focus();
        const selection = window.getSelection();
        selection.removeAllRanges();
        const range = document.createRange();
        range.selectNodeContents(el);
        selection.addRange(range);
        document.execCommand('insertText', false, t);
        return el.innerText.length;
      },
      { sel: INPUT, t: text }
    );
    await sleep(200);

    // Tolerancia porque o editor normaliza quebras de linha.
    if (inserted < text.length * 0.95) {
      log.push('ABORTADO na parte ' + n + ': inseriu ' + inserted + ' de ' + text.length + ' chars');
      break;
    }

    let armed = false;
    for (let i = 0; i < 20 && !armed; i++) {
      armed = await page.evaluate((sel) => {
        const b = document.querySelector(sel);
        return !!b && !b.disabled && !String(b.className).includes('disabled');
      }, SEND_BUTTON);
      if (!armed) await sleep(300);
    }

    await page.keyboard.press('Enter');
    await sleep(600);

    const enviou = await page.evaluate(
      (sel) => document.querySelector(sel).innerText.trim().length === 0,
      INPUT
    );
    if (!enviou) {
      log.push('ABORTADO: campo nao esvaziou na parte ' + n);
      break;
    }

    // Marcar aqui, e nao depois de esperar a resposta: a mensagem ja partiu, e
    // uma interrupcao entre o envio e a resposta faria a parte ser mandada de
    // novo na proxima execucao. Repetir conteudo e pior que registrar cedo.
    await page.request.post(BASE + '/sent/' + n);

    // Enquanto gera, a Inner AI troca o botao de enviar por um icone pulsando.
    // Esse e o estado real da interface: esperar por ele e imediato, ao contrario
    // de heuristica sobre o texto da pagina parar de crescer.
    let waited = 0;
    while (waited < 15000 && !(await generating())) {
      await sleep(150);
      waited += 150;
    }
    const comecou = waited < 15000;

    while (waited < 300000 && (await generating())) {
      await sleep(250);
      waited += 250;
    }

    const cresceu = (await bodyLen()) > before + 200;
    if (!cresceu) {
      log.push('ABORTADO: sem resposta para a parte ' + n + ' apos ' + (waited / 1000).toFixed(1) + 's');
      break;
    }

    log.push(
      'parte ' + n + '/' + total + ': ' + text.length + ' chars, ' +
      (waited / 1000).toFixed(1) + 's' + (comecou ? '' : ' [nao detectei inicio da geracao]')
    );
  }

  const tail = await page.evaluate(() => document.body.innerText.slice(-220));
  return { log, tail };
}
