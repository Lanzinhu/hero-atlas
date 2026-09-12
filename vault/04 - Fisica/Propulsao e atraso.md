---
tags: [fisica, propulsao, risco]
atualizado: 2026-09-11
---

# Propulsao e atraso

> **O atraso do atuador decide o projeto e e o pior conhecido.** Nenhum fabricante publica a
> resposta a degraus pequenos, que e exatamente o que importa na estabilizacao.

## O modelo

Nao e constante de primeira ordem simples:

```
Tdot = clip( (T_ss(u) - T) / tau(T, u, h) , -Tdot_down_max , +Tdot_up_max )

sujeito a  T >= T_marcha_lenta
com atraso discreto de ECU aplicado ao comando
```

A constante de tempo depende do **ponto de operacao**, nao so do tamanho do degrau, porque a inercia
do rotor e a margem de surge mudam ao longo da faixa. Subida e descida tem limites distintos.

## Interface comum turbina e eletrico

```python
class ThrustSource(Protocol):
    def thrust_max_N(self, atm) -> float: ...
    def thrust_steady_N(self, u, atm) -> float: ...
    def step(self, u_cmd, dt, atm) -> None: ...
    @property
    def thrust_N(self) -> float: ...
    def consumption_rate(self) -> float: ...   # kg/s ou W
    def spool_momentum(self) -> float: ...     # I*Omega, para o giroscopico
    def health(self): ...                      # OK | FLAMEOUT | DERATED
```

## Regra de ouro do envelope

**Proibido por convencao qualquer resultado com tau unico.** A analise de estabilidade sempre
devolve uma **curva sobre o envelope de tau**, e o entregavel e o **tau critico** onde a margem de
ganho cai abaixo de 6 dB.

```yaml
actuator_delay:
  pessimistic: ...
  nominal: ...
  optimistic: ...
  provenance: ...
```

## Orcamento de fase: a conta que explica tudo

Planta de taxa:

```
omega(s)/M_cmd(s) = 1/(I*s) * 1/(tau_act*s + 1) * exp(-T_d*s)

Fase em omega_c = -90 graus - atan(omega_c*tau_act) - omega_c*T_d
Para margem de fase de 45 graus:  atan(omega_c*tau) + omega_c*T_d = 0,785 rad
```

| Arquitetura | tau_act | T_d | **omega_c maximo** |
|---|---|---|---|
| Eletrico com fly-by-wire | 0,08 s | 0,01 s | **10,2 rad/s** |
| Turbina com fly-by-wire, degraus pequenos | 0,15 s | 0,03 s | **4,9 rad/s** |
| Turbina com fly-by-wire, degraus grandes | 0,50 s | 0,03 s | **1,8 rad/s** |
| Turbina com piloto humano puro | 0,50 s | 0,20 s | **1,15 rad/s** |

O modelo de crossover de McRuer diz que um humano atinge 2 a 4 rad/s numa planta bem comportada.
**Aqui a planta limita a 1,15 rad/s.**

Esse numero e a explicacao quantitativa de por que o Gravity exige atleta e por que JetPack Aviation
e Zapata puseram computador no laco.

## Ligacoes

[[Microturbinas disponiveis]] · [[ADR-003 - Efetividade dinamica no alocador]] ·
[[ADR-004 - Margem estatica e dinamica]] · [[Modelo de piloto]]
