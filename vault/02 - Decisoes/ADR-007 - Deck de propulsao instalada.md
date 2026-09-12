---
tags: [adr, propulsao, incerteza, nucleo]
adr: 007
estado: aceita
data: 2026-09-12
---

# ADR-007 - Deck de propulsao instalada e incerteza correlacionada

## Contexto: o ponto fragil foi mal formulado

Ate a revisao 7 o projeto dizia que o ponto mais fragil era o **atraso de pequenos sinais**. Isso
isolou demais a dinamica e deixou de fora o que realmente falta.

O objeto ausente e um **deck de propulsao instalada**, que liga num unico modelo quatro familias
de efeito que o vault mantinha separadas:

| Familia | O que falta |
|---|---|
| Estatico do motor | `T_ss(u, p, T, V)`, marcha lenta, maximo, deriva entre unidades |
| Dinamico do motor e da ECU | atraso de transporte, `tau`, rampa de subida, rampa de descida, histerese |
| Consumo | `mdot_f(T, p, T_amb)`, especialmente em **carga parcial** |
| Instalacao e interacao | perda de entrada, reingestao, pluma contra estrutura, acoplamento entre unidades, dependencia de pose |

```
Tdot_i = Phi_i( T_i, u_i, p, T_amb, V_in_i, q, qdot, x_vizinhanca )
```

com incerteza associada.

Sem esse objeto, os marcos 1, 2, 4, 5 e 7 podem ser matematicamente impecaveis e ainda descrever
apenas **uma familia arbitraria de atuadores**.

## Decisao

O proximo artefato de dados do projeto e o deck, nao mais uma nota isolada de analise. Ver
[[Deck de propulsao instalada - schema]].

Quatro saidas obrigatorias por propulsor: `T_ss`, `Tdot`, `mdot_f`, `H_rotor`.
Quatro grupos de incerteza: motor nu, ECU e dinamica, instalacao e interacao, dependencia de pose
e condicao atmosferica.

## ⚠ Correlacao: nem independencia, nem acoplamento perfeito

A intuicao de que instalacao apertada piora **tudo junto** e plausivel: geometria compacta, entradas
perto de plumas, mais distorcao de admissao, perda de empuxo, possivel piora de margem de surge e
de resposta transitoria.

Mas **o sinal e a intensidade da correlacao nao podem ser impostos como fato sem dados.** Uma
instalacao pode reduzir empuxo por perda aerodinamica quase estatica sem aumentar `tau` na mesma
proporcao. Outra pode degradar muito a resposta e pouco o empuxo maximo medido.

Amostragem independente deixa passar a **cauda otimista**: eficiencia de instalacao ruim com `tau`
milagrosamente baixo, rampa excelente e consumo excelente, tudo ao mesmo tempo. Isso nao existe
fisicamente e infla a regiao estavel.

Um escalar latente de severidade `z` resolve isso. Mas **usar so ele impoe correlacao de posto
perfeita, que e tao infundado quanto independencia, apenas na direcao oposta.**

### A decisao: familia de modelos de acoplamento, nao um modelo

```yaml
coupling_model_family:
  - name: independent
    description: amostragem independente, limite superior otimista conhecido
  - name: fully_coupled_latent
    description: todos os parametros monotonos num unico z de severidade
  - name: partially_coupled
    description: z com ruido por parametro, correlacao de posto entre 0 e 1
report_rule: >
  O resultado e reportado para a familia inteira. Conclusao que muda entre modelos de
  acoplamento nao e conclusao: o proprio acoplamento virou o achado dominante, e isso
  vai no relatorio como tal.
```

### O canto otimista sob acoplamento nao e o canto componente a componente

Sob acoplamento forte a melhor combinacao de cada parametro isolado pode ser **inviavel**.

```yaml
corner_reporting:
  componentwise_best: required      # o melhor de cada parametro, ignorando acoplamento
  attainable_best_under_coupling: required
  gap_between_them: required
```

A distancia entre os dois **e o valor de modelar a correlacao**, e por isso aparece explicita.

## Regra de amostragem

```yaml
sampling_rule:
  independent_parameter_sampling: prohibited_as_sole_model
  dependency_model_required: true
  correlation_evidence_status_required: true
  optimistic_joint_corner_reporting: required
  pessimistic_joint_corner_reporting: required
```

## O que o deck resolve e o que nao resolve

Ele resolve a **estrutura** do problema, nao a evidencia. Um deck sem dados de instalacao
permanece:

```yaml
propulsion_deck:
  status: assumed_parametric_family
  validation_status: unvalidated_for_installed_configuration
```

Isso continua valioso, desde que o resultado seja redigido como fronteira condicional:

> Para a familia declarada de decks de propulsao instalada, incluindo as correlacoes assumidas
> entre perda, atraso, rampa e consumo, o sistema e ou nao e controlavel no envelope declarado.

E um resultado **mais forte** que uma varredura independente, porque deixa explicito qual conjunto
de propriedades reais teria de ser demonstrado depois.

## Ligacoes

[[Deck de propulsao instalada - schema]] · [[Propulsao e atraso]] · [[Autonomia e energia]] ·
[[Nivel de evidencia]] · [[ADR-006 - Exploracao de R]]
