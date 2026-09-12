---
tags: [adr, trim]
adr: 002
estado: aceita
data: 2026-09-11
---

# ADR-002 - Trim sobre `O` inclui o momento do peso

## Contexto

Uma revisao anterior escrevia "momento de equilibrio no ponto de referencia", o que era vago.
A gravidade atua **no centro de massa**, logo sobre um ponto `O` diferente do centro ela produz
momento. Omitir esse termo faz o trim de qualquer postura assimetrica sair errado.

## Decisao

```
soma_i T_i * n_i,B  +  m * R_BI * g_I = 0

soma_i r_i/O,B x (T_i * n_i,B)  +  r_C/O,B x (m * R_BI * g_I) = 0

T_i,min <= T_i <= T_i,max
```

**O trim de uma postura inclinada depende da atitude do tronco.** Nao e formalismo.

Relevante sempre que:

- o piloto levanta um braco
- uma turbina se desloca para fora
- o tanque esta fora do eixo
- combustivel e queimado
- o tronco esta inclinado
- uma falha obriga postura assimetrica

## O contrato de solve_trim

Resolve **equilibrio de pose congelada e massa congelada**:

```
qdot = 0,  qddot = 0,  mdot_f = 0,  cenario atmosferico constante
```

Um `solve_dynamic_trim()` para postura deliberadamente variavel e problema posterior.

O tipo de trim e parametrizado, porque ha varios problemas com o mesmo nome:

| Tipo | Condicao |
|---|---|
| Pairado nivelado | velocidade e taxa angular nulas |
| Pairado inclinado | atitude fixa nao nula, aceleracao nula |
| Translacao uniforme | velocidade constante |
| Curva coordenada | aceleracao centripeta definida |
| Descida controlada | velocidade vertical constante |
| Pos-falha | motor indisponivel, equilibrio se existir |

```python
solve_trim(vehicle_state, scenario, trim_target, available_actuators) -> TrimSolution
```

O [[Marco 2 - Trim e autoridade]] implementa apenas o pairado nivelado, mas com o tipo ja
parametrizado.

## Ligacoes

[[Trim]] · [[R-02 - Dois niveis de trim]] · [[ADR-001 - Ponto de referencia e forma da dinamica]]
