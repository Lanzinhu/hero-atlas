---
tags: [fisica, piloto, marco-6]
atualizado: 2026-09-11
---

# Modelo de piloto

## A cadeia de atrasos, decomposta

Um unico numero de 150 a 300 ms esconde uma cadeia que **se soma**:

```
perturbacao -> percepcao -> decisao -> movimento do braco -> mudanca de geometria
            -> resposta da turbina -> torque no traje
```

| Componente | O que representa |
|---|---|
| Percepcao visual | perceber posicao, horizonte e movimento |
| Percepcao vestibular e proprioceptiva | percepcao corporal e angular |
| Decisao e neuromuscular | gerar comando muscular |
| Movimento articular | deslocamento efetivo do braco |
| Efeito propulsivo | mudanca de torque apos mover o braco |

```yaml
pilot:
  visual_delay_s: ...
  vestibular_delay_s: ...
  neuromuscular_time_constant_s: ...
  arm_rate_limit_rad_s: ...
  arm_acceleration_limit_rad_s2: ...
  shoulder_torque_limit_Nm: ...
```

Cada um com procedencia e incerteza proprias. Ver [[R-04 - Resultado humano e condicional]].

## Modelo de McRuer

```
Y_p(s) = K_p * exp(-tau_e*s) * (T_L*s + 1)/(T_I*s + 1) * 1/(T_N*s + 1)

tau_e = 0,15 a 0,30 s      T_N = cerca de 0,1 s (neuromuscular)
```

Implementacao: fila de amostras de comprimento `tau_e/dt` mais filtro discreto de primeira ordem.

## Carga biomecanica

Com cinco turbinas de cerca de 28,8 kgf, **cada braco sustenta cerca de 57,6 kgf, ou 565 N**, em
carga isometrica, enquanto executa controle de precisao.

A fadiga muscular e um limitador de tempo de voo **tao real quanto o combustivel**, e degrada a
autoridade de controle progressivamente durante o voo. Fadiga relevante em 3 a 4 minutos.

## As duas arquiteturas, comparadas explicitamente

> Provavelmente a conclusao de engenharia mais valiosa do projeto.

1. **Humano controla tudo diretamente**, sem estabilizacao automatica. E a filosofia Gravity, e e o
   que o recorde Guinness certifica: traje controlado por corpo.
2. **Humano comanda trajetoria e um computador estabiliza atitude.** E a filosofia Zapata e JetPack
   Aviation, ambas com computador no laco.

Se a primeira tiver margem minima ou nula e a segunda mudar o envelope radicalmente, **isso e
resultado, nao fracasso**. Zapata reconheceu isso ao criar o EZ-Fly com mais autoridade delegada ao
computador, com o objetivo explicito de reduzir o treinamento necessario.

## Ligacoes

[[Propulsao e atraso]] · [[Cinematica de braco]] · [[R-04 - Resultado humano e condicional]] ·
[[Marco 6 - Piloto e regiao R]]
