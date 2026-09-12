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

## Congelavel nao e o mesmo que aceito

Um campo estava fazendo dois trabalhos. Congelar uma comparacao conclusiva e uma coisa; tratar o
valor do modelo como concordante com a referencia e outra.

```
eligible_for_regression  =>  comparacao feita  e  status != INDETERMINATE
accepted_as_benchmark    =>  status == SATISFIED
accepted_as_benchmark    =>  eligible_for_regression
```

Um resultado `VIOLATED` **pode e deve** virar teste que confirma a rejeicao: congelar uma
discordancia conhecida protege contra regressao silenciosa. Mas nao e benchmark aceito, e chamar de
elegivel sem qualificar deixava a ambiguidade viva.

## Congelar exige carregar o contexto junto

Congelar preserva a discrepancia. **Sem o contexto, perde a razao de ela existir.**

Daqui a seis meses ninguem sabe se aquele numero diferente e defeito tolerado, limitacao conhecida
do modelo, ou erro da referencia. Por isso `FrozenComparison` exige, todos obrigatorios:

| Campo | Por que |
|---|---|
| Revisao da fonte | a referencia pode ter mudado |
| Hash da copia arquivada | prova de qual texto foi comparado |
| Versao do modelo | o lado de ca tambem evolui |
| Contexto de aplicabilidade | a comparacao vale em que condicao |
| Incerteza utilizada | qual orcamento foi aplicado |
| Data do congelamento | quando a decisao foi tomada |
| **Justificativa** | por que e teste, e nao bloqueio |

A justificativa e **obrigatoria quando o resultado e violado**, e opcional quando e concordancia.
Congelar indeterminado e recusado.

## Historico

O defeito apareceu **duas vezes**, e a segunda foi pior porque foi deixada para tras na primeira
correcao: `analysis.requirements` foi consertado, e `provenance` ficou com a mesma falha por mais
uma rodada. A avaliacao externa pegou.

Por isso o vocabulario agora vive num modulo unico, `verdict.py`, em vez de ser redefinido onde
aparece.

## Ligacoes

[[Regras de procedencia]] · [[ADR-007 - Deck de propulsao instalada]] · [[Nivel de evidencia]]
