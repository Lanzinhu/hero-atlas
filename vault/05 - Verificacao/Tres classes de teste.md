---
tags: [verificacao, numerico]
atualizado: 2026-09-11
---

# Tres classes de teste numerico, nunca misturadas

> Runge-Kutta de quarta ordem **nao implica** sistema hibrido de quarta ordem.

Saturacao por corte, limites de rampa, retencao, eventos discretos, falha de propulsor, troca de
modo, comando por trecho, rajada abrupta, controlador digital, limite de torque humano e retrim
tornam a solucao **nao diferenciavel** nesses pontos. A ordem global observada cai abaixo de quatro
**mesmo com integrador correto**.

Exigir ordem quatro do sistema inteiro produz um teste que falha por motivo certo, o que treina
qualquer pessoa a desliga-lo.

## Classe A - Ordem do integrador

Casos **suaves, continuos e sem eventos**:

- queda livre
- torque suave e continuo
- empuxo senoidal
- trajetoria de braco com continuidade de segunda ordem
- propulsao sem saturacao
- controlador continuo sem retencao

```
E(dt) proporcional a dt^4
```

**So vale** se a interpolacao do historico for causal e de ordem suficiente.
Ver [[Regras de tempo e eventos]].

## Classe B - Convergencia de metrica em sistema hibrido

Malha fechada com eventos, limites e controlador discreto.

O objetivo **nao e** provar ordem quatro. E verificar que metricas convergem sob refino:

```
| M(dt/2) - M(dt/4) | < eps_M
```

Metricas: pico de inclinacao, tempo de recuperacao, consumo de reserva, instante de saturacao,
margem de estabilidade estimada, frequencia de oscilacao, erro RMS de posicao.

## Classe C - Alinhamento de evento

**Separado da convergencia.**

Caso canonico: falha agendada em `t = 0,105 s`, passo maximo de 10 ms, controlador a 100 Hz.
O evento tem que ser aplicado em **0,105 s**, nao adiado para 0,110 s.

> O simulador nao pode ganhar nem perder 5 ms de atraso porque a malha temporal foi
> inconvenientemente escolhida.

O mesmo teste vale para guarda: a saturacao detectada cai no instante da raiz, nao na fronteira do
passo.

Este teste **ja e implementavel no [[Marco 0 - Fundacao]]**, so com a agenda de eventos, sem
nenhuma dinamica.

## Ligacoes

[[Invariantes por caso]] · [[Casos analiticos]] · [[Regras de tempo e eventos]]
