---
tags: [adr, eventos, escopo]
adr: 005
estado: aceita
data: 2026-09-11
---

# ADR-005 - Saturacao e limite de rampa sao telemetria, nao guarda

## Contexto

Uma revisao anterior sofisticou demais e transformou toda saturacao em evento por guarda com
localizacao de raiz. Isso constroi um automato hibrido grande cedo demais e cria risco de disparo
repetido na fronteira.

A equacao ja modela o limite:

```
Tdot = clip( (T_ss(u) - T) / tau , -Tdot_down_max , +Tdot_up_max )
sujeito a T >= T_marcha_lenta
```

## Decisao

Para o produto minimo basta:

1. limitar o comando
2. cortar a taxa na equacao diferencial
3. projetar o empuxo no intervalo fisico em excesso numerico pequeno
4. **registrar a ativacao do limite como telemetria**

| Evento | Tratamento no produto minimo |
|---|---|
| Falha programada | agendado |
| Falha detectada por limiar | guarda |
| Combustivel zerado | guarda |
| Contato com solo | guarda |
| Troca de modo de controle | agendado ou guarda |
| Rajada predefinida | agendado |
| Saturacao de empuxo | projecao mais registro |
| Limite fisico de rampa | corte na equacao mais registro |
| Saturacao de comando da ECU | limitacao discreta mais registro |

## Quando guardas de saturacao entram

Quando houver motivo concreto: modo de protecao da ECU, limite termico, protecao contra surge,
modelo por regimes, ou necessidade de medir com precisao extrema o tempo no limite.

Histerese e tempo minimo entre eventos continuam declarados para as guardas que existem.
Ver [[Regras de tempo e eventos]].

## Ligacoes

[[Regras de tempo e eventos]] · [[Propulsao e atraso]] · [[Telemetria]]
