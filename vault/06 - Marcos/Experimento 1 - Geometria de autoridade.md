---
tags: [experimento, geometria, marco-2]
atualizado: 2026-09-12
status: concluido
---

# Experimento 1 - Geometria de autoridade

> A pergunta nao e "qual traje construir". E **quais classes de geometria nao merecem dinamica**,
> porque nao fecham trim ou falham com deslocamento minimo de centro de massa.

Roda com `python tools/sweep_geometry.py`. Massa de 117 kg, 35 kgf por bocal, marcha lenta de 10
por cento.

⚠ Geometrias **plausiveis, nao medidas**. Pairado nivelado, pose e massa congeladas.

## Resultado: 9 de 11 arquiteturas eliminadas

| Arquitetura | n | Posto | Rolagem pura | Janela x | Janela y | Falhas |
|---|---|---|---|---|---|---|
| base 5 bocais | 5 | 4/6 | nao | 13,5 cm | 0 | 0/5 |
| altura escalonada | 5 | 4/6 | nao | 13,5 cm | 0 | 0/5 |
| envergadura escalonada | 5 | 4/6 | nao | 13,5 cm | 0 | 0/5 |
| inclinacao lateral escalonada | 5 | 4/6 | nao | 11,5 cm | 0 | 0/5 |
| com inclinacao longitudinal | 5 | 5/6 | nao | 9,5 cm | 0 | 0/5 |
| altura + longitudinal | 5 | 5/6 | nao | 10,5 cm | 0 | 0/5 |
| tres pares, so altura | 7 | 4/6 | nao | 20,5 cm | 0 | **5/7** |
| tres pares + longitudinal | 7 | 5/6 | nao | 11,0 cm | 0 | 2/7 |
| **3 pares, tudo escalonado** | 7 | 5/6 | **SIM** | 22,0 cm | 3,2 cm | 1/7 |
| **3 pares escalonados + longitudinal** | 7 | **6/6** | **SIM** | 10,5 cm | **21,6 cm** | 0/7 |
| dois pares + dois dorsais | 6 | 5/6 | nao | 10,5 cm | 0 | 0/6 |

## ⚠ O filtro decisivo: rolagem pura

Um centro de massa deslocado lateralmente exige **momento de rolagem sem forca lateral**.

Numa arquitetura de pares simetricos, isso vem dos graus de liberdade **antissimetricos**, que
precisam gerar tres grandezas: forca lateral, rolagem e guinada.

```
2 pares  ->  2 graus antissimetricos  ->  nao cobre 3 grandezas  ->  falha sempre
```

## ⚠ E contagem de pares NAO basta

**Tres pares diferindo so em altura continuam falhando.** As contribuicoes antissimetricas ficam
linearmente dependentes.

"Mais propulsores resolve" e falso. **Colunas mais diversas** resolve.

### ⚠ Correcao de uma afirmacao minha

Eu havia escrito que os pares precisam diferir em **envergadura, altura e inclinacao**, nos tres.
Testado, e **falso**:

| Variacao entre os tres pares | Posto | Rolagem pura |
|---|---|---|
| so altura | 4/6 | nao |
| so envergadura | 4/6 | nao |
| altura + envergadura | 4/6 | nao |
| **so inclinacao** | **5/6** | **SIM** |
| envergadura + inclinacao | 5/6 | SIM |
| altura + inclinacao | 5/6 | SIM |
| os tres | 5/6 | SIM |

Nesta familia, **diferenca de inclinacao sozinha ja basta**, e altura mais envergadura juntas nao
bastam.

E a condicao geral nao e nenhum parametro especifico: e **posto da matriz de alocacao**. Qualquer
geometria que gere colunas independentes serve, e a varredura testou uma familia so.

## ⚠ Posto nao e margem

| Variante | Rolagem pura | Menor valor singular |
|---|---|---|
| tres pares, so altura | nao | 0,1245 |
| tres pares, so inclinacao | **SIM** | **0,0306** |
| 3 pares, tudo escalonado | SIM | **0,0206** |

As que conseguem rolagem pura tem a direcao mais fraca **cinco a seis vezes menor**. A direcao
existe e exige redistribuicao enorme de empuxo para ser usada.

Alcancar nao e ter autoridade.

## ⚠ Artefato do objetivo, corrigido

A primeira versao desta varredura reportava **folga zero** em quase toda arquitetura. Era artefato:
o solver minimizava empuxo total, o que encosta nos limites **por construcao**.

Com trim de margem maxima, a folga real aparece, e custa menos de 1 por cento de empuxo a mais:

| Arquitetura | Folga real |
|---|---|
| cinco bocais | 5,5 a 9,2 kgf |
| sete bocais | 14,5 a 15,6 kgf |

## Um conflito de projeto aparece

| Arquitetura | Autoridade | Redundancia |
|---|---|---|
| tres pares, so altura | posto 4, sem rolagem pura | **5 de 7 perdas toleradas** |
| 3 pares escalonados + longitudinal | **posto 6, janela lateral de 21,6 cm** | **0 de 7** |

A geometria que maximiza autoridade e a que menos tolera falha, e vice-versa. Isso nao e
coincidencia: escalonar tudo torna cada propulsor **unico** no que contribui, e perder um unico
remove uma contribuicao insubstituivel.

Esta tensao ainda **nao foi explorada**. Resolve-la e questao de projeto, nao de simulacao, e
provavelmente exige mais propulsores do que sete.

## O que sobrevive para a dinamica

Duas de onze. E nenhuma das duas tolera falha de forma aceitavel.

## Ligacoes

[[Marco 2 - Trim e autoridade]] · [[Marco 3 - Dinamica]] · [[ADR-007 - Deck de propulsao instalada]]
