---
tags: [adr, dinamica, nucleo]
adr: 001
estado: aceita
data: 2026-09-11
---

# ADR-001 - Ponto de referencia e forma da dinamica, em duas etapas

## Contexto

Uma revisao anterior declarou dinamica sobre ponto de referencia fixo no corpo e manteve a equacao
angular valida sobre o centro de massa. **Inconsistente.**

Sobre um ponto `O` que nao e o centro de massa, forca e rotacao ficam acopladas:

```
a_C = a_O + omega_dot x r_C/O + omega x (omega x r_C/O) + 2 omega x rdot_C/O + rddot_C/O
F_ext = m * a_C
```

A forca externa participa da solucao angular atraves da migracao de massa. Recalcular `I_O` e
aplicar uma equacao de Euler enriquecida **nao fecha**.

E o centro de massa migra o tempo todo: com a pose dos bracos e com o combustivel queimado.
Ver [[Propriedades de massa]].

## Decisao

Encenada em duas etapas, para nao bloquear o progresso nem esconder a aproximacao.

### Marcos 3 a 5: rota reduzida, explicitamente declarada

```yaml
dynamics_model:
  formulation: reduced_quasi_static_pose
  internal_mass_migration_coupling: false
  valid_for: [geometry, torque_authority, actuator_delay, saturation, controller_stability]
  invalid_for: [arm_motion_induced_torque, fast_pose_transient]
```

A pose altera geometria dos bocais, centro de massa e tensor de inercia de forma quase estatica,
mas os termos de acoplamento por migracao interna nao entram.

**Permite** estudar geometria, autoridade de torque, atraso de turbina, saturacao e estabilidade do
controlador.
**Nao permite** concluir sobre torque induzido por movimento rapido de braco.

### Marco 6 em diante: rota espacial completa sobre `O`, obrigatoria

O [[Marco 6 - Piloto e regiao R]] e exatamente onde o torque induzido pelo braco vira o objeto de
estudo, e nesta arquitetura **o braco e o atuador**. Aproximar ali seria aproximar a variavel sob
investigacao.

```
V_O     = [omega_B ; v_O,B]
W_O,ext = [tau_O,B ; F_ext,B]
W_O,ext = M_O(q, m_f) * Vdot_O + b_O(q, qdot, qddot, m_f, mdot_f, V_O)
Vdot_O  = inv(M_O) * (W_O,ext - b_O)
```

`b_O` reune Coriolis, centrifuga, variacao de inercia, migracao do centro, momento relativo dos
bracos e variacao lenta de combustivel quando habilitada.

## Consequencia: um ponto so, em todo lugar

Nao pode haver dinamica sobre o chassi, torque de propulsor sobre o centro, posicao monitorada no
centro e matriz de alocacao montada sobre um quarto ponto. **Isso daria tres centros diferentes ao
simulador, e a fisica nao perdoa esse tipo de criatividade.**

```python
@dataclass
class PlantState:
    position_O_I_m: NDArray      # ponto estrutural fixo, NAO o centro de massa
    velocity_O_I_m_s: NDArray
    quaternion_BI: NDArray
    omega_B_rad_s: NDArray
    thrust_actual_N: NDArray
    fuel_mass_kg: float
```

O centro e **derivado, nunca integrado**:

```
p_C,I = p_O,I + R_IB * r_C/O,B
v_C,I = v_O,I + R_IB * (omega_B x r_C/O,B + rdot_C/O,B)
```

E o wrench da alocacao e montado sobre o mesmo `O`: `tau_O,B = soma_i r_i/O,B x F_i,B`.

## Ligacoes

[[Dinamica 6-DOF]] · [[Propriedades de massa]] · [[R-01 - Conservacao com bracos moveis]] ·
[[ADR-002 - Trim inclui momento do peso]]
