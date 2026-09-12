---
tags: [visao, escopo]
atualizado: 2026-09-11
---

# Escopo e nao-escopo

## Escopo

- Simulador de dinamica e controle, em Python, com NumPy e SciPy
- Estudo de viabilidade com procedencia rastreavel
- Analise de trim, alocacao, autoridade, atraso, falha e piloto no laco
- CAD parametrico e analise estrutural apenas a partir do [[Marco 8 - CAD e estrutura]]

## Nao-escopo

- Qualquer hardware
- Compra de turbina, bateria, controlador ou bancada
- Qualquer software pago. Custo **zero**, so livre
- Conclusao sobre pilotabilidade real por pessoa real.
  Ver [[R-04 - Resultado humano e condicional]]

## Restricoes de ambiente

| Item | Estado |
|---|---|
| Python | 3.12.10, instalado |
| git | 2.55, instalado |
| WSL | **nao instalado** |
| OpenFOAM, ArduPilot SITL | dependem de WSL, marcos tardios e opcionais |
| acados | nao instalar no Windows, exige cadeia C. Usar CasADi |
| Blender | so render, nao exporta STEP, nao serve para peca com tolerancia |

## Principio de isolamento do nucleo

```
Nucleo (trim, alocacao, dinamica, controle, analise)
   consome
Deck com envelope pessimista-nominal-otimista e escopo de validade declarado
   produzido por
Ficha de fabricante, estimativa analitica, pyCycle, CFD, FEM, futuro ensaio de bancada
```

O nucleo importa **apenas** NumPy, SciPy, pandas e pydantic. Ferramentas pesadas nunca sao
importadas por ele. O simulador roda no primeiro dia e continua rodando se nada pesado for
instalado.

## Tres familias de veiculo, sem requisito compartilhado

| Familia | Propulsao | Limitacao dominante |
|---|---|---|
| Traje com microturbinas | Querosene | Atraso, calor, consumo, ruido |
| Traje eletrico | Bateria com rotores ou ventiladores | Densidade energetica e massa |
| Mochila dorsal | Qualquer uma | Centro de massa e estrutura |

A mesma forca de empuxo tem custos completamente diferentes entre elas. Comparacao so por metricas
normalizadas.

## Ligacoes

[[MOC - Hero Atlas]] · [[Indice de marcos]]
