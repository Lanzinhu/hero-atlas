---
tags: [dados, propulsao, referencia]
atualizado: 2026-09-11
nota: dados de catalogo, precisam de copia arquivada antes de virar teste
---

# Microturbinas disponiveis no mercado

> Dados de fabricante e revendedor. Ver [[Regras de procedencia]]: ficha e evidencia forte para
> massa e dimensao, razoavel para empuxo em condicao especificada, **nenhuma** para resposta
> transitoria.

## Tabela comparativa

| Modelo | Empuxo | Massa | Consumo maximo | TSFC calculado | Preco |
|---|---|---|---|---|---|
| Xicoy X45 | 45 N / 4,5 kgf | 400 g | 145 g/min | 1,93 | cerca de 700 a 900 euros |
| Swiwin SW60B | 60 N / 6 kgf | cerca de 1,0 kg | 164 g/min | 1,64 | cerca de 1.300 dolares |
| Kingtech K-180G5 | 176 N / 18 kgf | 1.540 g | 560 g/min | 1,87 | cerca de 2.800 dolares |
| JetCat P220-RXi | 231 N / 23,6 kgf | cerca de 2,0 kg | - | - | cerca de 5.500 dolares |
| Swiwin SW300B | 300 N / 30 kgf | cerca de 2,8 kg | - | - | 3.775 a 3.900 dolares |
| **Kingtech K-320G5** | 314 N / 32 kgf | 2,9 kg | 870 g/min | **1,63** | **4.230 dolares** |
| AMT Titan | 392 N / 40 kgf | cerca de 2,9 kg | - | - | 9 a 12 mil euros |
| **JetCat P400-PRO-LN** | **397 N / 40,5 kgf** | **3.650 g** | **1.300 mL/min (1,04 kg/min)** | **1,54** | **10.748 euros** |
| AMT Nike | 784 N / 80 kgf | 9.150 g motor, 11.300 g sistema | 1.850 g/min | **1,39** | 28.314 euros |

TSFC em kg por kgf por hora, calculado a partir dos dados publicados.

⚠ Comparacao com turbofan comercial, que costuma ficar em 0,35 a 0,60: os valores de catalogo
destas microturbinas sao muito superiores. **A comparacao e indicativa e nao representa
equivalencia de condicao operacional.** TSFC varia com velocidade, altitude, ponto de operacao e
arquitetura; comparar microturbina em bancada estatica com turbofan em cruzeiro compara missoes
diferentes.

## Leituras de engenharia

### Escala melhora o TSFC nesta amostra

Do X45 (1,93) ao Nike (1,39) ha ganho de cerca de **28 por cento** subindo 18 vezes em tamanho.

⚠ Isso sugere um trade-off relevante, mas **nao estabelece monotonicidade universal** entre
fabricantes, pontos operacionais ou arquiteturas. E observacao de amostra de catalogo, nao lei.

Isso favorece **poucas turbinas grandes** sobre muitas pequenas, exatamente o oposto do que a
redundancia exige. **Este e o trade-off central do projeto de um traje.**

### Custo por kgf

| Fabricante | Custo por kgf |
|---|---|
| Kingtech K-320G5 | 132 dolares |
| Swiwin SW300B | 126 dolares |
| JetCat P400 Pro | 265 euros |
| AMT Nike | 354 euros |

Turbinas asiaticas custam cerca de metade por kgf. As europeias vendem confiabilidade, suporte e
tempo entre revisoes.

### Conjunto tipo Gravity, 144 kgf

- 5 JetCat P400 Pro (202 kgf): cerca de **53.700 euros** so em motores
- 5 Kingtech K-320G5 (160 kgf): cerca de **21.150 dolares**

Contra preco de traje de 340 mil libras, os motores sao **12 a 15 por cento** do preco. O resto e
pesquisa amortizada, estrutura, integracao, exclusividade e margem.

### Relacao empuxo por peso das proprias turbinas

P400 Pro da 11 para 1. Nike da 7 para 1. K-320 da 11 para 1.
A literatura cita mais de 5 para 1 como caracteristico da classe.

### Operacao

Todas queimam Jet A-1 com cerca de 5 por cento de oleo, lubrificacao por mistura, sem sistema de
oleo separado. Temperatura de gases de escape entre **480 e 750 graus C**.

## O que o catalogo NAO diz

**A resposta a degraus pequenos**, que e o numero que decide este projeto.
Ver [[Propulsao e atraso]].

Catalogos publicam "marcha lenta a maximo em 1 a 3 s", que e o degrau grande. Para estabilizacao o
que importa e a constante de tempo local em torno do ponto de operacao, e ela nao esta em lugar
nenhum.

## Ligacoes

[[Propulsao e atraso]] · [[Autonomia e energia]] · [[Estado da arte - trajes de voo]]
