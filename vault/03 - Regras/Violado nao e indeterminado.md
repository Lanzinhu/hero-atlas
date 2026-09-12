---
tags: [regra, epistemologia, nucleo]
estado: ativa
atualizado: 2026-09-12
---

# Violado nao e indeterminado

> Fundir violado com indeterminado transforma lacuna de evidencia em veredito negativo.
> Fundir indeterminado com satisfeito transforma lacuna de evidencia em aprovacao.
>
> **Os dois erros existem, sao simetricos, e os dois ja apareceram neste projeto.**

## O vocabulario, um so para todo o projeto

| Veredito | O que o modelo diz |
|---|---|
| `SATISFIED` | **sim**, e isso e demonstravel |
| `VIOLATED` | **nao**, e isso e demonstravel |
| `INDETERMINATE` | **nao da para concluir** |

## Rejeicao operacional nao e conclusao cientifica

```
candidato_aceito        = veredito e SATISFIED
candidato_rejeitado     = veredito em {VIOLATED, INDETERMINATE}
elegivel_como_conclusao = veredito em {SATISFIED, VIOLATED}
```

A rejeicao pode tratar os dois casos igual: nao demonstrado nao e aprovado. **O dado e o relatorio,
nunca.** Dizer que um conceito falhou quando o que houve foi falta de parametro e afirmar sobre
fisica o que so se sabe sobre evidencia.

## Onde isso vale

| Contexto | Caso indeterminado |
|---|---|
| Requisito de atuador | parametro ausente no candidato |
| Comparacao com referencia | incerteza nao declarada de qualquer lado |
| Construcao de requisito | contexto ausente: nem chega a existir |

As duas primeiras sao vereditos. A terceira e recusada na construcao, porque condicao sem o
contexto em que foi obtida nao e interpretavel.

## Historico

O defeito apareceu **duas vezes**, e a segunda foi pior porque foi deixada para tras na primeira
correcao: `analysis.requirements` foi consertado, e `provenance` ficou com a mesma falha por mais
uma rodada. A avaliacao externa pegou.

Por isso o vocabulario agora vive num modulo unico, `verdict.py`, em vez de ser redefinido onde
aparece.

## Ligacoes

[[Regras de procedencia]] · [[ADR-007 - Deck de propulsao instalada]] · [[Nivel de evidencia]]
