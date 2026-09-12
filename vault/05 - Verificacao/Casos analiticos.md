---
tags: [verificacao, testes]
atualizado: 2026-09-11
---

# Casos analiticos e cruzamento

## Os casos com resposta fechada

| Caso | O que pega |
|---|---|
| Queda livre | integracao translacional |
| Pairado em equilibrio | trim e sinal de forca |
| Binario puro | forca resultante nula, torque exato |
| Norma do quaternion | deriva de normalizacao |
| Ordem de convergencia | implementacao do integrador |
| **Efeito Dzhanibekov** | **erro de sinal na equacao de Euler e na propagacao do quaternion** |
| **Equivariancia sob rotacao do referencial** | **confusao entre matriz de rotacao e sua transposta** |
| **Agregacao de massa** | **rotacao de tensor e eixos paralelos** |

Os tres em negrito sao os decisivos, porque pegam erros de sinal e de convencao que produzem
trajetorias suaves e completamente falsas.

### Efeito Dzhanibekov

Corpo livre de torque com tres momentos principais distintos. O eixo intermediario e instavel e o
corpo capota periodicamente. E o teste mais sensivel a erro de sinal que existe para corpo rigido.

### Equivariancia sob rotacao

Rodar a configuracao inteira por uma rotacao arbitraria `R`. A trajetoria resultante tem que ser a
original rodada por `R`. Pega erro de `C_nb` contra `C_bn`.

### Agregacao de massa

Conjuntos com solucao fechada:

- **Haltere**: duas massas pontuais em mais e menos L/2 no eixo x, sobre o centro, da
  `diag(0, m L^2 / 2, m L^2 / 2)`
- **Quatro massas nos cantos de um quadrado** de lado `a` no plano xy, sobre o centro, da
  `diag(m a^2, m a^2, 2 m a^2)` com produtos nulos
- **Barra montada a partir de duas meias-barras**: cada metade com massa M/2, comprimento L/2,
  centrada em mais e menos L/4. O agregado tem que dar exatamente `M L^2 / 12`, a inercia da barra
  inteira. Exercita rotacao, translacao e soma **juntas**, com resultado conhecido
- **Componente rotacionado**: a mesma meia-barra com inercia definida em eixos proprios girados 90
  graus, com matriz de orientacao compensando. O resultado tem que ser identico. **Pega troca entre
  `R` e a transposta de `R`**

## Cruzamento com JSBSim, graduado

O JSBSim e **oraculo de regressao para subconjuntos de corpo rigido bem definidos**, nao validacao
integral do traje.

| Caso | Criterio |
|---|---|
| Queda livre sem rotacao | coincidencia quase exata |
| Torque constante em corpo rigido | orientacao e taxa angular comparaveis |
| Empuxo vertical constante | aceleracao e altitude comparaveis |
| Pairado em malha aberta | erro limitado e estavel |
| Malha fechada | metricas RMS e de resposta, **nao trajetoria ponto a ponto** |

Exigir coincidencia de uma parte em dez mil ao longo de 30 s em malha fechada e rigor no lugar
errado, e produziria um teste instavel que alguem desliga. Diferencas em integrador, passo,
normalizacao, interpolacao e ordem de avaliacao crescem legitimamente.

### O que continua exclusivo do nosso nucleo

Massa movel por bracos, bocais cuja geometria depende do piloto, propulsao com atraso nao linear,
marcha lenta minima, alocacao incremental, reingestao parametrizada, falha assimetrica e atrasos
neuromusculares.

Tratar o cruzamento como selo de validacao da arquitetura completa produz **falsa sensacao de
independencia**.

## A regra de ouro

> Nenhum resultado de viabilidade sai sem a tabela de referencias passando no mesmo commit, e
> nenhuma figura de relatorio e gerada fora do comando oficial.

## Ligacoes

[[Tres classes de teste]] · [[Propriedades de massa]] · [[Nivel de evidencia]]
