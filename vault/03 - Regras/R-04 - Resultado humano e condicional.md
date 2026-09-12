---
tags: [regra, piloto, redacao]
regra: R-04
estado: ativa
data: 2026-09-11
---

# R-04 - Resultado humano e sempre condicional

## A regra de redacao

O relatorio escreve:

> Para o envelope de atraso vestibular, atraso visual, capacidade articular e torque de ombro
> assumido, a arquitetura apresenta (ou nao apresenta) uma regiao estavel.

**Nunca** escreve:

> Um humano consegue.
> Um humano nao consegue.

## Por que

Sem dados instrumentados de pilotos reais, a primeira forma e ciencia de simulacao e a segunda e
adivinhacao. O projeto nao tem, e nao vai ter, piloto instrumentado.

O risco concreto: concluir que "controle humano direto e inviavel" quando a conclusao honesta seria
"inviavel dentro do envelope humano hipotetico usado". A primeira ainda e uma conclusao valiosa,
desde que seja dita assim.

## Procedencia humana tem o mesmo rigor da de motor

Os parametros do piloto sao tao ou mais decisivos que parte dos dados de propulsao. O atraso humano,
de 150 a 300 ms, e **maior** que o do atuador eletrico e tem evidencia empirica provavelmente mais
fraca que qualquer ficha de fabricante.

```yaml
pilot_parameter:
  value: ...
  unit: ...
  provenance:
    source_type: literature | estimate | calibration
    evidence_class: measured | derived | inferred
    applicability:
      posture: ...
      task: ...
      fatigue_state: ...
      subject_population: ...
  uncertainty:
    distribution: ...
```

## Ligacoes

[[Modelo de piloto]] · [[Regras de procedencia]] · [[Marco 6 - Piloto e regiao R]]
