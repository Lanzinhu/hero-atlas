---
tags: [indice, marcos, cronograma]
atualizado: 2026-09-11
---

# Indice de marcos

> **Trim, alocacao e mapa de autoridade vem ANTES da dinamica sofisticada.**
> Analise barata pode eliminar ou transformar uma arquitetura antes de semanas em integracao de
> quaternion.

| # | Marco | Pergunta respondida | Prazo | Estado |
|---|---|---|---|---|
| 0 | [[Marco 0 - Fundacao]] | A fundacao esta correta? | 1 semana | **em andamento** |
| 1 | [[Marco 1 - Envelope]] | O conceito fecha na conta? | 1 semana | aguardando |
| 2 | [[Marco 2 - Trim e autoridade]] | Os atuadores produzem o necessario, e em quanto tempo? | 1 semana | aguardando |
| 3 | [[Marco 3 - Dinamica]] | O integrador esta correto e os eventos caem no instante certo? | 2 semanas | aguardando |
| 4 | [[Marco 4 - Pairado]] | Paira, e quando nao paira, por que? | 2 semanas | aguardando |
| 5 | [[Marco 5 - Sensibilidade]] | Quais parametros dominam e qual e o atraso critico? | 2 semanas | aguardando |
| 6 | [[Marco 6 - Piloto e regiao R]] | Qual e a regiao R, e o que a encolhe? | 3 semanas | aguardando |
| 7 | [[Marco 7 - Falha e contingencia]] | Existe trim pos-falha **e** da para alcanca-lo a tempo? | 3 semanas | aguardando |
| 8+ | [[Marco 8 - CAD e estrutura]] | So com pergunta especifica | 2 dias cada | aguardando |

## Produto minimo cientificamente util

Antes de qualquer coisa do marco 8, o projeto precisa responder:

> Um traje idealizado, com geometria e massa plausiveis, permanece estavel em pairado sob atraso de
> atuador e atraso humano plausiveis?

Bastam: uma familia de veiculo, geometria parametrica simples, quatro ou cinco propulsores, trim
resolvido, dinamica 6-DOF, bracos prescritos, empuxo com atraso e saturacao, PID basico, varredura
de atraso, autoridade de torque e perturbacoes padronizadas.

## Estouro de prazo corta escopo, nao estende cronograma

Cada marco carrega a **sua propria ordem de corte** antes de comecar. Exemplo para o marco 6, o
mais exposto:

```yaml
scope_cut_order:
  1: remove_direct_lateral_route_comparison
  2: use_single_axis_pilot_model_before_3d_pilot
  3: use_prescribed_arm_motion_with_spatial_dynamics
  4: defer_full_R_sampling_to_post_M6
```

Sem isso, marco 6 vira nome elegante para tres meses ajustando jacobianos.

## Ligacoes

[[MOC - Hero Atlas]] · [[Indice do diario]]
