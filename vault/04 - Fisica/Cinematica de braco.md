---
tags: [fisica, cinematica, piloto]
atualizado: 2026-09-11
---

# Cinematica de braco

> Nesta arquitetura **o braco e o atuador**. O angulo de vetorizacao nao e um servo, e o ombro do
> piloto, com banda de 2 a 4 rad/s. E isso que separa o conceito Gravity do conceito JetPack
> Aviation, onde a vetorizacao e mecanica e rapida.

## Por que corpo rigido simples nao basta

Com quatro motores de cerca de 3,65 kg nos bracos, mover um braco muda **simultaneamente**:

- a direcao do empuxo
- o braco de alavanca do empuxo
- o centro de massa
- o tensor de inercia
- o momento angular do corpo
- a carga biomecanica no ombro
- o acoplamento entre comandos de atitude e translacao

O deslocamento e de primeira ordem, nao de segunda.

## A equacao, quando a rota espacial entrar

```
H = I(q, m_f) * omega  +  H_rel(q, qdot)

I*omegadot + omega x (I*omega) + Idot*omega + Hdot_rel + omega x H_rel = tau_externo

Hdot_rel = dH_rel/dq * qdot  +  dH_rel/dqdot * qddot
```

Ate o marco 5 esses termos **nao entram**, por decisao registrada em
[[ADR-001 - Ponto de referencia e forma da dinamica]]. A consequencia para testes esta em
[[R-01 - Conservacao com bracos moveis]].

## Derivadas fornecidas, nunca diferenciadas

Calcular `Idot` e `Hdot_rel` por diferenca finita sobre poses cria **torques artificiais enormes
exatamente durante o movimento rapido de braco**, que e o regime de interesse do estudo.

Regra: trajetorias com continuidade de segunda ordem, com posicao, velocidade e aceleracao
articulares **fornecidas analiticamente**. Diferenca finita so como teste de consistencia.

```python
@dataclass(frozen=True)
class ArmKinematics:
    joint_position_rad: NDArray
    joint_velocity_rad_s: NDArray
    joint_acceleration_rad_s2: NDArray

@dataclass(frozen=True)
class KinematicAggregate:
    mass_kg: float
    center_of_mass_body_m: NDArray
    inertia_body_kg_m2: NDArray
    inertia_rate_body_kg_m2_s: NDArray          # Idot
    relative_angular_momentum_Nm_s: NDArray     # H_rel
    relative_angular_momentum_rate_Nm: NDArray  # Hdot_rel
    nozzles: list
```

A interface e construida **completa desde o inicio**, mesmo com termos zerados, para o modelo nao
precisar ser quebrado quando a cinematica deixar de ser meramente geometrica.

## Parametrizacao da postura

Ver [[R-03 - R tem parametros finitos]]. Postura e funcao temporal, nao dimensao de Monte Carlo.

## Ligacoes

[[Propriedades de massa]] · [[Modelo de piloto]] · [[Dinamica 6-DOF]]
