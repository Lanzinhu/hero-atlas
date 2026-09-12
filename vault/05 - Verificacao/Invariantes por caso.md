---
tags: [verificacao, fisica]
atualizado: 2026-09-11
---

# Invariante apropriada a cada caso

## O problema

O sistema **nao conserva energia mecanica** quando ha propulsao, consumo de combustivel, arrasto,
controlador, atrasos e bracos prescritos.

Pior: a trajetoria articular prescrita **injeta trabalho**, representando musculos idealizados.
Logo o modelo pode alterar a energia de rotacao do tronco **sem que isso seja erro**.

Testar conservacao onde ela nao vale produz dois desastres: teste falhando porque a fisica certa foi
modelada, ou teste passando porque a energia injetada foi esquecida.

## A tabela

| Caso | Invariante apropriada |
|---|---|
| Corpo rigido isolado, sem torque externo | momento angular total |
| Corpo rigido isolado, sem dissipacao | energia cinetica |
| Queda livre | energia mecanica |
| Bracos fixos, sem propulsao | invariantes de corpo rigido |
| **Bracos moveis prescritos, sem torque externo** | **momento angular total**, se os segmentos estiverem corretamente incluidos |
| Propulsao, arrasto ou combustivel | balanco de energia e momento, **nao** conservacao simples |

## O caso mais valioso da tabela

**Bracos moveis sem torque externo.** E o unico teste que verifica se `H_rel` esta corretamente
ligado. Sem ele, um erro nesse termo passa despercebido para sempre.

Mas ele **so existe a partir do marco 6**, porque o modelo reduzido dos marcos 3 a 5 nao tem os
termos que produziriam a conservacao. Ver [[R-01 - Conservacao com bracos moveis]].

E avaliado **no referencial inercial**:

```
H_I(t) = R_IB(t) * H_B(t)
criterio:  || H_I(t) - H_I(0) || < eps_H
```

Verificar componentes de `H_B` no referencial do corpo seria incorreto, porque o proprio referencial
gira.

## Ligacoes

[[Tres classes de teste]] · [[Cinematica de braco]] · [[R-01 - Conservacao com bracos moveis]]
