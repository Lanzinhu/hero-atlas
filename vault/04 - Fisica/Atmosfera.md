---
tags: [fisica, ambiente]
atualizado: 2026-09-11
---

# Atmosfera, sem dupla contagem

## O erro que esta nota evita

Uma versao anterior multiplicava razao de densidade por uma penalidade termica generica.
**Densidade ja depende de temperatura**, porque `rho = p / (R * T)`. Multiplicar as duas penaliza a
mesma fisica duas vezes.

## A forma correta

Primeiro o estado atmosferico completo, depois so o que a densidade nao cobre:

```
p(h),  T(h, dT),  rho(h, dT) = p / (R * T)
T_bruto = f(u, p_amb, T_amb, V_entrada)
```

## Verificacao numerica

| Condicao | Razao de densidade |
|---|---|
| 1000 m, ISA padrao | 0,907 |
| 1000 m, ISA mais 15 K, mesma pressao | **0,862** |

O termo termico adicional cobre apenas o efeito **residual** de limite de temperatura de entrada da
turbina, que e real mas menor: **0,95 a 0,97**.

Produto final entre **0,82 e 0,84**, proximo do 0,81 antigo por coincidencia, agora derivado
corretamente.

```yaml
ambient_model:
  method: full_state_plus_residual_engine_term
  density_model: ISA_plus_delta_T
  residual_temperature_correction:
    enabled: true
    justification: >
      Limite de temperatura de entrada da turbina e perda de eficiencia que a razao
      de densidade ja nao captura. Nao repete o efeito de densidade.
```

## Cenarios nomeados, cada um calculado

| Cenario | Altitude | Temperatura |
|---|---|---|
| Referencia | nivel do mar | ISA (vale 1,00 por definicao) |
| Missao nominal | 1.000 m | ISA |
| Dia quente | 1.000 m | ISA mais 15 K |
| Adverso | altitude mais calor mais instalacao degradada | definido |

A distribuicao nasce de **cenario fisico**, nao de preferencia narrativa. Nao existe um "nominal"
ambiguo.

## Ligacoes

[[Forca requerida x capacidade de entrega]] · [[Propulsao e atraso]]
