---
tags: [dados, evidencia, processo]
atualizado: 2026-09-11
---

# Nivel de evidencia dos dados do projeto

## Estado atual: nada esta arquivado

> **Nenhum numero deste vault tem copia arquivada com hash ainda.**
> Ate ter, nenhum pode virar teste de regressao que quebra o build.

Esta e a primeira divida tecnica do projeto, e ela e do tipo que envenena tudo em silencio se ficar
pendente.

## O que precisa ser arquivado, em ordem de prioridade

| Fonte | Para que serve | Prioridade |
|---|---|---|
| Ficha JetCat P400-PRO-LN | empuxo, massa, consumo, TSFC de referencia | alta |
| Ficha Kingtech K-320G5 | alternativa de classe e custo | alta |
| Pagina de specs JetPack Aviation | benchmark de T/W com fly-by-wire | media |
| PDF de specs AMT Titan e Nike | faixa superior de empuxo | media |
| Relatorio anual 2017 da JPA a SEC | confirma turbinas europeias modificadas | baixa |
| Literatura de McRuer sobre crossover | parametros de piloto | alta |
| Literatura de atraso vestibular e visual | parametros de piloto | alta |

As duas ultimas sao **as mais importantes e as mais ausentes**. O atraso humano e maior que o do
atuador eletrico e decide a conclusao do [[Marco 6 - Piloto e regiao R]].
Ver [[R-04 - Resultado humano e condicional]].

## Como arquivar

1. Baixar o PDF ou salvar a pagina em `docs/sources/`
2. Calcular SHA-256
3. Registrar no schema de procedencia com data de acesso e revisao da fonte
4. Declarar o escopo de aplicabilidade: em que condicao aquele numero vale

```yaml
provenance:
  source_type: manufacturer_datasheet
  evidence_class: declared_specification
  retrieval_date: 2026-09-11
  source_file_sha256: "..."
  applicability:
    configuration: static_test_stand
    altitude_m: 0
    atmosphere: ISA
    installation: bare_engine
  uncertainty: { type: bounded, lower: 380, upper: 410, unit: N }
```

## Classificacao dos numeros que ja temos

| Nivel | Exemplos |
|---|---|
| Ficha de fabricante | JetCat P400 Pro com 40,5 kgf, 3,65 kg, 1,04 kg/min. Kingtech K-320G5 com 32 kgf e 2,9 kg. Specs publicadas da JetPack Aviation |
| Derivado por fisica conhecida | TSFC calculado. Autonomia integrada. T/W a partir de massas publicadas. Potencia por newton |
| Imprensa ou alegacao sem verificacao | Modelo de turbina da Gravity, **nunca divulgado**. Os "1.050 bhp" e "1.500 hp", incoerentes. Autonomia de 7 a 8 min do Mk3. Teto de 12.000 pes, nunca demonstrado |

Nenhum numero do terceiro grupo vira teste de igualdade.

## Ressalva permanente do relatorio

A reconciliacao de massa contabil com CAD so e possivel a partir do
[[Marco 8 - CAD e estrutura]]. **Toda conclusao de viabilidade dos marcos 1 a 7 repousa sobre massa
estimada, nao geometrica.** Isso vai explicito no relatorio, nao apenas implicito no esquema de
incerteza.

## Ligacoes

[[Regras de procedencia]] · [[Estado da arte - trajes de voo]] · [[Microturbinas disponiveis]] ·
[[Propriedades de massa]]
