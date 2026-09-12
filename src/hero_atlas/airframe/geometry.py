"""Geometria de propulsao: onde cada bocal esta e para onde aponta.

Ver vault/06 - Marcos/Marco 2 - Trim e autoridade.md

Aqui acaba a suposicao do marco 1 de que **toda capacidade instalada contribui para
a direcao util**. Cada bocal tem posicao, direcao e limites proprios, e a soma
vetorial deles pode ser muito menor que a soma escalar dos empuxos.

Convencao de referencial: corpo com x para frente, y para a direita, z para baixo.
A gravidade inercial aponta para z positivo.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = [
    "ArmPairSpec",
    "AxialNozzleSpec",
    "NozzleSpec",
    "parametric_layout",
    "PropulsionGeometry",
    "allocation_matrix",
    "gravity_like_layout",
]


def _unit_vector(value: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} deve ter forma (3,), recebeu {arr.shape}")
    norma = float(np.linalg.norm(arr))
    if norma < 1e-12:
        raise ValueError(f"{name} tem norma nula e nao define direcao")
    return arr / norma


@dataclass(frozen=True, slots=True)
class NozzleSpec:
    """Um propulsor, com geometria e limites proprios.

    Attributes:
        name: identificador legivel, usado no diagnostico de restricao ativa.
        position_body_m: onde o empuxo e aplicado, no referencial do corpo.
        direction_body: para onde a **forca** aponta, normalizado na construcao.
            Um bocal que expele gas para baixo empurra para cima, entao a direcao
            de um propulsor de sustentacao e ``[0, 0, -1]``.
        thrust_min_N: marcha lenta. **Nao e zero** numa turbina, e a restricao
            dura que mais corta o conjunto de wrenches atingiveis.
        thrust_max_N: limite superior.
        available: falso quando o propulsor esta indisponivel, para estudo de falha.
    """

    name: str
    position_body_m: NDArray[np.float64]
    direction_body: NDArray[np.float64]
    thrust_min_N: float
    thrust_max_N: float
    available: bool = True

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("nome do bocal nao pode ser vazio")
        object.__setattr__(
            self, "position_body_m", np.asarray(self.position_body_m, dtype=np.float64)
        )
        if self.position_body_m.shape != (3,):
            raise ValueError(f"{self.name}: posicao deve ter forma (3,)")
        object.__setattr__(
            self, "direction_body", _unit_vector(self.direction_body, f"{self.name}.direction")
        )
        if not 0.0 <= self.thrust_min_N <= self.thrust_max_N:
            raise ValueError(
                f"{self.name}: limites invalidos, min={self.thrust_min_N} max={self.thrust_max_N}"
            )

    def wrench_column(self, reference_point_body_m: NDArray[np.float64]) -> NDArray[np.float64]:
        """Coluna deste bocal na matriz de alocacao, sobre o ponto de referencia.

            [ n_i ; (r_i - r_O) x n_i ]

        Seis componentes: forca e depois momento, ambos no referencial do corpo.
        """
        braco = self.position_body_m - reference_point_body_m
        return np.concatenate([self.direction_body, np.cross(braco, self.direction_body)])


@dataclass(frozen=True, slots=True)
class PropulsionGeometry:
    """O conjunto de propulsores, sobre um ponto de referencia declarado.

    O ponto de referencia e **fixo no corpo**, nunca o centro de massa, que migra
    com a pose e com o combustivel. Ver ADR-001.
    """

    nozzles: tuple[NozzleSpec, ...]
    reference_point_body_m: NDArray[np.float64]

    def __post_init__(self) -> None:
        if not self.nozzles:
            raise ValueError("geometria sem nenhum bocal")
        nomes = [n.name for n in self.nozzles]
        duplicados = {n for n in nomes if nomes.count(n) > 1}
        if duplicados:
            raise ValueError(f"nomes de bocal duplicados: {sorted(duplicados)}")
        object.__setattr__(
            self,
            "reference_point_body_m",
            np.asarray(self.reference_point_body_m, dtype=np.float64),
        )

    @property
    def count(self) -> int:
        return len(self.nozzles)

    @property
    def available(self) -> tuple[NozzleSpec, ...]:
        return tuple(n for n in self.nozzles if n.available)

    @property
    def total_thrust_max_N(self) -> float:
        """Soma **escalar** dos maximos.

        ⚠ Este e o numero do marco 1, e ele superestima: a soma vetorial na direcao
        util e menor sempre que os bocais nao sao colineares.
        """
        return sum(n.thrust_max_N for n in self.available)

    def fail(self, *names: str) -> PropulsionGeometry:
        """Nova geometria com os bocais nomeados indisponiveis."""
        alvo = set(names)
        desconhecidos = alvo - {n.name for n in self.nozzles}
        if desconhecidos:
            raise ValueError(f"bocais inexistentes: {sorted(desconhecidos)}")
        return PropulsionGeometry(
            nozzles=tuple(
                NozzleSpec(
                    name=n.name,
                    position_body_m=n.position_body_m,
                    direction_body=n.direction_body,
                    thrust_min_N=n.thrust_min_N,
                    thrust_max_N=n.thrust_max_N,
                    available=n.available and n.name not in alvo,
                )
                for n in self.nozzles
            ),
            reference_point_body_m=self.reference_point_body_m,
        )


def allocation_matrix(geometry: PropulsionGeometry) -> NDArray[np.float64]:
    """Matriz de alocacao ``W``, de forma (6, N) sobre os bocais **disponiveis**.

        W = [ n_1 ... n_N ; (r_1-r_O) x n_1 ... (r_N-r_O) x n_N ]

    As tres primeiras linhas dao forca, as tres ultimas dao momento sobre o ponto de
    referencia. Posto, condicionamento e conjunto atingivel saem daqui.
    """
    disponiveis = geometry.available
    if not disponiveis:
        raise ValueError("nenhum bocal disponivel")
    return np.column_stack([n.wrench_column(geometry.reference_point_body_m) for n in disponiveis])


def gravity_like_layout(
    *,
    thrust_max_N: float,
    idle_fraction: float = 0.10,
    arm_tilt_rad: float = math.radians(25.0),
    arm_half_span_m: float = 0.35,
    arm_forward_m: float = 0.30,
    arm_height_m: float = -0.20,
    back_height_m: float = 0.10,
    reference_point_body_m: ArrayLike | None = None,
) -> PropulsionGeometry:
    """Arquitetura de cinco propulsores, dois por braco mais um dorsal.

    E a configuracao do traje da Gravity Industries em ordem de grandeza: quatro
    motores de braco inclinados para fora, que e o que gera autoridade de controle e
    o que cobra o cosseno, mais um dorsal alinhado com a vertical.

    ⚠ Geometria **plausivel, nao medida**. Envergadura, avanco e altura sao
    estimativas antropometricas, nao dados do traje real.

    Args:
        thrust_max_N: empuxo maximo de **cada** propulsor.
        idle_fraction: marcha lenta como fracao do maximo. Turbina nao desliga.
        arm_tilt_rad: inclinacao dos bocais de braco em relacao a vertical.
        arm_half_span_m: meia envergadura entre os bracos.
        arm_forward_m: quanto os bracos ficam a frente do ponto de referencia.
        arm_height_m: altura dos bocais de braco, negativo e acima.
        back_height_m: altura do bocal dorsal.
    """
    if thrust_max_N <= 0.0:
        raise ValueError("empuxo maximo precisa ser positivo")
    if not 0.0 <= idle_fraction < 1.0:
        raise ValueError("fracao de marcha lenta em [0, 1)")

    idle = idle_fraction * thrust_max_N
    seno, cosseno = math.sin(arm_tilt_rad), math.cos(arm_tilt_rad)

    bocais: list[NozzleSpec] = []
    for lado, sinal in (("esq", -1.0), ("dir", +1.0)):
        for pos, avanco in (("frente", arm_forward_m), ("tras", arm_forward_m - 0.15)):
            bocais.append(
                NozzleSpec(
                    name=f"braco_{lado}_{pos}",
                    position_body_m=np.array([avanco, sinal * arm_half_span_m, arm_height_m]),
                    # empurra para cima (z negativo) e para fora (y no sinal do lado)
                    direction_body=np.array([0.0, sinal * seno, -cosseno]),
                    thrust_min_N=idle,
                    thrust_max_N=thrust_max_N,
                )
            )

    bocais.append(
        NozzleSpec(
            name="dorsal",
            position_body_m=np.array([-0.15, 0.0, back_height_m]),
            direction_body=np.array([0.0, 0.0, -1.0]),
            thrust_min_N=idle,
            thrust_max_N=thrust_max_N,
        )
    )

    referencia = (
        np.zeros(3)
        if reference_point_body_m is None
        else np.asarray(reference_point_body_m, dtype=np.float64)
    )
    return PropulsionGeometry(nozzles=tuple(bocais), reference_point_body_m=referencia)


@dataclass(frozen=True, slots=True)
class ArmPairSpec:
    """Um par simetrico de propulsores de braco, esquerdo e direito.

    Cada par tem geometria propria. **Variar parametros entre pares e o que quebra
    o acoplamento entre forca lateral e rolagem**, porque a dependencia vem de todos
    compartilharem o mesmo valor da razao

        Mx/Fy = -( span*cos(tilt) + height*sin(tilt) ) / sin(tilt)

    Attributes:
        forward_m: avanco em relacao ao ponto de referencia.
        span_m: meia envergadura, distancia lateral ao plano de simetria.
        height_m: altura. Negativo e acima do ponto de referencia.
        lateral_tilt_rad: inclinacao para fora, em relacao a vertical.
        longitudinal_tilt_rad: inclinacao para frente. Positivo empurra para tras.
            **Zero aqui significa nenhuma forca longitudinal disponivel.**
    """

    forward_m: float
    span_m: float
    height_m: float
    lateral_tilt_rad: float
    longitudinal_tilt_rad: float = 0.0


@dataclass(frozen=True, slots=True)
class AxialNozzleSpec:
    """Propulsor no plano de simetria, tipicamente dorsal."""

    name: str
    forward_m: float
    height_m: float
    longitudinal_tilt_rad: float = 0.0


def parametric_layout(
    *,
    pairs: Sequence[ArmPairSpec],
    axial: Sequence[AxialNozzleSpec] = (),
    thrust_max_N: float,
    idle_fraction: float = 0.10,
    reference_point_body_m: ArrayLike | None = None,
) -> PropulsionGeometry:
    """Constroi uma geometria a partir de pares simetricos e bocais axiais.

    Generaliza :func:`gravity_like_layout` para varredura de arquitetura: cada par
    carrega avanco, envergadura, altura e as duas inclinacoes proprias.

    ⚠ Geometria **plausivel, nao medida**, em qualquer combinacao de parametros.
    """
    if not pairs and not axial:
        raise ValueError("layout sem nenhum propulsor")
    if thrust_max_N <= 0.0:
        raise ValueError("empuxo maximo precisa ser positivo")
    if not 0.0 <= idle_fraction < 1.0:
        raise ValueError("fracao de marcha lenta em [0, 1)")

    idle = idle_fraction * thrust_max_N
    bocais: list[NozzleSpec] = []

    for indice, par in enumerate(pairs):
        sl, cl = math.sin(par.lateral_tilt_rad), math.cos(par.lateral_tilt_rad)
        sx = math.sin(par.longitudinal_tilt_rad)
        for lado, sinal in (("esq", -1.0), ("dir", +1.0)):
            bocais.append(
                NozzleSpec(
                    name=f"par{indice}_{lado}",
                    position_body_m=np.array([par.forward_m, sinal * par.span_m, par.height_m]),
                    direction_body=np.array([sx, sinal * sl, -cl]),
                    thrust_min_N=idle,
                    thrust_max_N=thrust_max_N,
                )
            )

    for bocal in axial:
        sx = math.sin(bocal.longitudinal_tilt_rad)
        bocais.append(
            NozzleSpec(
                name=bocal.name,
                position_body_m=np.array([bocal.forward_m, 0.0, bocal.height_m]),
                direction_body=np.array([sx, 0.0, -math.cos(bocal.longitudinal_tilt_rad)]),
                thrust_min_N=idle,
                thrust_max_N=thrust_max_N,
            )
        )

    referencia = (
        np.zeros(3)
        if reference_point_body_m is None
        else np.asarray(reference_point_body_m, dtype=np.float64)
    )
    return PropulsionGeometry(nozzles=tuple(bocais), reference_point_body_m=referencia)
