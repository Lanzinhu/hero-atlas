---
tags: [regra, criterio]
estado: ativa
---

# "Estavel" definido operacionalmente

## O termo que se usa

**Estavel sobre o envelope de cenarios declarado.**

O produto minimo **nao** alega robustez formal no sentido de analise estruturada, mu-analise ou
IQCs. Isso pode entrar depois, e e pesado demais agora.

Sem definicao, cada notebook interpreta robustez de um jeito e "estavel" acaba significando apenas
"nao explodiu numericamente".

## O contrato computavel

Para todo cenario do envelope e toda perturbacao do conjunto declarado:

| Metrica | Criterio inicial |
|---|---|
| Inclinacao maxima | 10 graus |
| Inclinacao RMS em pairado | 2 graus |
| Desvio horizontal maximo | 1,5 m |
| Taxa angular maxima | limite biomecanico e estrutural declarado |
| Saturacao continua | proibida acima de duracao declarada |
| Velocidade vertical no solo | abaixo do limite declarado |
| Recuperacao | `norma(x(t_f) - x_trim) < eps` |

Os limiares sao **versionados em configuracao**, nunca fixos no codigo. Podem mudar; o que nao muda
e que sejam explicitos.

## "Reserva positiva" e ambiguo

Ha pelo menos quatro reservas: vertical, rolagem, arfagem e guinada. Pode haver reserva vertical
positiva sem nenhuma autoridade de guinada, ou com rolagem bloqueada pela marcha lenta, ou com
saturacao por limite de rampa.

A medida correta e a distancia do wrench requerido a fronteira do conjunto atingivel, com escala
fisica porque forca e torque tem unidades diferentes:

```
d_W = min sobre w na fronteira de || S * (w - w_req) ||

S = diag( 1/Fx*, 1/Fy*, 1/Fz*, 1/taux*, 1/tauy*, 1/tauz* )
```

O produto minimo usa substitutos mensuraveis: reserva vertical minima, reserva de torque por eixo,
fracao de atuadores saturados, distancia normalizada ao limite, e resduo do wrench com a **mesma
escala S**.

## Ligacoes

[[Alocacao de controle]] · [[ADR-004 - Margem estatica e dinamica]] · [[Pergunta central R]]
