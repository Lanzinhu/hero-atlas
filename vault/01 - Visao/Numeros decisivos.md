---
tags: [visao, nucleo]
atualizado: 2026-09-11
---

# Os numeros que decidem

Nenhum deles aparece num desenho de peca. Por isso o projeto comeca por fisica, nao por CAD.

## Quatro decidem a controlabilidade do pairado

### 1. Relacao entre empuxo disponivel e peso

| Sistema | T/W |
|---|---|
| Gravity Jet Suit, bruto | 1,19 a 1,23 |
| Gravity, efetivo apos cosseno dos bracos | 1,03 a 1,14 |
| JetPack Aviation JB-12 | 1,48 a 1,52 |
| Jetson ONE, eletrico | 1,7 a 2,0 |
| Minimo que a comunidade de drones aceita como "controlado" | 2,0 |
| Drone de corrida | 10 a 14 |

Um traje tripulado opera com **margem cerca de dez vezes menor** que um drone de corrida, e em
varios casos abaixo do minimo que a propria comunidade de drones considera pilotavel.

A 1,1 de T/W a aceleracao vertical disponivel e **0,1 g**. Para deter uma descida de 3 m/s sao
precisos cerca de 3 segundos e 4,5 m de altura. Voando a 2 m do solo nao existe recuperacao.

### 2. Atraso do atuador

| Atuador | Marcha lenta a maximo |
|---|---|
| Microturbina | 1 a 3 s |
| Motor eletrico | cerca de 0,1 s |

O que importa para estabilizacao nao e o degrau grande do catalogo, e sim a resposta a **degraus
pequenos**, que nenhum fabricante publica. Ver [[Propulsao e atraso]].

### 3. Autoridade de momento

Gerar forca vertical nao basta. E preciso gerar torque suficiente nos tres eixos, **inclusive com
um propulsor apagado**. Ver [[Alocacao de controle]] e [[ADR-004 - Margem estatica e dinamica]].

### 4. Taxa maxima de variacao do empuxo

Separada da constante de tempo. E ela que satura o controlador na perturbacao forte.

## Uma quinta familia decide a utilidade operacional

**Massa, energia e consumo.** Nao e questao secundaria.

- Turbina: massa de combustivel, consumo, tempo de voo
- Eletrico: energia da bateria, massa da bateria, empuxo necessario, mais massa, num laco que pode
  nao convergir

Ver [[Autonomia e energia]].

## Ligacoes

[[Pergunta central R]] · [[Forca requerida x capacidade de entrega]] · [[Estado da arte - trajes de voo]]
