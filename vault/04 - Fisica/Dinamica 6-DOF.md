---
tags: [fisica, dinamica, nucleo]
atualizado: 2026-09-11
---

# Dinamica 6-DOF

## Estado da planta

Sobre o ponto de referencia **fixo** `O`, nunca sobre o centro de massa.
Ver [[ADR-001 - Ponto de referencia e forma da dinamica]].

```python
@dataclass
class PlantState:          # continuo, 14 + N
    position_O_I_m: NDArray      # 3
    velocity_O_I_m_s: NDArray    # 3
    quaternion_BI: NDArray       # 4, com norma unitaria como restricao
    omega_B_rad_s: NDArray       # 3
    thrust_actual_N: NDArray     # N
    fuel_mass_kg: float          # 1
```

Estados auxiliares vivem em classes separadas **por natureza temporal**, mas evoluem no mesmo
relogio. Ver [[Regras de tempo e eventos]].

```python
ContinuousControllerState   # filtros, integradores, estimador
DiscreteControllerState     # amostras, comando retido, buffers de atraso
ContinuousHumanState        # neuromuscular, posicao e velocidade articular
```

## Forcas e momentos

```
F_b = soma_i T_i * n_i(delta_i)  +  C_bn(q) * [0, 0, m*g]  +  F_aero

F_aero = -0,5 * rho * |v_rel| * diag(CdA_x, CdA_y, CdA_z) * v_rel
```

Ordem de grandeza do arrasto: com `CdA_z` de cerca de 0,85 m2, a 13,9 m/s (50 km/h) o arrasto e
**104 N**, cerca de 9 por cento do peso. Nao e desprezivel, e precisa ser tensor por eixo porque o
corpo humano tem area frontal muito diferente da lateral.

```
M_O = soma_i (r_i - r_O) x (T_i * n_i)  +  M_aero  +  M_giroscopico
```

## Momento giroscopico e vetorial

```
M_giro = omega_corpo x soma_i ( I_rotor_i * Omega_i * s_i )
```

Depende da inercia polar de cada rotor, da rotacao real, da orientacao e **do sentido de giro**.
Pares contra-rotativos cancelam boa parte do momento angular total, entao o sentido e decisao
explicita de arquitetura:

```yaml
rotors:
  spin_direction:
    left_arm_fwd: cw
    left_arm_aft: ccw
    right_arm_fwd: ccw
    right_arm_aft: cw
    back: cw
```

Sem cancelamento, cinco turbinas alinhadas a 100 mil rotacoes por minuto produzem cerca de
**14 N m** a uma taxa de corpo de 1 rad/s, contra cerca de **196 N m** de autoridade diferencial.
Isso e 7 por cento, e e uma **condicao especifica**, nao constante do sistema.

## Massa variavel: aproximacao declarada

Uma microturbina e sistema aberto. Se o empuxo vem do deck como forca liquida ja aplicada a
estrutura, a formulacao com massa decrescendo lentamente e adequada, mas e **aproximacao**, nao
derivacao completa, e nao se confunde com o modelo de um foguete.

```yaml
variable_mass_model:
  method: quasi_steady_external_thrust
  description: >
    O empuxo do deck e forca externa liquida ja resultante do fluxo de momento do
    motor. A massa de combustivel altera propriedades de massa lentamente. Termos
    explicitos de fluxo de momento associados a ejecao nao sao integrados a parte.
```

## Ligacoes

[[Propriedades de massa]] · [[Cinematica de braco]] · [[Regras de tempo e eventos]] ·
[[Tres classes de teste]]
