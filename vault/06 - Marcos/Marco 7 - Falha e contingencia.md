---
tags: [marco]
marco: 7
prazo: 3 semanas
estado: aguardando
---

# Marco 7 - Falha e contingencia

## Pergunta

**Existe trim pos-falha, e o controlador consegue alcanca-lo a tempo?**

As duas metades sao perguntas diferentes. Ver [[R-02 - Dois niveis de trim]].

## Entregavel

- Injecao de falha, programada e detectada por limiar
- Deteccao, classificacao e reconfiguracao de atuadores
- `retrim` com verificacao de existencia
- Alvo de contingencia e transitorio ate ele
- **Regiao de captura**
- Campanha de sensibilidade condicionada

## Criterio de sucesso

Metricas mensuraveis por cenario:

| Metrica | Pergunta |
|---|---|
| Existencia de trim pos-falha | Ha equilibrio possivel? |
| Tempo de deteccao | Quando a reconfiguracao comeca? |
| Excursao antes do retrim | O que acontece no transiente? |
| Saturacao de atuadores | Ha forca disponivel durante a recuperacao? |
| Perda de altitude | Existe tempo para a contingencia? |
| Regiao de captura | O controlador alcanca o novo trim? |

## Sensibilidade condicionada, nao probabilidade

A campanha **nao** produz probabilidade de perda de controle. Produz **sensibilidade sob hipoteses
de distribuicao declaradas**, porque as distribuicoes de atraso, empuxo, massa, centro, vento, erro
de sensor e capacidade humana nao tem base empirica neste projeto.

O relatorio usa essa expressao literal e toda figura carrega as hipoteses na legenda.

## O contexto que torna isso serio

Perder 1 de 5 turbinas e menos 20 por cento de empuxo **mais** um momento assimetrico, com T/W que
ja era 1,1. E nao existe envelope de recuperacao: sem autorrotacao, sem planeio, e paraquedas
balistico exige 50 a 100 m enquanto o voo real acontece a 1 a 15 m.
Ver [[Estado da arte - trajes de voo]].

## Ligacoes

[[R-02 - Dois niveis de trim]] · [[Alocacao de controle]] · [[Trim]]
