---
tags: [marco]
marco: 3
prazo: 2 semanas
estado: aguardando
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

## O que NAO pode ser testado aqui

Conservacao de momento angular com bracos moveis. Ver [[R-01 - Conservacao com bracos moveis]].

## Ligacoes

[[Dinamica 6-DOF]] · [[Regras de tempo e eventos]] · [[Invariantes por caso]]
