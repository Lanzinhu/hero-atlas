"""Dinamica de corpo rigido, rota reduzida do ADR-001.

Ver vault/02 - Decisoes/ADR-001 - Ponto de referencia e forma da dinamica.md

**Rota reduzida, marcos 3 a 5.** A pose altera propriedades de massa de forma quase
estatica, mas os termos de acoplamento por migracao interna **nao entram**:

```yaml
dynamics_model:
  formulation: reduced_quasi_static_pose
  internal_mass_migration_coupling: false
  valid_for: [geometry, torque_authority, actuator_delay, saturation, controller_stability]
  invalid_for: [arm_motion_induced_torque, fast_pose_transient]
```

Com a pose congelada, o deslocamento do centro em relacao ao ponto de referencia e
**constante no corpo**, e entao a formulacao abaixo e exata, nao aproximada:

    Euler sobre o CENTRO:   I_C omegadot + omega x (I_C omega) = M_C
    Newton:                 a_C,I = R_IB F_B / m
    Transporte para O:      a_O,I = a_C,I - R_IB ( omegadot x d + omega x (omega x d) )

O estado integra o **ponto de referencia** `O`, conforme ADR-001, e o centro e
derivado. A gravidade nao produz momento sobre o centro, por definicao de centro de
massa; ela reaparece no momento assim que a referencia muda para `O`.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..units import G0
from .quaternion import (
    kinematic_derivative,
    normalize,
    rotation_matrix_from_unit,
    rotation_matrix_ib,
)

__all__ = [
    "RigidBodyProperties",
    "BodyWrench",
    "PlantState",
    "state_derivative",
    "kinetic_energy_J",
    "angular_momentum_inertial",
]


def _cross3(a: NDArray[np.float64], b: NDArray[np.float64]) -> NDArray[np.float64]:
    """Produto vetorial de tres componentes, explicito.

    ``numpy.cross`` gasta a maior parte do tempo em despacho generico de eixo, que
    para vetores de tamanho fixo e puro custo. Medido em perfil: 70 por cento do
    tempo de integracao.
    """
    return np.array(
        [
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        ]
    )


def _vec3(value: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} deve ter forma (3,), recebeu {arr.shape}")
    return arr


@dataclass(frozen=True, slots=True)
class RigidBodyProperties:
    """Propriedades de massa congeladas para a rota reduzida.

    Attributes:
        mass_kg: massa total.
        inertia_about_cg_kg_m2: tensor sobre o **centro de massa**, nos eixos do corpo.
        cg_offset_from_reference_m: ``d = r_C - r_O``, constante enquanto a pose e a
            massa estiverem congeladas. E a hipotese que torna esta formulacao exata.
    """

    mass_kg: float
    inertia_about_cg_kg_m2: NDArray[np.float64]
    cg_offset_from_reference_m: NDArray[np.float64]
    _inertia_inverse: NDArray[np.float64] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not np.isfinite(self.mass_kg) or self.mass_kg <= 0.0:
            raise ValueError(f"massa deve ser positiva, recebeu {self.mass_kg!r}")
        tensor = np.asarray(self.inertia_about_cg_kg_m2, dtype=np.float64)
        if tensor.shape != (3, 3):
            raise ValueError("tensor de inercia deve ter forma (3, 3)")
        if not np.allclose(tensor, tensor.T, atol=1e-9):
            raise ValueError("tensor de inercia nao e simetrico")
        if np.any(np.linalg.eigvalsh(tensor) <= 0.0):
            raise ValueError("tensor de inercia precisa ser positivo definido")
        object.__setattr__(self, "inertia_about_cg_kg_m2", tensor)
        object.__setattr__(
            self,
            "cg_offset_from_reference_m",
            _vec3(self.cg_offset_from_reference_m, "cg_offset_from_reference_m"),
        )
        object.__setattr__(self, "_inertia_inverse", np.linalg.inv(tensor))

    @property
    def inertia_inverse(self) -> NDArray[np.float64]:
        """Inverso do tensor, calculado **uma vez** na construcao.

        Era propriedade que invertia a matriz a cada avaliacao da derivada, ou seja
        quatro inversoes por passo de Runge-Kutta.
        """
        return self._inertia_inverse


@dataclass(frozen=True, slots=True)
class BodyWrench:
    """Forca e momento aplicados, no referencial do corpo.

    ⚠ ``moment_about_cg_Nm`` e sobre o **centro de massa**, nao sobre o ponto de
    referencia. Quem monta o wrench a partir da geometria precisa transportar, e a
    gravidade nao entra aqui: ela e somada dentro de :func:`state_derivative`,
    porque depende da atitude.
    """

    force_N: NDArray[np.float64]
    moment_about_cg_Nm: NDArray[np.float64]

    def __post_init__(self) -> None:
        object.__setattr__(self, "force_N", _vec3(self.force_N, "force_N"))
        object.__setattr__(
            self, "moment_about_cg_Nm", _vec3(self.moment_about_cg_Nm, "moment_about_cg_Nm")
        )

    @classmethod
    def zero(cls) -> BodyWrench:
        return cls(force_N=np.zeros(3), moment_about_cg_Nm=np.zeros(3))


@dataclass(frozen=True, slots=True)
class PlantState:
    """Estado continuo da planta, 13 componentes.

    Integra o **ponto de referencia** ``O``, conforme ADR-001. O centro de massa e
    derivado, nunca integrado.

    Attributes:
        position_O_I_m: posicao do ponto de referencia, no inercial.
        velocity_O_I_m_s: velocidade do ponto de referencia, no inercial.
        quaternion_ib: atitude. Leva vetor do corpo para o inercial.
        omega_B_rad_s: velocidade angular, no corpo.
    """

    position_O_I_m: NDArray[np.float64]
    velocity_O_I_m_s: NDArray[np.float64]
    quaternion_ib: NDArray[np.float64]
    omega_B_rad_s: NDArray[np.float64]

    SIZE = 13

    def to_vector(self) -> NDArray[np.float64]:
        return np.concatenate(
            [
                self.position_O_I_m,
                self.velocity_O_I_m_s,
                self.quaternion_ib,
                self.omega_B_rad_s,
            ]
        )

    @classmethod
    def from_vector(cls, x: ArrayLike) -> PlantState:
        arr = np.asarray(x, dtype=np.float64)
        if arr.shape != (cls.SIZE,):
            raise ValueError(f"estado deve ter {cls.SIZE} componentes, recebeu {arr.shape}")
        return cls(
            position_O_I_m=arr[0:3],
            velocity_O_I_m_s=arr[3:6],
            quaternion_ib=arr[6:10],
            omega_B_rad_s=arr[10:13],
        )

    @classmethod
    def at_rest(cls, position_O_I_m: ArrayLike = (0.0, 0.0, 0.0)) -> PlantState:
        return cls(
            position_O_I_m=_vec3(position_O_I_m, "position_O_I_m"),
            velocity_O_I_m_s=np.zeros(3),
            quaternion_ib=np.array([1.0, 0.0, 0.0, 0.0]),
            omega_B_rad_s=np.zeros(3),
        )

    def with_normalized_attitude(self) -> PlantState:
        return PlantState(
            position_O_I_m=self.position_O_I_m,
            velocity_O_I_m_s=self.velocity_O_I_m_s,
            quaternion_ib=normalize(self.quaternion_ib),
            omega_B_rad_s=self.omega_B_rad_s,
        )

    def center_of_mass_position_I_m(self, body: RigidBodyProperties) -> NDArray[np.float64]:
        """Posicao do centro, derivada: ``p_C = p_O + R_IB d``."""
        return self.position_O_I_m + rotation_matrix_ib(self.quaternion_ib) @ (
            body.cg_offset_from_reference_m
        )

    def center_of_mass_velocity_I_m_s(self, body: RigidBodyProperties) -> NDArray[np.float64]:
        """Velocidade do centro: ``v_C = v_O + R_IB (omega x d)``."""
        return self.velocity_O_I_m_s + rotation_matrix_ib(self.quaternion_ib) @ _cross3(
            self.omega_B_rad_s, body.cg_offset_from_reference_m
        )


def state_derivative(
    state: PlantState,
    body: RigidBodyProperties,
    wrench: BodyWrench,
    *,
    gravity_I_m_s2: ArrayLike = (0.0, 0.0, G0),
) -> NDArray[np.float64]:
    """Derivada do estado, rota reduzida.

    A gravidade entra aqui e nao no wrench porque depende da atitude, e porque sobre
    o centro de massa ela **nao produz momento**. Ela volta a produzir momento no
    instante em que a referencia muda para ``O``, e e por isso que o trim precisa do
    termo e a dinamica sobre o centro nao.

    Args:
        wrench: forca no corpo e momento **sobre o centro de massa**, sem gravidade.
        gravity_I_m_s2: aceleracao da gravidade no inercial. Padrao com z para baixo.
    """
    q = normalize(state.quaternion_ib)
    R_ib = rotation_matrix_from_unit(q)  # ja unitario, nao normaliza de novo
    omega = state.omega_B_rad_s
    d = body.cg_offset_from_reference_m

    # rotacional, sobre o centro de massa: Euler puro
    inercia = body.inertia_about_cg_kg_m2
    omega_dot = body.inertia_inverse @ (wrench.moment_about_cg_Nm - _cross3(omega, inercia @ omega))

    # translacional do centro, no inercial
    gravidade = _vec3(gravity_I_m_s2, "gravity_I_m_s2")
    a_cg_I = R_ib @ (wrench.force_N / body.mass_kg) + gravidade

    # transporte do centro para o ponto de referencia
    a_O_I = a_cg_I - R_ib @ (_cross3(omega_dot, d) + _cross3(omega, _cross3(omega, d)))

    return np.concatenate(
        [state.velocity_O_I_m_s, a_O_I, kinematic_derivative(q, omega), omega_dot]
    )


def angular_momentum_inertial(state: PlantState, body: RigidBodyProperties) -> NDArray[np.float64]:
    """Momento angular sobre o centro, expresso no **inercial**.

    ⚠ A avaliacao tem que ser no inercial. Verificar as componentes no corpo seria
    incorreto, porque o proprio referencial gira: elas mudam mesmo com o momento
    angular conservado.
    """
    R_ib = rotation_matrix_ib(state.quaternion_ib)
    return R_ib @ (body.inertia_about_cg_kg_m2 @ state.omega_B_rad_s)


def kinetic_energy_J(state: PlantState, body: RigidBodyProperties) -> float:
    """Energia cinetica total: translacao do centro mais rotacao."""
    v_cg = state.center_of_mass_velocity_I_m_s(body)
    translacao = 0.5 * body.mass_kg * float(v_cg @ v_cg)
    omega = state.omega_B_rad_s
    rotacao = 0.5 * float(omega @ (body.inertia_about_cg_kg_m2 @ omega))
    return translacao + rotacao
