---
tags: [fisica, energia]
atualizado: 2026-09-11
---

# Autonomia e energia

## Turbina: a conta, com a unidade visivel

⚠ A forma antiga, `mdot_f = TSFC * T_pairado`, e **dimensionalmente ambigua**. TSFC de catalogo
vem em `kg/(kgf*h)` e o empuxo do nucleo esta em newton. A conversao tem que aparecer:

```
mdot_f = f_TSFC( T / T_max , p , T_amb ) * T / g0        [T em N, TSFC em kg/(kgf*s)]
```

ou, preferivelmente, o deck armazena diretamente o consumo, sem passar por TSFC:

```
mdot_f = f_mdot( T , p , T_amb )
```

Depois integra ate a reserva, porque **a massa cai com o consumo**:

```
T_pairado(t) = m(t)*g / cos(theta)
dm/dt = -mdot_f
```

### ⚠ TSFC de catalogo nao vale em pairado

TSFC e `mdot_f / F`. Fora do ponto de projeto o empuxo cai, e se o fluxo de combustivel nao cair
proporcionalmente o consumo especifico **piora**. A eficiencia global tambem tende a se deteriorar
em off-design.

O TSFC publicado costuma estar associado a um ponto perto do **maximo**. Pairado com varias
turbinas ocorre em fracao de empuxo diferente, e o TSFC nessa regiao **nao pode ser presumido
constante**.

Consequencia: usar TSFC de catalogo como aproximacao de pairado **nao e conservador por padrao**.
Pode subestimar o consumo.

### A verificacao antiga, rebaixada

Com os dados de catalogo da JetCat P400 Pro (1,04 kg/min para 40,5 kgf, TSFC 1,54):

```
Para sustentar 121 kgf, a TSFC constante:  121 * 1,54 = 186 kg/h = 3,1 kg/min = 3,9 L/min
```

Isso fica na mesma ordem de grandeza dos 4 a 4,5 L/min declarados pela Gravity. ⚠ Mas **nao e
validacao**, e sim coerencia de ordem de grandeza sob a hipotese de TSFC constante, que e
justamente a hipotese em duvida.

O marco 1 nao devolve autonomia pontual. Devolve **banda**:

```
t_autonomia pertence a [ t_min , t_max ]
```

condicionada a uma familia explicita de curvas de carga parcial, declarada em
[[Deck de propulsao instalada - schema]].

## Eletrico: a lei do disco atuador

```
v_i  = raiz( T / (2*rho*A) )
P_id = T * v_i
P_el = P_id / (FM * eta_motor)      FM = 0,70,  eta = 0,88  ->  eta_total = 0,616
t    = (m_bateria * e_pack * DoD) / P_el
```

Com pack de 180 Wh/kg e profundidade de descarga de 85 por cento, sobram **153 Wh/kg uteis**.

### Mochila de 2 rotores de 0,90 m, area 1,27 m2

| Bateria | Massa total | P eletrica | **Autonomia** |
|---|---|---|---|
| 15 kg | 120 kg | 37,1 kW | **3,7 min** |
| 25 kg | 130 kg | 41,9 kW | **5,5 min** |
| 35 kg | 140 kg | 46,8 kW | **6,9 min** |
| 50 kg | 155 kg | 54,6 kW | **8,4 min** |

**Retorno decrescente brutal:** triplicar a bateria so dobra a autonomia, porque `P` cresce com
`m^1,5` e **cada quilo de bateria carrega a si mesmo**.

### A variavel que realmente manda e a area, nao a bateria

Para sustentar 981 N com 30 kg de bateria:

| Area de disco | Equivalente | **Autonomia** |
|---|---|---|
| 0,5 m2 | 2 dutos de 0,56 m | 6,1 min |
| 1,3 m2 | CopterPack | 9,9 min |
| 3,0 m2 | 4 rotores de 0,98 m | 15,0 min |
| 6,0 m2 | Jetson ONE | 21,2 min |
| 12,0 m2 | helicoptero ultraleve | 30,0 min |

> **Autonomia eletrica e funcao da envergadura, nao da bateria.**
> Nao existe "mochila eletrica de 30 minutos". Existe "aeronave de 3 m de diametro de 30 minutos".

## O insight central: por que jato ganha na mochila

| Sistema | Velocidade de esteira | **Potencia por newton** |
|---|---|---|
| Microturbina JetCat P400 | 589 m/s | **294,5 W/N** |
| CopterPack | 20,2 m/s | 20,2 W/N |
| Jetson ONE | 12,2 m/s | **12,2 W/N** |

Um traje a jato gasta **cerca de 24 vezes mais potencia por newton** de sustentacao que um
multirrotor.

E ainda assim empata em autonomia por quilo de "tanque":

- Jet A-1 em microturbina: 10 kg de combustivel dao cerca de 3,2 min
- Lition em rotor de 1,27 m2: 10 kg de bateria dao cerca de 2,6 min

O querosene tem cerca de **65 vezes** mais Wh/kg que a bateria, mas a turbina desperdica cerca de
95 por cento disso em energia cinetica de ar. **As duas ineficiencias quase se cancelam.**

> A diferenca real e **geometrica**: a turbina faz isso em 0,04 m2 de bocal. O eletrico precisa de
> 1,3 m2.

## E o inverso? Traje a jato eletrico?

Para replicar 5 min com a mesma carga de disco dos bocais seriam necessarios cerca de 48 kWh, ou
**cerca de 315 kg de bateria**. Fisicamente impossivel por cerca de tres ordens de grandeza.

## Ligacoes

[[Numeros decisivos]] · [[Estado da arte - trajes de voo]] · [[Microturbinas disponiveis]]
