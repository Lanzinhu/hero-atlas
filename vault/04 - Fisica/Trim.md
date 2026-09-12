---
tags: [fisica, trim, marco-2]
atualizado: 2026-09-11
---

# Trim

## A formulacao

Sobre o ponto fixo `O`, com a gravidade no **mesmo referencial** dos bocais:

```
min  soma_i T_i

s.a. soma_i T_i * n_i,B                        = -m * R_BI * g_I
     soma_i r_i/O,B x (T_i * n_i,B)
       + r_C/O,B x (m * R_BI * g_I)            = 0
     T_i,min <= T_i <= T_i,max
```

O termo do peso sobre `O` e obrigatorio. Ver [[ADR-002 - Trim inclui momento do peso]].

**O trim de uma postura inclinada depende da atitude do tronco.**

## Contrato

```python
solve_trim(vehicle_state, scenario, trim_target, available_actuators) -> TrimSolution
```

Resolve equilibrio de **pose congelada e massa congelada**: `qdot = 0`, `qddot = 0`, `mdot_f = 0`,
cenario atmosferico constante.

## Duas viabilidades, nunca uma

Ver [[R-02 - Dois niveis de trim]].

```yaml
trim_status: feasible | infeasible

trim_capture_status:
  reachable_within_horizon: true | false
  horizon_s: ...
  limiting_actuators: [...]
```

## O que o trim alimenta

- empuxo minimo de pairado
- distribuicao de carga entre turbinas
- reservas vertical, lateral e de torque
- margem pos-falha
- **ponto de operacao inicial da alocacao incremental**

Ver [[Alocacao de controle]].

## Tres operacoes distintas

| Operacao | Finalidade |
|---|---|
| `solve_trim()` | equilibrio para uma pose, atitude e cenario |
| `allocate_incremental()` | pequenas correcoes ao redor do trim |
| `retrim()` | recalcular apos mudanca grande ou falha |

**Falha de motor nao e um incremento grande.** Ela altera a geometria de equilibrio e exige retrim.

## Ligacoes

[[Alocacao de controle]] · [[Forca requerida x capacidade de entrega]] ·
[[Marco 2 - Trim e autoridade]]
