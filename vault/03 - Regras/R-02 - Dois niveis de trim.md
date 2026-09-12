---
tags: [regra, trim, falha]
regra: R-02
estado: ativa
data: 2026-09-11
---

# R-02 - Trim tem dois niveis de viabilidade

> **Existencia matematica nao e alcancabilidade.**

## A regra

Duas perguntas distintas, duas saidas distintas.

### Viabilidade estatica

Existe um vetor de empuxos dentro dos limites que resolve o equilibrio?

```yaml
trim_status: feasible | infeasible
```

### Viabilidade dinamica de captura

A partir do empuxo atual e dos limites de subida e descida, esse trim pode ser alcancado no tempo
necessario?

```yaml
trim_capture_status:
  reachable_within_horizon: true | false
  horizon_s: ...
  limiting_actuators: [...]
```

## Por que importa, especialmente apos falha

Um trim pos-falha pode existir matematicamente e ser **inalcancavel** antes de uma perda de
altitude ou de uma rotacao perigosa.

> Um novo trim possivel nao significa que a falha seja sobrevivivel.

`retrim` calcula um equilibrio possivel. Ele **nao** estabiliza o intervalo entre a falha e esse
equilibrio, quando o alocador pode saturar, a atitude divergir, o controlador perder autoridade, o
piloto nao mover os bracos rapido o suficiente, e a altitude acabar antes.

## Fluxo correto de falha

```
falha
  -> deteccao e classificacao
  -> reconfiguracao dos atuadores disponiveis
  -> solve_trim para verificar se existe equilibrio viavel
  -> definicao de alvo de contingencia
  -> alocador e controlador transitorios levam ao novo alvo
  -> retrim efetivo, se alcancado
```

## Metricas do relatorio de falha

| Metrica | Pergunta |
|---|---|
| Existencia de trim pos-falha | Ha equilibrio possivel? |
| Tempo de deteccao | Quando a reconfiguracao comeca? |
| Excursao antes do retrim | O que acontece no transiente? |
| Saturacao de atuadores | Ha forca disponivel durante a recuperacao? |
| Perda de altitude | Existe tempo para a contingencia? |
| Regiao de captura | O controlador alcanca o novo trim? |

## Ligacoes

[[Trim]] · [[ADR-002 - Trim inclui momento do peso]] · [[ADR-004 - Margem estatica e dinamica]] ·
[[Marco 7 - Falha e contingencia]]
