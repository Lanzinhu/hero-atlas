---
tags: [fisica, envelope, marco-1]
atualizado: 2026-09-11
---

# Forca requerida nao e capacidade de entrega

> A atmosfera **nao faz o traje precisar de mais forca** para equilibrar o peso.
> Ela faz os motores **entregarem menos**.

Confundir as duas leva alguem a ler "175 kgf instalados" como se os motores ja tivessem sido
escolhidos, quando 175 kgf e uma exigencia de projeto num cenario.

## As quatro grandezas

```
T_efetivo_requerido  = m*g / cos(theta) * k_reserva          <- fisica do equilibrio
T_efetivo_disponivel = soma_i T_i_ref * eta_motor(p,T,V) * eta_instalacao * eta_interacao
lambda_T             = T_efetivo_disponivel / T_efetivo_requerido

T_referencia_instalado_necessario = T_efetivo_requerido / eta_total_cenario
```

```python
thrust_effective_required_N    # forca fisica necessaria no ar
thrust_effective_available_N   # o que o conjunto entrega naquele cenario
thrust_reference_installed_N   # capacidade nominal em condicao de referencia
thrust_margin_ratio            # lambda_T
```

## Exemplo de referencia: piloto de 80 kg

Piloto 80 kg, traje 25 kg, combustivel 12 kg, total **117 kg**, peso 1147 N.

| Etapa | Fator | Resultado | Significado |
|---|---|---|---|
| Peso | - | 117,0 kgf | - |
| Cosseno do braco a 25 graus | /0,906 | 129,1 kgf | forca efetiva de equilibrio |
| Reserva provisoria | x1,10 | **142,0 kgf** | **exigencia fisica de empuxo efetivo** |
| Missao nominal, eta = 0,90 | /0,90 | 157,8 kgf | quanto instalar em referencia |
| Quente e alto, eta = 0,81 | /0,81 | 175,3 kgf | idem, cenario adverso |

## O cosseno e modelo de ordem zero

Serve ao [[Marco 1 - Envelope]] e sobrevive depois **apenas como verificacao de ordem de
grandeza**. A partir do [[Marco 2 - Trim e autoridade]] a fonte de verdade e [[Trim]] resolvido,
porque cada propulsor tem direcao, posicao, limites, eficiencia e falha proprios.

## A reserva de 10 por cento e marcador provisorio

```
T_efetivo_disponivel >= T_trim + dT_perturbacao + dT_manobra + dT_falha
```

```yaml
control_reserve:
  method: provisional_fraction
  value: 0.10
  replacement_milestone: M2_trim_and_authority
```

Depois do marco 2 a fracao fixa e **substituida** por margem calculada a partir do conjunto de
forcas atingiveis. O marcador existe so para o marco 1 nao ficar bloqueado.

## Ligacoes

[[Atmosfera]] · [[Trim]] · [[Numeros decisivos]] · [[Autonomia e energia]]
