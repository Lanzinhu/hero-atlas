---
tags: [regra, evidencia]
estado: ativa
---

# Regras de procedencia

## O principio

> Uma ficha de fabricante e fonte primaria para saber que **o fabricante declara** um valor.
> Isso nao a torna evidencia forte sobre o comportamento em toda condicao operacional.

A mesma ficha e:

| Para | Forca da evidencia |
|---|---|
| Massa seca | muito forte |
| Diametro externo | muito forte |
| Empuxo estatico em condicao especificada | razoavel |
| Resposta transitoria | **nenhuma** |
| Reingestao de gases quentes | **nenhuma** |
| Comportamento com bocal vetorizado | **nenhuma** |

E um valor derivado por fisica conhecida **nao e automaticamente mais fraco**: um peso calculado a
partir de massa bem definida tem incerteza menor que um empuxo de catalogo sem condicao de ensaio
descrita.

## O schema

```yaml
provenance:
  source_type: manufacturer_datasheet   # datasheet | literature | derived | press | estimate | test
  evidence_class: declared_specification # measured | declared | derived | inferred
  retrieval_date: 2026-09-11
  source_revision: "rev. X"
  source_file_sha256: "..."             # copia arquivada em docs/sources/
  applicability:
    configuration: static_test_stand
    altitude_m: 0
    atmosphere: ISA
    inlet_distortion: none
    installation: bare_engine
  uncertainty: { type: bounded, lower: 380, upper: 410, unit: N }
```

## Copia versionada e obrigatoria

**URL sem copia arquivada nao conta como procedencia.** Paginas mudam e fichas sao revisadas.
Toda fonte vai para `docs/sources/` com hash SHA-256 registrado.

## Tolerancia pertence a grandeza, nao a fonte

O criterio de aceitacao compara incertezas, nao uma porcentagem institucional:

```
aceitar se  |y_modelo - y_referencia| <= delta_y_referencia + delta_y_modelo
```

| Grandeza | Natureza | Faixa inicial |
|---|---|---|
| Massa seca | mensuravel diretamente | estreita |
| Dimensao geometrica | mensuravel diretamente | estreita |
| Empuxo estatico de catalogo | depende da condicao de ensaio | moderada |
| Consumo maximo | depende de regime e combustivel | moderada |
| Tempo de aceleracao | depende fortemente da ECU | larga |
| Autonomia de traje | depende do perfil de missao | larga |
| Teto operacional | frequentemente derivado ou promocional | exploratoria |

Um catalogo pode dar massa com precisao de gramas e empuxo arredondado ao quilograma-forca, na
mesma pagina. Tolerancia uniforme por fonte produz bloqueio falso no integrador continuo.

## Isso vale para o piloto tambem

Ver [[R-04 - Resultado humano e condicional]].

## Ligacoes

[[Nivel de evidencia]] · [[Estado da arte - trajes de voo]] · [[Regras de unidades]]

## ⚠ Incerteza ausente e inconclusiva, nao aprovada

Uma versao anterior fazia incerteza nao declarada devolver **infinito**, de modo que qualquer
divergencia passasse no criterio de aceitacao. Matematicamente consistente, epistemicamente
invertido: **a falta de incerteza tornava o dado irrefutavel por tolerancia infinita.**

Isso contradiz a regra central do projeto. Numero sem procedencia e ficcao, nao verdade
inquestionavel.

Tres coisas que precisam ficar separadas:

| Situacao | O que e |
|---|---|
| Comparacao inconclusiva | a incerteza nao e conhecida |
| Criterio satisfeito | so pode ser emitido com comparacao feita |
| Elegivel como teste de regressao | so com comparacao conclusiva |

```
aceita(a, b) = indeterminado            se falta incerteza necessaria
             = |a - b| <= U_a + U_b     caso contrario
```

```yaml
acceptance_result:
  status: indeterminate
  reason: uncertainty_missing
  numeric_comparison_performed: false
  eligible_for_regression: false
```

Implementado em `AcceptanceResult`. Ver [[Violado nao e indeterminado]].
