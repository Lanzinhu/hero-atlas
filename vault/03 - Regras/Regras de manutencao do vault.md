---
tags: [regra, processo, vault]
estado: ativa
---

# Regras de manutencao do vault

> Um vault que apodrece e pior que nenhum vault, porque da confianca falsa.

## As quatro regras

### 1. Uma nota, uma ideia

Se a nota precisa de dois titulos de nivel um, sao duas notas. Nota longa nao e consultada, e
conhecimento nao consultado nao existe.

### 2. Diario e temporal, vault e permanente

O diario registra **o que aconteceu naquele dia**. O vault permanente registra **o que e verdade**.

Regra de promocao: se uma anotacao do diario for consultada duas vezes, promova para nota permanente
e deixe o link no lugar.

### 3. Toda nota de fisica declara a sua aproximacao

Nenhuma equacao entra sem dizer o que ela **nao** modela. O projeto inteiro foi salvo cinco vezes
por essa disciplina. Ver [[Historico de revisoes]].

### 4. Numero sem procedencia e ficcao

Nenhum numero vira teste de regressao antes de ter copia arquivada com hash.
Ver [[Regras de procedencia]] e [[Nivel de evidencia]].

## Ritmo de atualizacao

| Quando | O que atualizar |
|---|---|
| Todo dia de trabalho | Nota diaria, com as cinco perguntas |
| Ao tomar decisao arquitetural | Novo ADR em `02 - Decisoes`, mais linha em [[Indice de decisoes]] |
| Ao terminar um marco | Estado em [[Indice de marcos]], e criterio de sucesso marcado |
| Ao arquivar uma fonte | Nota de fonte com hash, mais linha em [[Nivel de evidencia]] |
| Ao descobrir que uma nota esta errada | **Corrigir a nota**, e registrar no diario o que estava errado |
| Toda semana | [[Decisoes em aberto]] e o campo `atualizado` do [[MOC - Hero Atlas]] |

## Nota errada se corrige, nao se acumula

Se uma nota permanente estiver errada, **edite a nota**. Nao adicione um paragrafo "na verdade e
assim". O historico de correcoes vive no git e em [[Historico de revisoes]], nao no corpo da nota.

A excecao e quando o erro **em si** e instrutivo: ai ele vira uma secao "o erro que esta nota evita",
como em [[Propriedades de massa]] e [[Atmosfera]].

## Convencao de nome

- Notas permanentes: substantivo descritivo, sem data
- ADR: `ADR-NNN - Decisao em forma de frase`
- Regras: `R-NN - Regra em forma de afirmacao`
- Marcos: `Marco N - Nome`
- Diario: `AAAA-MM-DD`

## Tags minimas

`moc`, `indice`, `adr`, `regra`, `fisica`, `verificacao`, `marco`, `diario`, `dados`, `risco`.

Tag nao substitui link. Use links para relacao, tags para tipo.

## Ligacoes

[[MOC - Hero Atlas]] · [[Indice do diario]]

Templates: [[Template diario]] · [[Template ADR]] · [[Template fonte]] · [[Template marco]]
