---
tags: [dados, referencia, benchmark]
atualizado: 2026-09-11
nota: numeros de referencia, precisam de copia arquivada em docs/sources antes de virar teste
---

# Estado da arte - trajes de voo pessoal

> **Atencao de procedencia.** Estes numeros vieram de pesquisa web e ainda **nao tem copia
> arquivada com hash**. Ate terem, nao podem virar teste de regressao.
> Ver [[Regras de procedencia]] e [[Nivel de evidencia]].

## Resumo comparativo

| Sistema | Propulsao | Empuxo total | Massa vazia | Autonomia | T/W | Preco |
|---|---|---|---|---|---|---|
| Gravity Jet Suit Mk2/Mk3 | 5 microturbinas, 4 nos bracos e 1 nas costas | cerca de 144 kgf (1.414 N) | 25 a 27 kg mais 8 a 16 kg de combustivel | 3,5 a 5 min | 1,18 a 1,25 bruto | 340 mil libras |
| JetPack Aviation JB-10 | 2 turbojatos | 179 kgf (395 lbf) | 38 kg | 8 min | cerca de 1,40 | sob consulta |
| JetPack Aviation JB-11 | 6 turbojatos | 240 kgf (530 lbf) | 52 kg | 10 min | cerca de 1,48 | sob consulta |
| JetPack Aviation JB-12 | 6 turbojatos de 88 lbf | 239 kgf (528 lbf) | 48 kg | 8 min | cerca de 1,52 | 400 mil dolares |
| Zapata Flyboard Air | 5 turbinas Jet A-1 | nao publicado | nao publicado | cerca de 10 min | nao publicado | nao vendido |
| Jetson ONE | 8 motores eletricos, 88 kW | cerca de 2.060 N | 55 kg vazio | 17 a 20 min alegado | 1,7 a 2,0 | 98 a 128 mil dolares |
| Martin Jetpack P12 | 2 ventiladores, V4 200 hp gasolina | mais 50 kgf em 330 kg | 200 kg | 28 a 30 min | cerca de 1,15 | empresa fechou em 2019 |

## Gravity Industries: a analise que importa

### Configuracao

Cinco microturbinas: **duas em cada braco mais uma nas costas**. Os bracos fazem simultaneamente
sustentacao, controle de atitude e controle direcional, por vetorizacao via posicao corporal.
Estrutura quase toda impressa em 3D, com suportes de braco em titanio.

### O modelo exato das turbinas nunca foi divulgado

A associacao com JetCat P400 que circula na internet vem do **Jetman de Yves Rossy**, cuja asa usa
4 unidades P400. Sistema diferente.

Engenharia reversa: 144 kgf dividido por 5 da **28,8 kgf por turbina**, o que **exclui** a P400 Pro
(40,5 kgf) e aponta para a classe de 280 a 300 N.

Varias fontes citam "22 kg de empuxo por motor de braco", o que com 144 kgf totais implicaria motor
dorsal de 56 kgf. Provavelmente specs de geracoes diferentes misturadas. **Tratar ambos os conjuntos
como nao verificados.**

### T/W efetivo e o numero que explica a dificuldade

Os quatro motores de braco **nao apontam para baixo** em voo. Ficam inclinados 20 a 30 graus da
vertical para gerar autoridade de controle. A componente vertical cai por cosseno.

| Parametro | Valor |
|---|---|
| Massa total com piloto de 80 kg e 20 L | cerca de 121 kg |
| T/W bruto | 1,19 |
| **T/W efetivo vertical** | **1,03 a 1,12** |

Ou seja, margem vertical real de **3 a 12 por cento** no inicio do voo com tanque cheio. Isso
explica por que o traje e notoriamente dificil e por que a Gravity so voa sobre agua ou grama, e
baixo.

### Consumo: fecha fisicamente

Consumo alegado de 4 a 4,5 L/min. Verificacao independente pelo TSFC de catalogo da JetCat P400 Pro
da **3,9 L/min** para sustentar 121 kgf. **Consistente.** Ver [[Autonomia e energia]].

Ceticismo sobre o Mk3 com 7 a 8 min: exigiria 30 a 35 L, o que derruba o T/W inicial abaixo de 1,10,
ou um ganho de TSFC de cerca de 40 por cento, improvavel nessa classe.

### Numeros que sao marketing

- "1.050 bhp": turbojatos **nao produzem potencia de eixo**. Numero construido
- Teto de 12.000 pes: **alegacao teorica nunca demonstrada**. A operacao real e de 1 a 15 m do solo
- Recorde Guinness de 2019: 136,891 km/h, esse sim verificado

## As tres filosofias de controle, incompativeis

| Sistema | Filosofia |
|---|---|
| **Gravity** | controle corporal puro, **zero computador de estabilizacao**, T/W minimo, dificuldade maxima |
| **Zapata** | corpo mais fly-by-wire com redundancia tripla, auto-hover, eletronica independente por turbina |
| **JetPack Aviation** | vetorizacao de motor inteiro mais computador de gerenciamento de empuxo, 6 motores |

As duas ultimas **convergiram para o computador no laco**. A primeira e demonstracao de virtuosismo
humano, nao caminho de produto. O EZ-Fly da Zapata existe explicitamente para reduzir o treinamento
necessario, delegando mais ao computador.

Isso alimenta diretamente [[Modelo de piloto]].

## Modos de falha conhecidos

| Modo | Detalhe |
|---|---|
| Flameout de turbina | perder 1 de 5 e menos 20 por cento de empuxo **mais** momento assimetrico |
| Oscilacao induzida pelo piloto | atraso de turbina mais autoridade vertical de 0,1 g |
| Falha de sensor unico | caso Hoversurf em Dubai: um barometro, queda de 30 m |
| Termico | gases a 480 a 750 graus C saindo a 589 m/s |
| Combustivel | 10 a 42 L nas costas, sem tanque autosselante |
| **Ausencia de envelope de recuperacao** | sem autorrotacao, sem planeio, paraquedas balistico exige 50 a 100 m e o voo e a 1 a 15 m |

A mitigacao real e **operacional, nao tecnica**: voar baixo, sobre agua, com cabo de seguranca no
treinamento.

## Incidentes documentados

| Data | Sistema | Desfecho |
|---|---|---|
| 2020-11-17 | Jetman Dubai, 4 JetCat P400 | **fatal**, paraquedas nao acionado, causa nao explicada |
| 2022-05-28 | Zapata, prototipo | subida nao comandada mais rotacao, queda de 15 m, hospitalizado |
| 2019-07-25 | Zapata Flyboard Air | falha no reabastecimento, caiu no mar |
| cerca de 2020 | Hoversurf S3 | subiu a 30 m contra teto de projeto de 5 m, falha de barometro, aeronave destruida |
| 2021-05 | CopterPack | video do "primeiro voo" tinha cabo removido digitalmente, **falha de credibilidade** |

## Ligacoes

[[Microturbinas disponiveis]] · [[Autonomia e energia]] · [[Numeros decisivos]] ·
[[Nivel de evidencia]]
