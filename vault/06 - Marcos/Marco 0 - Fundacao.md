---
tags: [marco, ativo]
marco: 0
prazo: 1 semana
estado: em andamento
iniciado: 2026-09-11
---

# Marco 0 - Fundacao

> Deliberadamente pouco cinematografico e muito confiavel.
> Nada de dinamica, alocacao ou piloto.

## Por que este e o primeiro commit

E a peca de **menor risco e maior valor de verificacao imediata**, testavel em isolamento, sem
dependencia de turbina, dinamica, controlador, CAD, dados humanos, CFD ou JSBSim.

E e exatamente a que motivou a correcao mais seria de todo o processo de revisao: agregar inercias
sem alinhar referenciais e pontos de referencia. Ver [[Propriedades de massa]].

## Entregavel

```
 1. pyproject.toml, venv, git init, ruff, pytest, nox
 2. units.py                      - SI interno, conversao e validacao de dimensao na fronteira
 3. provenance.py                 - schema pydantic, hash de fonte, docs/sources/
 4. MassComponent                 - dataclass congelado
 5. aggregate_mass_properties()   - massa, centro, rotacao de tensor, eixos paralelos
 6. test_tensor_rotation          - caso analitico de rotacao
 7. test_parallel_axis            - caso analitico de translacao
 8. test_aggregate_known_solution - conjunto de componentes com resultado fechado
 9. EventSchedule                 - agenda de eventos agendados, sem guardas ainda
10. telemetry.py                  - esqueleto de registro de evento
```

## Criterio de sucesso

- `nox -s lint test` verde
- Os tres testes analiticos de massa passam com tolerancia numerica apertada
- O teste de alinhamento de evento passa: falha em 0,105 s com passo maximo de 10 ms e controlador a
  100 Hz e aplicada em **0,105 s**, nao em 0,110 s. Ver [[Tres classes de teste]], classe C
- Teste de fumaca roda em menos de 30 segundos sem nenhuma dependencia pesada instalada

## Casos analiticos obrigatorios

Ver [[Casos analiticos]] para as solucoes fechadas:

- Haltere: `diag(0, m L^2 / 2, m L^2 / 2)`
- Quatro massas em quadrado: `diag(m a^2, m a^2, 2 m a^2)`
- Barra montada de duas meias-barras: tem que dar `M L^2 / 12`
- Componente rotacionado: resultado identico, pega troca entre `R` e transposta de `R`

## O que NAO entra neste marco

Dinamica, integrador, propulsao, controlador, piloto, guardas de evento, CAD.

## Ligacoes

[[Propriedades de massa]] · [[Regras de unidades]] · [[Regras de procedencia]] ·
[[Regras de tempo e eventos]] · [[Marco 1 - Envelope]]
