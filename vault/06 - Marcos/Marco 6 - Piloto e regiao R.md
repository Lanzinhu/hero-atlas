---
tags: [marco, critico]
marco: 6
prazo: 3 semanas
estado: aguardando
---

# Marco 6 - Piloto e regiao R

> O marco mais importante e o mais exposto a estouro de prazo.

## Pergunta

**Qual e a regiao R, e o que a encolhe?**

## Aqui a dinamica espacial completa vira obrigatoria

Este e exatamente o marco onde o torque induzido pelo braco vira o objeto de estudo, e nesta
arquitetura **o braco e o atuador**. Aproximar aqui seria aproximar a variavel sob investigacao.

Ver [[ADR-001 - Ponto de referencia e forma da dinamica]], rota espacial.

## Entregavel

- Dinamica espacial completa sobre `O`, com `M_O` e `b_O`
- Piloto com a cadeia de atrasos decomposta
- Amostragem de R, fases 2 e 3 de [[ADR-006 - Exploracao de R]]
- Comparacao das duas rotas laterais, por funcional multiobjetivo
- **Comparacao das duas arquiteturas de pilotagem**

## Criterio de sucesso

Mapa bidimensional de ganho humano contra atraso, com as fronteiras de oscilacao induzida.
E a classificacao por **modo de falha**, nao por binario.

## Ordem de corte, declarada antes de comecar

```yaml
scope_cut_order:
  1: remove_direct_lateral_route_comparison
  2: use_single_axis_pilot_model_before_3d_pilot
  3: use_prescribed_arm_motion_with_spatial_dynamics
  4: defer_full_R_sampling_to_post_M6
```

## Como o resultado e redigido

Ver [[R-04 - Resultado humano e condicional]]. Sempre condicional ao envelope humano assumido.
Nunca "um humano consegue".

## Ligacoes

[[Modelo de piloto]] · [[Pergunta central R]] · [[Cinematica de braco]] ·
[[R-01 - Conservacao com bracos moveis]] · [[R-03 - R tem parametros finitos]]
