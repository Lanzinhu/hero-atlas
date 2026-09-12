"""Algebra de quaternion, com a convencao declarada e testada.

⚠ **Convencao, fixada aqui e em lugar nenhum mais.** Confusao de convencao produz
trajetoria suave e completamente falsa, e nao quebra nenhum teste ingenuo. Por isso
ela e verificada pelo teste de equivariancia sob rotacao do referencial.

    formato:    q = [w, x, y, z], escalar primeiro
    sentido:    q leva vetor do CORPO para o INERCIAL
                v_I = R(q) @ v_B
    produto:    Hamilton
    cinematica: qdot = 0.5 * q (x) (0, omega_B)

O nome ``ib`` le-se "inercial vindo do corpo".
"""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = [
    "IDENTITY",
    "conjugate",
    "hamilton",
    "kinematic_derivative",
    "normalize",
    "rotate_body_to_inertial",
    "rotate_inertial_to_body",
    "rotation_matrix_ib",
    "rotation_matrix_from_unit",
    "from_axis_angle",
    "quaternion_error",
]

IDENTITY: NDArray[np.float64] = np.array([1.0, 0.0, 0.0, 0.0])
"""Atitude sem rotacao."""

_NORM_TOL = 1e-12


def _as_quaternion(value: ArrayLike, name: str = "q") -> NDArray[np.float64]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (4,):
        raise ValueError(f"{name} deve ter forma (4,) como [w, x, y, z], recebeu {arr.shape}")
    return arr


def _as_vector3(value: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} deve ter forma (3,), recebeu {arr.shape}")
    return arr


def normalize(q: ArrayLike) -> NDArray[np.float64]:
    """Devolve o quaternion unitario.

    A norma deriva por acumulo numerico ao longo da integracao, e um quaternion nao
    unitario deixa de representar rotacao: a matriz resultante passa a escalar
    vetores. Normalizar a cada passo e obrigatorio, nao cosmetico.
    """
    arr = _as_quaternion(q)
    norma = float(np.linalg.norm(arr))
    if norma < _NORM_TOL:
        raise ValueError("quaternion de norma nula nao representa rotacao")
    return arr / norma


def conjugate(q: ArrayLike) -> NDArray[np.float64]:
    """Conjugado. Para quaternion unitario, e a rotacao inversa."""
    arr = _as_quaternion(q)
    return np.array([arr[0], -arr[1], -arr[2], -arr[3]])


def hamilton(p: ArrayLike, q: ArrayLike) -> NDArray[np.float64]:
    """Produto de Hamilton ``p (x) q``.

    Nao comutativo. A ordem e a fonte classica de erro de sinal que nenhum teste de
    norma detecta.
    """
    pw, px, py, pz = _as_quaternion(p, "p")
    qw, qx, qy, qz = _as_quaternion(q, "q")
    return np.array(
        [
            pw * qw - px * qx - py * qy - pz * qz,
            pw * qx + px * qw + py * qz - pz * qy,
            pw * qy - px * qz + py * qw + pz * qx,
            pw * qz + px * qy - py * qx + pz * qw,
        ]
    )


def rotation_matrix_from_unit(q: NDArray[np.float64]) -> NDArray[np.float64]:
    """Matriz de rotacao **assumindo** quaternion ja unitario.

    Caminho quente da integracao: evita normalizar duas vezes por passo. A API
    publica :func:`rotation_matrix_ib` normaliza e deve ser preferida em qualquer
    outro lugar.
    """
    w, x, y, z = q
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def rotation_matrix_ib(q: ArrayLike) -> NDArray[np.float64]:
    """Matriz que leva vetor do corpo para o inercial: ``v_I = R @ v_B``.

    A transposta faz o caminho inverso, porque a matriz e ortogonal.
    """
    w, x, y, z = normalize(q)
    return np.array(
        [
            [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
            [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
            [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
        ]
    )


def rotate_body_to_inertial(q: ArrayLike, v_body: ArrayLike) -> NDArray[np.float64]:
    return rotation_matrix_ib(q) @ _as_vector3(v_body, "v_body")


def rotate_inertial_to_body(q: ArrayLike, v_inertial: ArrayLike) -> NDArray[np.float64]:
    return rotation_matrix_ib(q).T @ _as_vector3(v_inertial, "v_inertial")


def kinematic_derivative(q: ArrayLike, omega_body: ArrayLike) -> NDArray[np.float64]:
    """Derivada do quaternion de atitude.

        qdot = 0.5 * q (x) (0, omega_B)

    ⚠ A velocidade angular esta no referencial do **corpo**, e a multiplicacao e
    pela **direita**. Trocar o lado equivale a interpretar ``omega`` no inercial, o
    que produz trajetoria plausivel e errada.
    """
    arr = _as_quaternion(q)
    w = _as_vector3(omega_body, "omega_body")
    qw, qx, qy, qz = arr
    wx, wy, wz = w
    return 0.5 * np.array(
        [
            -qx * wx - qy * wy - qz * wz,
            qw * wx + qy * wz - qz * wy,
            qw * wy - qx * wz + qz * wx,
            qw * wz + qx * wy - qy * wx,
        ]
    )


def from_axis_angle(axis: ArrayLike, angle_rad: float) -> NDArray[np.float64]:
    """Quaternion de uma rotacao de ``angle_rad`` em torno de ``axis``."""
    eixo = _as_vector3(axis, "axis")
    norma = float(np.linalg.norm(eixo))
    if norma < _NORM_TOL:
        raise ValueError("eixo de rotacao nulo")
    eixo = eixo / norma
    meia = 0.5 * angle_rad
    return np.concatenate([[np.cos(meia)], np.sin(meia) * eixo])


def quaternion_error(q_command: ArrayLike, q_current: ArrayLike) -> NDArray[np.float64]:
    """Erro de atitude ``q_cmd* (x) q``, util para controle.

    A parte vetorial e proporcional ao erro angular para erros pequenos.
    """
    return hamilton(conjugate(normalize(q_command)), normalize(q_current))
