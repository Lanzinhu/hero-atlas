---
tags: [dados, propulsao, schema, prioridade-alta]
atualizado: 2026-09-12
status: assumed_parametric_family
validation_status: unvalidated_for_installed_configuration
---

# Deck de propulsao instalada - schema e hipoteses

> **Este e o proximo artefato de dados do projeto.** Nao mais analise de controle, CFD, CAD ou
> pesquisa de estado da arte. Ver [[ADR-007 - Deck de propulsao instalada]].

## Saidas obrigatorias, por propulsor

| Saida | Simbolo | Unidade |
|---|---|---|
| Empuxo estacionario | `T_ss(u, p, T_amb, V_in)` | N |
| Taxa de empuxo | `Tdot(T, u, ...)` | N/s |
| Consumo massico | `mdot_f(T, p, T_amb)` | kg/s |
| Momento angular do rotor | `H_rotor` | N m s |

## Envelope minimo de dinamica

O projeto nao varre mais **apenas** `tau`. O envelope e:

```
Theta_atuador = [ T_d , tau_subida , tau_descida , Tdot_up_max , Tdot_down_max , T_min , T_max ]
```

Dois decks com o **mesmo** `tau` e controlabilidade radicalmente diferente: um com rampa muito
limitada, marcha lenta alta, saturacao assimetrica e perda instalada dependente de atitude; outro
sem nada disso.

O produto da analise deixa de ser `tau_critico` e passa a ser a sensibilidade da regiao estavel ao
envelope inteiro. Em linguagem de relatorio: **quais combinacoes de atraso, constante local, rampa
e autoridade residual deixam de satisfazer os criterios operacionais.**

## Schema de incerteza correlacionada

```yaml
propulsion_uncertainty_model:
  latent_installation_severity_z:
    distribution: bounded
    range: [0.0, 1.0]
    meaning: severidade da instalacao, do caso limpo ao caso apertado

  thrust_installation_efficiency:
    function_of: [z, arm_pose, forward_speed]
    lower_bound: null      # a preencher, sem base ainda
    upper_bound: null

  actuator_time_constant:
    function_of: [z, thrust_fraction, ambient_state]
    lower_bound_s: null
    upper_bound_s: null

  thrust_ramp_up:
    function_of: [z, thrust_fraction]
    lower_bound_N_s: null
    upper_bound_N_s: null

  tsfc:
    function_of: [z, thrust_fraction, ambient_state]
    lower_bound: null
    upper_bound: null

  coupling_model: independent | fully_coupled_latent | partially_coupled
  correlation_status:
    type: assumed_structural_correlation
    evidence_status: unvalidated
```

Os campos nulos sao deliberados: **preencher com numero inventado seria pior que deixar vazio.**
O schema existe para tornar a lacuna visivel e enderecavel.

## Estado da evidencia, por grupo

| Grupo | Existe dado? |
|---|---|
| Empuxo estatico e massa, motor nu | **sim**, catalogo. Ver [[Microturbinas disponiveis]] |
| Consumo em empuxo maximo | **sim**, catalogo |
| Consumo em carga parcial | **nao** |
| Atraso de transporte da ECU | **nao** |
| `tau` local perto do trim | **nao** |
| Rampa local de subida e descida | **nao** |
| Eficiencia de instalacao em arranjo vestivel | **nao** |
| Interacao entre unidades e dependencia de pose | **nao** |

Sete de oito grupos sem dado. Essa e a real dimensao da lacuna, e ela e **maior** do que o vault
descrevia quando falava so de atraso.

## Por que carga parcial importa mais do que parece

TSFC e definido como `mdot_f / F`. Fora do ponto de projeto o empuxo cai, e se o fluxo de
combustivel nao cair proporcionalmente o consumo especifico **piora**. A eficiencia global tambem
tende a se deteriorar em off-design.

Consequencia direta: **usar TSFC de catalogo, medido perto do maximo, como aproximacao de pairado
nao e conservador por padrao.** Pode subestimar o consumo.

Isso invalida o uso do TSFC de catalogo como validacao forte de autonomia alegada.
Ver [[Autonomia e energia]].

## Ligacoes

[[ADR-007 - Deck de propulsao instalada]] · [[Propulsao e atraso]] · [[Nivel de evidencia]] ·
[[Microturbinas disponiveis]]
