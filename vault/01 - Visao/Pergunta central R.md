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

## ⚠ R nao se reduz a atraso contra empuxo por peso

A projecao de duas variaveis, `tau` contra `T/W`, e **grafico de comunicacao, nao criterio**.

O motivo e fisico. `T/W` mede capacidade translacional vertical, mas controle de atitude depende de
aceleracao angular disponivel:

```
alpha_max = M_max / I        com  M_max ~ r_efetivo * Delta_T_max
```

Duas arquiteturas com o **mesmo** `T/W` e o **mesmo** `tau` podem ter resultados opostos se
diferirem em braco efetivo, tensor de inercia, posicao do centro, empuxo minimo, margem diferencial
em torno do trim, geometria dos vetores, ou numero de atuadores.

Nao foi encontrada fronteira publicada universal do tipo `tau` contra `T/W` para veiculos
comparaveis, e ha razao fisica para desconfiar que exista.

O criterio interno usa grupos adimensionais:

```
tau_atuador * omega_c        T_d * omega_c        M_max / (I * omega_c^2)

Delta_T_max / T_trim         lambda_T = T_disponivel / T_requerido
```

O terceiro grupo tem dimensao de angulo: e **quanta excursao de atitude o atuador consegue deter na
banda `omega_c`**.

O conjunto minimo a varrer:

```
R_minima = { ( tau , T_d , Tdot_max , lambda_T , M_max/I , cond(W) , r_C/O ) :
             criterios operacionais satisfeitos }
```

onde `cond(W)` e o condicionamento da matriz de alocacao, ou da sua versao dinamica.

## Como R e explorada

Grade cartesiana nao serve: cinco valores em sete dimensoes ja sao **78.125** execucoes, antes de
cenarios, perturbacoes, falhas e arquiteturas de controle.
Ver [[ADR-006 - Exploracao de R]] e [[R-03 - R tem parametros finitos]].

E a amostragem nao pode ser independente entre parametros de propulsao, senao a **cauda otimista**
passa. Ver [[ADR-007 - Deck de propulsao instalada]].

## Ligacoes

[[Numeros decisivos]] · [[Estavel definido operacionalmente]] · [[Modelo de piloto]]
