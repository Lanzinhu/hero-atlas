---
tags: [regra, numerico, eventos]
estado: ativa
---

# Regras de tempo e eventos

> O Hero Atlas estuda margens estreitas. Uma retencao tratada como atraso continuo, um atraso
> fracionario arredondado ou um evento aplicado um passo tarde produz conclusao errada com
> aparencia impecavel.

## Congelar estado discreto no subpasso depende do caso

Nao existe regra geral. Ha tres casos e o projeto tera os tres.

### Caso A - Retencao de ordem zero

Com `u(t) = u[k]` para `t` em `[t_k, t_k+1)`, congelar o comando em todos os estagios de
Runge-Kutta e **exatamente correto**. E a representacao fiel da retencao, nao perda de precisao.

### Caso B - Atraso de transporte continuo

Com `u_d(t) = u(t - tau)` e comando variando continuamente, o atraso e consultado no instante de
cada estagio:

```
k1 = f( t_k,          x_k,             u(t_k - tau) )
k2 = f( t_k + dt/2,   x_k + dt/2*k1,   u(t_k + dt/2 - tau) )
k3 = f( t_k + dt/2,   x_k + dt/2*k2,   u(t_k + dt/2 - tau) )
k4 = f( t_k + dt,     x_k + dt*k3,     u(t_k + dt - tau) )
```

Congelar aqui introduz **erro de fase**, o pior erro possivel num estudo sobre margem de atraso.

### Caso C - Atraso fracionario de amostra

Controlador a 100 Hz com atraso de 35 ms sao 3,5 periodos. Exige politica declarada.
Pade serve para analise linear, nao para a simulacao principal.

## Interpolacao de atraso: tres condicoes

**Causalidade estrita.** Uma spline cubica global pode usar amostras futuras para determinar
coeficientes. Aceitavel em pos-processamento, **proibido** na simulacao causal.

**Compatibilidade com a suavidade do sinal.** Interpolar cubicamente um sinal com retencao inventa
transicoes inexistentes e pode ultrapassar limites de comando.

| Tipo de sinal atrasado | Interpolacao apropriada |
|---|---|
| Comando digital com retencao | retencao |
| Amostra digital com metodo declarado | o metodo escolhido |
| Sinal continuo suave | cubica causal ou saida densa |
| Sinal com descontinuidade | por trechos, respeitando a descontinuidade |
| Analise linear local | Pade, marcado como aproximacao |

**Atraso continuo menor que o passo e proibido no modo padrao.** Com passo maximo de 10 ms e atraso
de 3 ms, o estagio final precisa do comando em `t_k + 7 ms`, que esta dentro do passo sendo
integrado. O historico externo nao tem esse valor.

```yaml
integration:      { max_step_s: 0.002 }
delay_validation: { min_continuous_delay_s: 0.020, require_delay_greater_than_max_step: true }
delay_policy:     { fractional_method: interpolated_history, interpolation_order: cubic,
                    causality: strict }
```

A restricao e confortavel porque os atrasos humanos, de 150 a 300 ms, sao muito maiores que alguns
milissegundos.

## Dois tipos de evento

### Agendados

Conhecidos antes de integrar o intervalo: atualizacao de sensor, atualizacao de controlador,
publicacao de comando, chegada de comando atrasado, inicio e fim de rajada definida no cenario,
falha programada, mudanca de referencia, amostras de trajetoria prescrita.

```
t_{n+1} = min( t_n + dt_max , t_evento_agendado , t_final )
```

### Por guarda

Dependem do estado evoluindo dentro do passo:

```
g_max_i = T_i_max - T_i        g_fuel = m_fuel        g_omega = omega_max - ||omega||

deteccao:    g_j(t_n, x_n) * g_j(t_n+1, x_n+1) < 0
localizacao: bissecao, secante ou saida densa
```

**Por que importa:** se uma turbina satura em 1,0037 s e o integrador so percebe em 1,0050 s, o
modelo concede 1,3 ms de aceleracao impossivel. Repetido ao longo de perturbacoes, altera a
autoridade efetiva do conjunto.

**Histerese e obrigatoria.** Se o estado fica sobre a fronteira, o detector dispara a cada
microtempo e trava a simulacao.

```yaml
guard_hysteresis: { relative_band: 0.002, min_dwell_s: 0.0005 }
```

Quais guardas existem no produto minimo: ver [[ADR-005 - Saturacao e telemetria]].

## Passo irregular nao contamina coeficiente discreto

Dividir o passo na fronteira torna o incremento nao uniforme. Runge-Kutta aceita, por ser metodo de
passo unico. Mas **limite de rampa, filtro discreto e derivada por diferenca sao avaliados contra o
proprio periodo declarado**, nunca contra o passo instantaneo.

## Interpolacao do historico limita a ordem

Interpolacao linear e de segunda ordem e derruba o esquema abaixo de quarta, mesmo em caso suave.
Com atraso continuo presente, a interpolacao precisa ser **ao menos cubica** para o teste de ordem
valer.

## Estado separado por natureza temporal

O integrador do PID e equacao diferencial continua ou soma acumulada digital? As duas sao validas e
tem **fase diferente**. Por isso todo estado declara:

```yaml
time_domain: continuous | sampled | event_driven
```

## Ligacoes

[[Tres classes de teste]] · [[ADR-005 - Saturacao e telemetria]] · [[Dinamica 6-DOF]]
