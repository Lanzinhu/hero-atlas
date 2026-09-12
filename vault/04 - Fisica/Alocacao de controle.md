---
tags: [fisica, controle, alocacao]
atualizado: 2026-09-11
---

# Alocacao de controle

## Subatuado nao e incontrolavel

Um quadrirrotor tem posto 4 e e perfeitamente controlavel por inclinacao. Concluir que cinco bocais
com posto 5 "exigem vetorizacao para fechar seis graus" e **raciocinio errado**.

Tres analises distintas, nunca confundidas:

| Analise | Pergunta |
|---|---|
| Alocacao instantanea, `W = [n_i ; (r_i - r_O) x n_i]` | Quais wrenches sao atingiveis? |
| Controlabilidade linearizada, `C = [B, AB, A2B, ...]` | A dinamica pode ser conduzida? |
| Condicionamento | Quanto esforco e quanta sensibilidade? |

Um sistema pode ter posto suficiente e ser impilotavel por mau condicionamento, e pode ser
subatuado e perfeitamente pilotavel.

## As duas rotas laterais

Nesta arquitetura existe **forca lateral direta** comandavel sem inclinar o tronco, porque os bocais
de braco apontam para fora. Isso e caracteristica real do conceito e nao deve ser apagado pela
analogia com multirrotor.

Comparacao por funcional multiobjetivo, nao por tempo de resposta:

```
J = w_p * integral ||p_xy - p_ref||^2 dt
  + w_theta * integral ||theta||^2 dt
  + w_u * integral ||dT||^2 dt
```

Mais pico de deslocamento, tempo de recuperacao, excursao de atitude, perda de altitude, consumo de
reserva vertical, saturacao, movimento de braco exigido, torque de ombro, margem pos-falha e erro de
guinada induzido.

**Resultado esperado, contraintuitivo:** forca lateral direta corrige mais rapido mas induz guinada
e exige assimetria grande entre bracos, enquanto inclinar o corpo demora mais, preserva simetria e
usa o vetor de empuxo de forma mais eficiente.

## Alocacao incremental em torno do trim

Metodo primario. Com `T_i = T_i_trim + dT_i`, e convexa, fisicamente correta, bem condicionada, e
**nunca se aproxima da regiao anelar perto de zero**.

```
min_du  || W_T * G_T * du - dw_desejado ||^2_Q  +  || du ||^2_R
s.a.    u_min <= u_k + du <= u_max
        |du| <= du_max_ECU
```

`G_T` e a efetividade dinamica prevista. Ver [[ADR-003 - Efetividade dinamica no alocador]].

Limitacao a declarar: e local, entao excursao grande como falha de motor exige retrim.

## Por que o cone de segunda ordem so serve de diagnostico

Com folga por bocal, `||f_i|| <= Gamma_i` e `T_min <= Gamma_i <= T_max`, o otimizador pode escolher
`Gamma_i = T_min` com `f_i = 0`. A variavel auxiliar respeita o minimo **enquanto o motor esta
desligado na fisica**. O resduo `Gamma_i - ||f_i||` detecta mas nao resolve.

Uso legitimo: limite inferior de custo, solucao inicial, deteccao de geometria ruim.

## Quatro modos de falha, nao um

Com limites de caixa e objetivo de minimos quadrados **quase sempre existe solucao admissivel**,
ainda que incapaz de produzir o wrench pedido. O evento importante e o resduo.

| Situacao | Evento |
|---|---|
| Solucao obtida com resduo alto | `wrench_unattainable` |
| Igualdade dura mais limites sem solucao | `allocator_infeasible` |
| Solver falha por condicionamento ou escala | `solver_failure` |
| Retorno viola restricao por tolerancia | `constraint_violation` |

```yaml
allocator_event:
  type: wrench_unattainable
  time_s: 12.475
  requested_wrench: { force_body_N: [0.0, 35.0, 1220.0], torque_body_Nm: [45.0, -20.0, 8.0] }
  achieved_wrench:  { force_body_N: [0.0, 18.0, 1175.0], torque_body_Nm: [31.0, -16.0, 2.0] }
  normalized_residual: 0.41
  active_constraints: [engine_2_thrust_max, engine_4_ramp_up_max, engine_5_unavailable]
  trim_id: post_failure_trim_003
```

O resduo usa a **mesma matriz de escala S** da margem geometrica, senao forca e torque nao sao
comparaveis. Ver [[Estavel definido operacionalmente]].

Isso transforma o simulador de um sistema que informa "nao conseguiu" num instrumento que explica o
que foi pedido, o que foi entregue, qual eixo faltou, e se o limite foi empuxo, marcha lenta, taxa,
falha ou geometria.

## Hierarquia de contingencia, declarada

Em contingencia nao da para preservar tudo. A ordem de sacrificio e explicita, nao escondida em
pesos arbitrarios:

```
limites fisicos  >  taxa angular  >  atitude  >  reducao de velocidade vertical
                 >  altitude  >  posicao lateral  >  trajetoria nominal
```

O produto minimo usa pesos documentados que **aproximam prioridade lexicografica**, e o relatorio
diz isso.

## Ligacoes

[[Trim]] · [[ADR-004 - Margem estatica e dinamica]] · [[Marco 7 - Falha e contingencia]]
