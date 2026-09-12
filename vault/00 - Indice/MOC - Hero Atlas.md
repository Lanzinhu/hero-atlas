---
tags: [moc, indice]
atualizado: 2026-09-11
---

# Hero Atlas - Mapa central

> Laboratorio virtual para descobrir quais limites fisicos e de controle tornam um traje de
> propulsao pessoal controlavel, marginal ou inevitavelmente instavel.

**Nao e** "simular um Homem de Ferro". O entregavel e o simulador e o estudo de viabilidade.
Sem hardware. Custo zero. Python.

## Estado atual

- Plano: **revisao 7, fechada para implementacao**
- Fase: marcos 0, 1 e 2 **entregues**. Proximo: [[Marco 3 - Dinamica]]
- Decisoes bloqueando: nenhuma. Ver [[Decisoes em aberto]]

## Por onde entrar

| Se voce quer | Va para |
|---|---|
| Entender o objetivo | [[Pergunta central R]] |
| Saber o que decide viabilidade | [[Numeros decisivos]] |
| Ver o que ja foi decidido e por que | [[Indice de decisoes]] |
| Ver as regras que nao se negocia | [[Indice de regras]] |
| Entender a fisica implementada | [[Propriedades de massa]] · [[Dinamica 6-DOF]] · [[Propulsao e atraso]] |
| Saber o que testar | [[Tres classes de teste]] |
| Ver o cronograma | [[Indice de marcos]] |
| Consultar dados de referencia | [[Estado da arte - trajes de voo]] |
| Ver o registro diario | [[Indice do diario]] |

## Estrutura do vault

- `01 - Visao` - por que o projeto existe e o que ele responde
- `02 - Decisoes` - ADRs, com motivo e consequencia
- `03 - Regras` - invariantes de projeto, violacao quebra o build
- `04 - Fisica` - equacoes implementadas e aproximacoes declaradas
- `05 - Verificacao` - como saber que o simulador nao esta mentindo
- `06 - Marcos` - cronograma e criterio de sucesso de cada etapa
- `07 - Diario` - registro diario, uma nota por dia
- `08 - Dados` - procedencia, fontes arquivadas, numeros de referencia
- `99 - Templates` - modelos de nota

## Os tres riscos

1. **Nao existe deck de propulsao instalada.** Autoridade estatica, resposta transitoria, consumo e
   perdas de interacao estao separados e sem correlacao declarada, e sete dos oito grupos de
   parametro nao tem dado. Ver [[ADR-007 - Deck de propulsao instalada]].
2. **Um simulador pode concordar consigo mesmo e estar errado.** Ver [[Tres classes de teste]].
3. **Paralisia de analise.** Sete revisoes de plano com pasta vazia. Ver [[Indice de marcos]].

E um quarto, epistemologico: **a familia parametrica nao validada pode ganhar aparencia de medicao**
por meio de graficos precisos e fronteiras suaves. Mitigado estruturalmente: `model_status.py`
recusa emitir saida condicional sem marca.
