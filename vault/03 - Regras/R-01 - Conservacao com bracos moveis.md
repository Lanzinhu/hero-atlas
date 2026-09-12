---
tags: [regra, verificacao]
regra: R-01
estado: ativa
data: 2026-09-11
---

# R-01 - O teste de conservacao com bracos moveis so existe a partir do marco 6

## A contradicao que esta regra resolve

O [[ADR-001 - Ponto de referencia e forma da dinamica]] declara, para os marcos 3 a 5:

```yaml
internal_mass_migration_coupling: false
```

E a verificacao mantinha como caso valioso "bracos moveis prescritos, sem torque externo, conserva
momento angular total".

**Sem os termos `Idot`, `H_rel`, `Hdot_rel`, `r_C/O`, `rdot_C/O` e `rddot_C/O`, nao ha razao para
esperar conservacao.** O teste verificaria a ausencia que o proprio modelo declarou, e falharia por
motivo correto, o que treina qualquer pessoa a desliga-lo.

## A regra

| Teste | Marco minimo |
|---|---|
| Corpo rigido sem segmentos moveis | 3 |
| Bracos fixos, sem torque externo | 3 |
| Massa variavel lenta, sem bracos moveis | 3 ou 4 |
| **Bracos moveis conservando momento angular** | **6** |
| **Comparacao entre dinamica reduzida e espacial** | **6** |

## Como avaliar, quando chegar a hora

**No referencial inercial**, porque o referencial do corpo gira:

```
H_I(t) = R_IB(t) * H_B(t)

criterio:  || H_I(t) - H_I(0) || < eps_H
```

Verificar componentes de `H_B` no referencial do corpo **seria incorreto**.

## Por que esse teste vale tanto

E ele que verifica se `H_rel` esta corretamente ligado. Sem ele, um erro nesse termo passa
despercebido para sempre, porque nenhum outro caso o exercita.

## Ligacoes

[[Invariantes por caso]] · [[Cinematica de braco]] · [[ADR-001 - Ponto de referencia e forma da dinamica]]
