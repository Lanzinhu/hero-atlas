---
tags: [marco]
marco: 2
prazo: 1 semana
estado: aguardando
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

## Ligacoes

[[Trim]] · [[Alocacao de controle]] · [[ADR-002 - Trim inclui momento do peso]] ·
[[ADR-004 - Margem estatica e dinamica]] · [[R-02 - Dois niveis de trim]]
