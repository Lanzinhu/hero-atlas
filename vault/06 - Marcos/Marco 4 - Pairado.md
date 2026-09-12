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

## Criterio de sucesso

60 s de pairado com rajada: atitude abaixo de 2 graus RMS, deriva abaixo de 1,5 m, sem saturacao
sustentada, com o tau nominal do envelope.

E, quando falhar, o registro tem que dizer **qual eixo faltou e qual restricao estava ativa**:

```yaml
allocator_event:
  type: wrench_unattainable
  normalized_residual: 0.41
  active_constraints: [engine_2_thrust_max, engine_4_ramp_up_max]
```

## Decisao pendente deste marco

Metodo de `G_T`: diferenca finita local ou modelo analitico.
Ver [[ADR-003 - Efetividade dinamica no alocador]].

## Ligacoes

[[Alocacao de controle]] · [[Estavel definido operacionalmente]] · [[Telemetria]]
