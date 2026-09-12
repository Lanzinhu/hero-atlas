---
tags: [visao, nucleo]
atualizado: 2026-09-11
---

# A pergunta central: a regiao R

```
R = { (tau_atuador, tau_humano, K_humano, Tdot_max, q_bracos, m, r_cg) :
      estavel sobre o envelope de cenarios declarado }
```

Em portugues: **para quais combinacoes de atraso de propulsao, atraso e ganho humanos, taxa maxima
de empuxo, postura de bracos, massa e centro de gravidade o modelo mantem estabilidade robusta?**

E, tao importante quanto: **quais variaveis encolhem essa regiao ate ela desaparecer?**

## Por que essa formulacao e nao outra

"Da para construir um Homem de Ferro" e pergunta ampla demais e induz conclusao cinematografica.
Um simulador nao certifica uma maquina real. Ele delimita regioes e nomeia as barreiras.

## O que conta como sucesso

Descobrir que a regiao e estreita ou vazia **e sucesso**. Se o estudo mostrar que:

- a geometria das maos reduz demais a autoridade de guinada
- a taxa de aceleracao da turbina e lenta demais
- a marcha lenta minima destroi a alocacao
- o movimento dos bracos introduz acoplamento intoleravel
- a margem cai a zero apos uma falha

entao o projeto encontrou a barreira real antes de alguem gastar dinheiro, combustivel ou
sobrancelhas.

## Como R e explorada

Grade cartesiana nao serve: cinco valores em sete dimensoes ja sao **78.125** execucoes, antes de
cenarios, perturbacoes, falhas e arquiteturas de controle.
Ver [[ADR-006 - Exploracao de R]] e [[R-03 - R tem parametros finitos]].

## Ligacoes

[[Numeros decisivos]] · [[Estavel definido operacionalmente]] · [[Modelo de piloto]]
