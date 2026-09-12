---
tags: [marco]
marco: 4
prazo: 2 semanas
estado: aguardando
---

# Marco 4 - Pairado

## Pergunta

**Paira? E quando nao paira, por que?**

A segunda metade da pergunta e a que produz valor.

## Entregavel

- PID em cascata, com domino temporal declarado
- Alocacao incremental por programacao quadratica, usando efetividade prevista `G_T`
- Sensores com ruido, bias e atraso
- **Telemetria de resduo do alocador**, com os quatro modos de falha distinguidos

## ⚠ Criterio de sucesso: fronteira, nao cenario

O criterio antigo era "60 s de pairado com o tau nominal". Isso e **demonstracao de cenario, nao
medicao de margem**, num projeto que afirma estudar margens estreitas. Pairar uma vez com o valor
nominal nao diz nada sobre onde a coisa para de funcionar.

O marco 4 produz a **primeira fronteira de estabilidade da malha fechada**, ainda que em modelo
reduzido:

```yaml
primary_success_criterion:
  name: closed_loop_stability_boundary
  output:
    - critical_actuator_delay_s
    - stability_boundary_over_thrust_margin
    - allocator_residual_near_boundary
    - active_constraint_at_failure
    - dominant_failure_mode
  evaluated_over:
    - familia declarada de perturbacao
    - pose de braco declarada
    - estado de massa e centro declarado
    - familia de incerteza do deck de atuador
```

⚠ E o resultado ideal **nao e um `tau_critico` unico**. E uma superficie condicionada:

```
tau_crit = f( lambda_T , Tdot_max , eta_inst , r_C/O , q_pose )
```

Os 60 s viram o que deveriam ser desde o inicio: teste de nao regressao, nao medalha.

```yaml
secondary_regression_case:
  duration_s: 60
  purpose: regressao deterministica, nao certificacao de viabilidade
```

Quando falhar, o registro diz **qual eixo faltou e qual restricao estava ativa**:

```yaml
allocator_event:
  type: wrench_unattainable
  normalized_residual: 0.41
  active_constraints: [engine_2_thrust_max, engine_4_ramp_up_max]
```

## ⚠ Ordem de corte deste marco

Produzir fronteira em vez de cenario **multiplica execucoes** num marco orcado em duas semanas.
Por isso a ordem de corte vem declarada antes de comecar:

```yaml
scope_cut_order:
  1: fronteira so sobre tau, com lambda_T e pose fixos
  2: adiar a superficie completa tau_crit(lambda_T, ...) para o marco 5
  3: uma familia de acoplamento so, a totalmente acoplada, que e a conservadora
  4: reduzir a familia de perturbacao a rajada unica padronizada
```

## Decisao pendente deste marco

Metodo de `G_T`: diferenca finita local ou modelo analitico.
Ver [[ADR-003 - Efetividade dinamica no alocador]].

## Ligacoes

[[Alocacao de controle]] · [[Estavel definido operacionalmente]] · [[Telemetria]]
