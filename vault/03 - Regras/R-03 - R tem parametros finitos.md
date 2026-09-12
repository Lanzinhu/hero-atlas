---
tags: [regra, campanha]
regra: R-03
estado: ativa
data: 2026-09-11
---

# R-03 - R explora parametros finitos e declarados, nao uma funcao de postura

## O problema

O vetor de R mistura naturezas muito diferentes, e `q_bracos` e **funcao temporal, nao numero**.

Explorar uma funcao como se fosse dimensao de Monte Carlo e dimensao infinita disfarcada.
A matematica nao reclama. O computador e o cronograma reclamam.

## A regra: tres classes separadas

### Arquitetura fixa

Nao muda dentro de uma campanha:

- numero e posicao nominal dos motores
- sentido de giro de cada rotor
- tipo de propulsor
- posicao estrutural do tanque
- geometria dos bocais
- tipo de controlador
- ponto de referencia `O`

### Parametros incertos e operacionais

Explorados por Sobol ou hipercubo latino:

- atraso de turbina
- taxas maximas de subida e descida
- perda de instalacao
- massa de combustivel e massa total
- centro de gravidade
- vento e erro de sensor
- atraso humano e ganho humano
- limite de braco
- residuo termico

### Postura e trajetoria

Parametrizadas por poucos valores interpretaveis:

```yaml
arm_pose:
  shoulder_pitch_rad: ...
  shoulder_roll_rad: ...
  elbow_flexion_rad: ...
  symmetry_mode: symmetric | asymmetric

arm_trajectory:
  template: quintic_transition
  initial_pose: ...
  final_pose: ...
  duration_s: ...
```

O template quintico nao e capricho: ele da continuidade de segunda ordem, que
[[Cinematica de braco]] exige para nao gerar torque artificial.

## Ligacoes

[[ADR-006 - Exploracao de R]] · [[Pergunta central R]] · [[Cinematica de braco]]
