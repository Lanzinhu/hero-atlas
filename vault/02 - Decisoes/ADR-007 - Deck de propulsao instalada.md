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

## ⚠ Inversao de proposito: o deck produz requisito, nao estimativa

A familia parametrica inicial e **objeto de exploracao de requisitos**, nao modelo de veiculo.

A saida prioritaria **nao** e estimativa central de `tau`, `eta_inst` ou consumo especifico. E uma
regiao admissivel:

> Para que o cenario seja controlavel no modelo, o conjunto instalado precisa satisfazer
> `Theta_prop` pertencente a `A`.

Na pratica, condicoes minimas **conjuntas**:

```
tau <= tau_max
Tdot_up_max >= Tdot_min
eta_inst >= eta_min
M_max / (I * omega_c^2) >= Gamma_min
```

sob a familia declarada de acoplamentos, porque condicao satisfeita isoladamente pode ser
inatingivel em conjunto.

Isso transforma ausencia de dado em **especificacao futura verificavel**. Nao "a turbina parece
rapida", e sim "a arquitetura exige resposta local, rampa, autoridade residual e perda instalada
dentro desta regiao".

Implementado em `analysis/requirements.py`, com `ActuatorRequirement` e `AdmissibleRegion`. Um
requisito sem `conditioned_on` e **recusado**: condicao sem o contexto em que foi obtida nao e
interpretavel.

## ⚠ Violado nao e o mesmo que indeterminado

Um booleano esconde a diferenca que mais importa quando sete de oito grupos de parametro nao tem
dado.

| Veredito | O que o modelo esta dizendo |
|---|---|
| `SATISFIED` | o candidato atende a condicao |
| `VIOLATED` | **nao**: o candidato existe e fura o limite |
| `INDETERMINATE` | **nao da para concluir**: falta o parametro |

Formalmente, a satisfacao nao e avaliavel quando falta um elemento necessario:

```
satisfaz(candidato, Theta) = falso   se existe theta_j necessario e ausente
```

**Nao porque o sistema fisico necessariamente falha**, mas porque a conclusao nao e demonstravel sob
aquele candidato. Fundir os dois transforma lacuna de evidencia em veredito negativo, que e o
espelho exato do erro que o carimbo bloqueia na outra direcao.

`RegionVerdict` separa as tres classes e **a distincao sobrevive ate o relatorio**:

```
Violadas, o modelo diz nao:
  Tdot_up_max >= 900 N/s

Nao demonstraveis sob este candidato, parametro ausente.
Isto NAO e reprovacao, e falta de evidencia:
  eta_inst >= 0.8 -  [parametro ausente]
```

`is_satisfied` exige as duas listas vazias, porque indeterminado nao conta como sim.
`is_demonstrable` diz se um veredito negativo e conclusao ou falta de parametro.
Violacao tem precedencia: se ja ha condicao furada, o modelo diz nao mesmo com outra inavaliavel.

## ⚠ Risco epistemologico: a familia nao pode virar medicao decorativa

O risco restante nao e fisico. E que a familia parametrica nao validada ganhe **aparencia de
medicao** por meio de graficos precisos, amostragens densas e fronteiras suaves. Uma superficie de
estabilidade colorida vira "resultado do traje" na memoria de quem le, inclusive de quem gerou.

Convencao erode. A marca e **estrutural**, em `model_status.py`:

```yaml
model_status:
  propulsion_installed_deck: parametric_unvalidated
  evidence_coverage: partial
  conclusion_scope: conditional_on_declared_model_family
  coupling_model: <qual familia gerou este resultado>
```

`assert_stamped` **recusa** emitir saida condicional sem a marca, e ela vai no titulo, na legenda ou
no rodape de toda figura derivada. A marca e deliberadamente verbosa: marca discreta e ignorada, e o
proposito dela e nao ser ignorada.

## Ligacoes

[[Deck de propulsao instalada - schema]] · [[Propulsao e atraso]] · [[Autonomia e energia]] ·
[[Nivel de evidencia]] · [[ADR-006 - Exploracao de R]]
