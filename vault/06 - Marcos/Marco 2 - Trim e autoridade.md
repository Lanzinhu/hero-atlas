---
tags: [marco]
marco: 2
prazo: 1 semana
estado: entregue
entregue_em: 2026-09-12
---

# Marco 2 - Trim e autoridade

## Pergunta

**Os atuadores produzem as forcas e torques necessarios, inclusive com falha, e em quanto tempo?**

## Entregavel

- `solve_trim()` com tipo parametrizado e momento do peso sobre `O`
- Matriz de alocacao instantanea
- Mapa de autoridade com **margem estatica e margem dinamica**
- Conjunto de momentos atingiveis, com e sem falha
- Numero de condicao por pose

## Criterio de sucesso

As duas margens aparecem **lado a lado** em toda figura.
Ver [[ADR-004 - Margem estatica e dinamica]].

E a reserva provisoria de 10 por cento e **substituida** pela margem calculada a partir do conjunto
de forcas atingiveis.

## Por que vem antes da dinamica

Analise barata pode eliminar ou transformar uma arquitetura antes de semanas gastas em integracao
de quaternion. Se a geometria nao tem autoridade de guinada, nenhum controlador vai salvar.

## ⚠ Resultado: tres achados duros

A geometria usada e **plausivel, nao medida**: cinco propulsores de 35 kgf, quatro de braco
inclinados 25 graus a 0,35 m de meia envergadura, mais um dorsal. Ainda assim, os achados sao
propriedades da **classe** de arquitetura, nao daquele numero.

### 1. Forca lateral e rolagem sao o mesmo canal

Com todos os bocais de braco na mesma altura e mesma envergadura, a linha de forca lateral e a de
momento de rolagem ficam **exatamente proporcionais**, com fator de menos 0,55.

Posto da matriz de alocacao: **4 de 6**, com cinco atuadores.

Nao da para comandar rolagem sem gerar forca lateral, nem o contrario. Sao um canal, nao dois.

### 2. Um milimetro de desvio lateral ja nao fecha

Consequencia direta do acoplamento. Um centro de massa deslocado lateralmente exige momento de
rolagem **sem** forca lateral, e isso esta fora do espaco coluna.

**Geometricamente inatingivel, nao falta de capacidade.** Motor maior nao resolve. Piloto com bracos
assimetricos, tanque fora do eixo, ou qualquer massa lateral nao tem equilibrio.

### 3. Nenhuma perda unica e tolerada

Perder **qualquer** um dos cinco propulsores torna o equilibrio inviavel no mesmo centro de massa.
Com posto 4 e cinco atuadores nao ha folga: cada um esta no equilibrio.

### A janela de centro de massa

| Eixo | Janela |
|---|---|
| Longitudinal | 13,5 cm, de +0,085 a +0,220 m |
| **Lateral** | **zero** |

E o centro precisa ficar **sob o centroide de empuxo**, nao sobre o ponto de referencia.

### O que o marco 1 nao conseguia ver

O envelope escalar presumia que toda capacidade instalada contribui para a direcao util. O trim
mostra que, mesmo no melhor caso desta geometria, a **eficiencia vertical fica entre 85 e 100 por
cento**, e a soma de empuxo do equilibrio e bem menor que a capacidade instalada.

### Duas causas de inviabilidade, que nao se confundem

| Causa | O que significa | O que resolve |
|---|---|---|
| `geometrically_unattainable` | wrench fora do espaco coluna | geometria diferente |
| `bounds_infeasible` | direcao atingivel, limites bloqueiam | motor maior ou marcha lenta menor |

Fundir as duas faz alguem comprar turbina maior para um problema que turbina nenhuma resolve.

## Ligacoes

[[Trim]] · [[Alocacao de controle]] · [[ADR-002 - Trim inclui momento do peso]] ·
[[ADR-004 - Margem estatica e dinamica]] · [[R-02 - Dois niveis de trim]]
