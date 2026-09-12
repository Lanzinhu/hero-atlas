"""Integradores de passo unico, com normalizacao de atitude a cada passo.

Runge-Kutta de quarta ordem em caso suave. ⚠ **Quarta ordem do integrador nao
implica quarta ordem do sistema hibrido**: saturacao, retencao, evento e troca de
modo tornam a solucao nao diferenciavel nesses pontos, e a ordem observada cai
mesmo com o integrador correto. Ver vault/05 - Verificacao/Tres classes de teste.md
"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from .quaternion import normalize
from .rigid_body import PlantState

__all__ = ["rk4_step", "euler_step", "integrate_fixed_step"]

Derivative = Callable[[float, NDArray[np.float64]], NDArray[np.float64]]


def _renormalize_attitude(x: NDArray[np.float64]) -> NDArray[np.float64]:
    """Reprojeta o quaternion na esfera unitaria.

    A norma deriva por acumulo numerico. Um quaternion nao unitario deixa de
    representar rotacao e passa a escalar vetores, o que aparece como ganho
    espurio de energia sem quebrar nenhum teste de forma.
    """
    saida = x.copy()
    saida[6:10] = normalize(x[6:10])
    return saida


def euler_step(f: Derivative, t: float, x: NDArray[np.float64], dt: float) -> NDArray[np.float64]:
    """Euler explicito. Existe para o teste de ordem ter com que comparar."""
    return _renormalize_attitude(x + dt * f(t, x))


def rk4_step(f: Derivative, t: float, x: NDArray[np.float64], dt: float) -> NDArray[np.float64]:
    """Runge-Kutta classico de quarta ordem."""
    k1 = f(t, x)
    k2 = f(t + 0.5 * dt, x + 0.5 * dt * k1)
    k3 = f(t + 0.5 * dt, x + 0.5 * dt * k2)
    k4 = f(t + dt, x + dt * k3)
    return _renormalize_attitude(x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4))


def integrate_fixed_step(
    f: Derivative,
    state: PlantState,
    *,
    t_final_s: float,
    dt_s: float,
    stepper: Callable[..., NDArray[np.float64]] = rk4_step,
) -> tuple[NDArray[np.float64], list[PlantState]]:
    """Integra a passo fixo, sem eventos.

    ⚠ Sem agenda de eventos: serve para os casos analiticos suaves. A integracao com
    fronteira discreta usa ``sim.events.EventSchedule`` e nunca atravessa um evento.

    Returns:
        instantes e estados, incluindo o inicial.
    """
    if dt_s <= 0.0 or t_final_s <= 0.0:
        raise ValueError("passo e horizonte precisam ser positivos")

    passos = int(round(t_final_s / dt_s))
    tempos = np.linspace(0.0, passos * dt_s, passos + 1)

    x = state.with_normalized_attitude().to_vector()
    trajetoria = [PlantState.from_vector(x)]

    for i in range(passos):
        x = stepper(f, float(tempos[i]), x, dt_s)
        trajetoria.append(PlantState.from_vector(x))

    return tempos, trajetoria
