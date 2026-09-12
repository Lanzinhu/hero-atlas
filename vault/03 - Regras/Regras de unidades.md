---
tags: [regra, implementacao]
estado: ativa
---

# Regras de unidades

## A regra

**SI no nucleo. Dimensao explicita na fronteira.**

Sufixo no nome da variavel ajuda, mas nao impede receber 150 em quilograma-forca onde se esperava
newton. Por isso cada campo de configuracao carrega a unidade:

```yaml
mass:        { value: 117,    unit: kg }
thrust_max:  { value: 430,    unit: N }
rotor_speed: { value: 100000, unit: rpm }
```

O carregador **valida a dimensao**, converte para SI e **rejeita unidade incompativel**.
Um campo de massa que recebe `N` falha no carregamento, nao no grafico.

## O que o nucleo ve

So SI: newton, quilograma, metro, segundo, kelvin, radiano.
Relatorios convertem de volta na saida: kgf, lbf, litro por minuto, rotacao por minuto, grau.

## Convencao de nome

Sufixo de unidade obrigatorio em assinatura publica:

```python
thrust_N          mass_kg           omega_rad_s
position_O_I_m    inertia_kg_m2     fuel_mass_kg
```

## Constantes canonicas

| Constante | Valor |
|---|---|
| g padrao | 9,80665 m/s2 |
| kgf para N | 9,80665 |
| lbf para N | 4,4482216152605 |
| Densidade do ar ao nivel do mar, ISA | 1,225 kg/m3 |
| Constante do ar seco | 287,05 J/(kg K) |

## Ligacoes

[[Regras de procedencia]] · [[Marco 0 - Fundacao]]
