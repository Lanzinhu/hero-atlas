---
tags: [adr, alocacao, controle]
adr: 003
estado: aceita
data: 2026-09-11
---

# ADR-003 - O alocador usa efetividade dinamica prevista, nao comando como empuxo

## Contexto

Uma revisao anterior separou as camadas de comando e de fisica, mas o problema quadratico ainda
tratava `delta_w = W * delta_T_cmd`, ou seja, mudanca de comando como mudanca **imediata** de empuxo.

**A turbina lenta e a razao de este projeto existir e nao pode desaparecer dentro do alocador.**

A cadeia real e:

```
u  ->  T_ss(u)  ->  T(t)  ->  F(t)  ->  w(t)
```

## Decisao

O alocador aloca **comandos**, usando a efetividade prevista no horizonte de controle `Ha`:

```
G_T = d T_{k+Ha} / d u_k        avaliado no estado atual

delta_w_{k+Ha} = W_T * G_T * delta_u_k

min_du   || W_T * G_T * du - delta_w_desejado ||^2_Q  +  || du ||^2_R
s.a.     u_min <= u_k + du <= u_max
         |du| <= du_max_ECU
```

A equacao diferencial da turbina continua sendo a **unica autoridade** sobre `T_real(t)`.
O alocador nao promete empuxo instantaneo.

## G_T nao e ganho fixo de catalogo

Depende de empuxo atual, comando atual, atraso da ECU, constante de tempo local, limite de rampa,
horizonte `Ha`, disponibilidade do motor e cenario atmosferico ativo.

No [[Marco 4 - Pairado]] uma aproximacao local por diferenca finita em torno do estado atual e
aceitavel, **desde que registrada como aproximacao numerica local**:

```
G_T,i = [ T_i(t+Ha ; u_i + eps) - T_i(t+Ha ; u_i) ] / eps
```

## Camadas, sem mistura

| Elemento | Onde e modelado |
|---|---|
| Limite de mudanca de comando da ECU | problema quadratico, camada discreta |
| Atraso de transporte da ECU | fila discreta |
| Resposta fisica da turbina | equacao diferencial continua |
| Limite fisico de taxa de empuxo | equacao diferencial continua |
| Empuxo real aplicado ao corpo | dinamica rigida |

## Ligacoes

[[Alocacao de controle]] · [[ADR-004 - Margem estatica e dinamica]] · [[Propulsao e atraso]]
