---
tags: [marco]
marco: 3
prazo: 2 semanas
estado: parcial
---

# Marco 3 - Dinamica

## Pergunta

**O integrador esta correto, a pose move o centro de massa, e os eventos caem no instante certo?**

## Entregavel

- Dinamica 6-DOF **reduzida** sobre o ponto fixo `O`
- Propulsao com atraso e saturacao
- Bracos prescritos com derivadas analiticas
- Integrador orientado a evento, com eventos agendados e as guardas do produto minimo

## A aproximacao esta declarada

```yaml
dynamics_model:
  formulation: reduced_quasi_static_pose
  internal_mass_migration_coupling: false
  valid_for: [geometry, torque_authority, actuator_delay, saturation, controller_stability]
  invalid_for: [arm_motion_induced_torque, fast_pose_transient]
```

Ver [[ADR-001 - Ponto de referencia e forma da dinamica]].

## Criterio de sucesso

- Suite analitica passa: Dzhanibekov, equivariancia, binario puro, norma do quaternion
- Ordem quatro em subcasos suaves, classe A de [[Tres classes de teste]]
- Deslocamento do centro de massa com bracos a 60 graus confere com calculo manual
- Alinhamento de evento, classe C

## ⚠ Ordem de corte, declarada antes de comecar

Duas semanas orcadas. Estouro corta escopo nesta ordem, nunca estende prazo.

```yaml
scope_cut_order:
  1: guardas de evento so para falha por limiar; solo e combustivel viram telemetria
  2: bracos em pose fixa, sem trajetoria prescrita; adia Idot e H_rel para o marco 6
  3: arrasto isotropico com um coeficiente so, em vez de tensor por eixo
  4: integrador de passo fixo apenas; adia passo adaptativo
  5: propulsao com constante de tempo unica, sem dependencia do ponto de operacao
```

O corte 2 e o mais caro cientificamente e por isso e o segundo, nao o primeiro: sem trajetoria de
braco o marco 3 ainda responde sobre integrador, eventos e propulsao, que sao suas perguntas.

O corte 5 **nao** pode virar resultado publicado: ele contradiz a regra de envelope de
[[Propulsao e atraso]]. Se for acionado, o marco 3 entrega apenas verificacao numerica, e a
varredura de atraso fica inteira para o [[Marco 5 - Sensibilidade]].

## O que NAO pode ser testado aqui

Conservacao de momento angular com bracos moveis. Ver [[R-01 - Conservacao com bracos moveis]].

## Ligacoes

[[Dinamica 6-DOF]] · [[Regras de tempo e eventos]] · [[Invariantes por caso]]
