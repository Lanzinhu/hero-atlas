---
tags: [adr, campanha, metodo]
adr: 006
estado: aceita
data: 2026-09-11
---

# ADR-006 - Estrategia de exploracao de R, em tres fases

## O problema

Grade cartesiana explode. Cinco valores em sete dimensoes ja sao:

```
5^7 = 78.125 execucoes
```

antes de incluir cenarios atmosfericos, perturbacoes, falhas, arquiteturas de controle, rotas
laterais e familias de veiculo.

## Decisao

### Fase 1 - Varreduras unidimensionais

Antes do piloto completo. Objetivo: **descobrir quais parametros dominam** e descartar os que nao
movem a agulha.

- atraso de turbina
- taxa maxima de empuxo
- relacao empuxo por peso
- posicao longitudinal do centro
- assimetria dos bracos

### Fase 2 - Amostragem de baixa discrepancia

Sobol ou hipercubo latino. Muito mais eficiente que grade completa em seis ou sete dimensoes.

Cada execucao classificada por **modo de falha**, nao por binario estavel e instavel:

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

### Fase 3 - Refinamento da fronteira

Concentrar novas amostras perto de `dR`.

**A pergunta nao e qual porcentagem foi estavel.** E qual combinacao reduz a margem ate a primeira
falha, e qual e o modo dominante.

## Restricao importante

`q_bracos` e **funcao temporal, nao numero**. Explorar uma funcao como dimensao de Monte Carlo e
dimensao infinita disfarcada. Ver [[R-03 - R tem parametros finitos]].

## Ligacoes

[[Pergunta central R]] · [[R-03 - R tem parametros finitos]] · [[Marco 6 - Piloto e regiao R]]
