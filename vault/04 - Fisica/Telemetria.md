---
tags: [implementacao, telemetria]
atualizado: 2026-09-11
---

# Telemetria

> Transformar o simulador de um sistema que informa "nao conseguiu" num instrumento que explica
> **o que foi pedido, o que foi entregue, qual eixo faltou e qual limite estava ativo**.

## Registro de execucao

Cada execucao grava `runs/<ISO8601>_<hash_git_curto>/` com:

- configuracao resolvida, com todos os valores apos conversao de unidade
- log em Parquet
- `metrics.json`
- `env.json` com versoes das bibliotecas

Reprodutibilidade e requisito, nao luxo.

## Evento de alocacao

O registro mais importante do projeto:

```yaml
allocator_event:
  type: wrench_unattainable        # | allocator_infeasible | solver_failure | constraint_violation
  time_s: 12.475
  requested_wrench:
    force_body_N: [0.0, 35.0, 1220.0]
    torque_body_Nm: [45.0, -20.0, 8.0]
  achieved_wrench:
    force_body_N: [0.0, 18.0, 1175.0]
    torque_body_Nm: [31.0, -16.0, 2.0]
  normalized_residual: 0.41
  active_constraints:
    - engine_2_thrust_max
    - engine_4_ramp_up_max
    - engine_5_unavailable
  trim_id: post_failure_trim_003
```

O resduo usa a **mesma matriz de escala S** da margem geometrica, senao forca e torque nao sao
comparaveis. Ver [[Estavel definido operacionalmente]].

## Ativacao de limite

Por [[ADR-005 - Saturacao e telemetria]], saturacao e limite de rampa sao **telemetria, nao guarda**
no produto minimo. Cada ativacao e registrada com instante, atuador e tipo de limite.

```yaml
limit_activation:
  time_s: 8.220
  actuator: engine_3
  limit: thrust_rate_up_max
  duration_s: 0.340
```

## Classificacao de resultado de campanha

Por modo de falha, nunca por binario:

```yaml
outcome:
  stable: true | false
  failure_mode:
    - attitude_divergence
    - altitude_loss
    - wrench_unattainable
    - actuator_saturation
    - post_failure_trim_absent
    - capture_region_missed
```

## Regra de geracao de figura

> Nenhuma figura de relatorio e gerada por script ad hoc. So pelo comando oficial, que carrega os
> mesmos modulos testados.

## Ligacoes

[[Alocacao de controle]] · [[ADR-005 - Saturacao e telemetria]] · [[Marco 0 - Fundacao]]
