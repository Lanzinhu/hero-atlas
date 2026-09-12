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

Achado que corrige a intuicao obvia. **Tres pares diferindo so em altura continuam falhando**, com
posto antissimetrico 2 de 3. As contribuicoes ficam linearmente dependentes.

Os pares precisam diferir em **envergadura, altura e inclinacao** para que as tres contribuicoes
sejam independentes.

"Mais propulsores resolve" e falso. **Propulsores mais diversos** resolve.

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
