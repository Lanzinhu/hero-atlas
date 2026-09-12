---
tags: [fisica, nucleo, marco-0]
atualizado: 2026-09-11
---

# Propriedades de massa

> O erro mais grave de todo o processo de revisao esteve aqui. Uma versao anterior escrevia
> `I_total = I_CAD + I_motores + ...`, o que e **matematicamente errado** se implementado
> literalmente.

## Por que somar tensores direto esta errado

Tensores de inercia so podem ser somados quando estao:

- expressos no mesmo referencial
- orientados pelos mesmos eixos
- calculados sobre o mesmo ponto de referencia

Em geral cada componente tem inercia **sobre o proprio centro de massa** e **na propria orientacao**.

## A agregacao correta

Primeiro massa e centro:

```
m_total    = soma_j m_j
r_CG_total = ( soma_j m_j * r_j ) / m_total
```

Depois cada tensor rotacionado e transladado, com `d_j = r_j_CG - r_ref`:

```
I_j_ref = R_j * I_j_CG * transposta(R_j)  +  m_j * ( ||d_j||^2 * I3  -  produto_externo(d_j, d_j) )

I_total_ref = soma_j I_j_ref
```

Convencao: `R_j` orienta o componente no corpo, ou seja `v_body = R_j * v_componente`.

```python
@dataclass(frozen=True)
class MassComponent:
    mass_kg: float
    center_of_mass_body_m: NDArray
    inertia_about_own_cg_kg_m2: NDArray
    orientation_body_from_component: NDArray
```

## Tudo depende disso

Torque necessario, resposta angular, `Idot`, `H_rel`, estabilidade de guinada, efeito de mover
bracos, efeito de combustivel queimado, propriedades pos-falha.

Um erro aqui produz um simulador que **voa lindamente no grafico**, que e bem mais perigoso do que
um que cai.

## Ponto de referencia fixo, nao centro movel

Ver [[ADR-001 - Ponto de referencia e forma da dinamica]]. Como o centro migra com a pose e com o
combustivel, o deslocamento `d_j` muda a cada passo. Recalcular a inercia sobre o novo centro e
aplicar a equacao de Euler padrao **parece certo e e sutilmente errado**.

## Combustivel entra na forma geral

```
I      = I(q, m_f)
Idot   = dI/dq * qdot  +  dI/dm_f * mdot_f
r_cg   = r_cg(q, m_f)
```

Para o produto minimo e aceitavel excluir o termo de combustivel da dinamica de curto horizonte,
**desde que explicitamente**:

```yaml
mass_properties:
  fuel_inertia_rate:
    included_in_short_horizon_dynamics: false
    included_in_retrim_and_mission_analysis: true
    justification: >
      A variacao de massa de combustivel e lenta na escala de segundos relevante
      para a estabilidade de atitude.
```

## Massa contabil, nao inercia de CAD

CAD produz propriedades de uma **geometria assumida**, com materiais e componentes explicitamente
modelados. Combustivel, fiacao, fixacoes, eletronica, roupa, capacete e corpo humano continuam
aproximacoes.

```yaml
mass_ledger:
  pilot:       { mass_kg: 80,   model: articulated_segments }
  turbines:    { mass_kg_each: 3.65, location_source: geometry }
  fuel:        { mass_kg_initial: 12, model: fixed_location_lumped_mass }
  electronics: { mass_kg: 2.3,  location_body_m: [0.08, 0.0, 0.12] }
  harness:     { mass_kg: 4.5,  uncertainty_kg: 1.0 }
```

O build alerta quando a massa contabil nao reconcilia com CAD mais concentradas.

**Ressalva obrigatoria no relatorio:** a reconciliacao so e possivel a partir do
[[Marco 8 - CAD e estrutura]]. Toda conclusao de viabilidade dos marcos 1 a 7 repousa sobre massa
**estimada**, nao geometrica.

## Ligacoes

[[Marco 0 - Fundacao]] · [[Casos analiticos]] · [[Cinematica de braco]] · [[Dinamica 6-DOF]]
