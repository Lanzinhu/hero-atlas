---
tags: [indice, adr]
atualizado: 2026-09-11
---

# Indice de decisoes (ADR)

Uma decisao arquitetural registrada tem motivo, alternativa descartada e consequencia.
Voce vai esquecer o porque em tres meses. Por isso elas existem.

| ADR | Decisao | Estado |
|---|---|---|
| [[ADR-001 - Ponto de referencia e forma da dinamica]] | Dinamica sobre ponto fixo `O`, em duas etapas | Aceita |
| [[ADR-002 - Trim inclui momento do peso]] | Trim sobre `O` carrega o momento gravitacional | Aceita |
| [[ADR-003 - Efetividade dinamica no alocador]] | Alocador usa `G_T`, nao comando como empuxo | Aceita |
| [[ADR-004 - Margem estatica e dinamica]] | Duas margens de autoridade, ambas reportadas | Aceita |
| [[ADR-005 - Saturacao e telemetria]] | Saturacao e rampa sao telemetria, nao guarda | Aceita |
| [[ADR-006 - Exploracao de R]] | Tres fases: sensibilidade, Sobol, fronteira | Aceita |

## Historico de revisoes do plano

O plano passou por sete revisoes antes de fechar. Cada uma corrigiu defeitos reais.
Ver [[Historico de revisoes]] para o que foi corrigido e por que importa.
