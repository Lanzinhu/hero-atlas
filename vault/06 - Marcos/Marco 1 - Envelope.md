---
tags: [marco]
marco: 1
prazo: 1 semana
estado: entregue
entregue_em: 2026-09-12
---

# Marco 1 - Envelope

## Pergunta

**O conceito fecha na conta?** Quanto empuxo, quanta massa, quantos minutos.

## Entregavel

- Envelope de massa e forca efetiva requerida
- Laco de fechamento de massa por ponto fixo
- Autonomia integrada para turbina e eletrico
- Tres familias de veiculo separadas, sem requisito compartilhado

## Criterio de sucesso

Devolve **faixa** de empuxo necessario, nunca numero unico. E reproduz os benchmarks dentro da
tolerancia do nivel de procedencia de cada um. Ver [[Nivel de evidencia]].

Referencia de calibracao: piloto de 80 kg, traje de 25 kg, combustivel de 12 kg tem que dar
**142,0 kgf de exigencia fisica de empuxo efetivo**. Ver
[[Forca requerida x capacidade de entrega]].

## Saida esperada

Tabela no terminal mais grafico de T/W contra massa do piloto e combustivel, com a linha de
viabilidade, mais grafico de autonomia contra diametro de rotor cruzando a linha da turbina.

O fator de crescimento de massa, isto e a derivada da massa bruta em relacao a carga paga, e a saida
mais informativa. **Acima de 4 o conceito e fragil.**

## ⚠ Resultado, calculado pelo codigo

### Exigencia fisica, que **nao** depende de atmosfera

Massa bruta de 117 kg com bocais a 25 graus: **142,0 kgf** de empuxo efetivo.

### Capacidade a instalar, que **depende** de atmosfera

| Cenario | Razao de densidade | Instalar |
|---|---|---|
| Referencia | 1,0000 | 142,0 kgf |
| Missao nominal, 1000 m | 0,9075 | 156,5 kgf |
| Dia quente, 1000 m ISA+15 | 0,8616 | 164,8 kgf |
| Adverso, 2000 m ISA+20 | 0,7659 | 185,4 kgf |

### Autonomia eletrica e funcao da area, nao da bateria

Sustentando 100 kg com 30 kg de bateria:

| Area de disco | Equivalente | Autonomia |
|---|---|---|
| 0,5 m2 | 2 dutos de 0,56 m | 6,1 min |
| 1,3 m2 | mochila de 2 rotores de 0,90 m | 9,9 min |
| 3,0 m2 | 4 rotores de 0,98 m | 15,0 min |
| 6,0 m2 | classe Jetson | 21,2 min |
| 12,0 m2 | ultraleve | 30,0 min |

### O retorno decrescente, medido

Mochila de 1,27 m2, massa seca de 105 kg:

| Bateria | Autonomia | Bateria relativa | Autonomia relativa |
|---|---|---|---|
| 15 kg | 3,7 min | 1,00 | 1,00 |
| 25 kg | 5,5 min | 1,67 | 1,48 |
| 35 kg | 6,9 min | 2,33 | 1,85 |
| 50 kg | 8,4 min | 3,33 | **2,27** |

**Triplicar a bateria nao chega a dobrar e meio a autonomia.**

### ⚠ Um achado novo: integrar muda o numero

O vault estimava autonomia de turbina pela taxa inicial constante. Integrando, porque a massa cai
enquanto queima e o empuxo de pairado cai junto:

| Metodo | Autonomia |
|---|---|
| Taxa constante inicial | 4,67 min |
| **Integrada** | **5,01 min** |

Ganho de 7,3 por cento. O fluxo cai de 3,43 para 2,97 kg/min ao longo do voo. Estimar pela taxa
inicial **subestima** a autonomia, e o vault fazia isso.

## Ligacoes

[[Forca requerida x capacidade de entrega]] · [[Autonomia e energia]] · [[Atmosfera]]
