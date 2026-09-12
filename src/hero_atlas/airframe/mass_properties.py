"""Agregacao de propriedades de massa.

Esta e a peca que motivou a correcao mais seria de todo o processo de revisao do
plano. Ver vault/04 - Fisica/Propriedades de massa.md

    Tensores de inercia NAO se somam diretamente. So podem ser somados quando estao
    expressos no mesmo referencial, orientados pelos mesmos eixos e calculados sobre
    o mesmo ponto de referencia. Em geral cada componente tem inercia sobre o proprio
    centro de massa e na propria orientacao.

A agregacao correta e:

    m_total    = soma_j m_j
    r_CG_total = (soma_j m_j * r_j) / m_total

    I_j_ref = R_j @ I_j_CG @ R_j.T  +  m_j * (|d_j|^2 * I3 - outer(d_j, d_j))
    I_total_ref = soma_j I_j_ref

com ``d_j = r_j_CG - r_ref``.

Convencao de rotacao: ``R_j`` orienta o componente no corpo, isto e
``v_body = R_j @ v_componente``.

Um erro aqui produz um simulador que voa lindamente no grafico, o que e bem mais
perigoso para um simulador do que um que cai.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

__all__ = [
    "MassComponent",
    "MassProperties",
    "rotate_inertia",
    "parallel_axis",
    "aggregate_mass_properties",
    "validate_inertia_tensor",
    "validate_rotation_matrix",
]

_SYMMETRY_ATOL = 1e-9
_ROTATION_ATOL = 1e-9
_EIGENVALUE_ATOL = 1e-12


def _as_vector3(value: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3,):
        raise ValueError(f"{name} deve ter forma (3,), recebeu {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contem valor nao finito")
    return arr


def _as_matrix3(value: ArrayLike, name: str) -> NDArray[np.float64]:
    arr = np.asarray(value, dtype=np.float64)
    if arr.shape != (3, 3):
        raise ValueError(f"{name} deve ter forma (3, 3), recebeu {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} contem valor nao finito")
    return arr


def validate_rotation_matrix(R: ArrayLike, *, name: str = "rotacao") -> NDArray[np.float64]:
    """Exige rotacao propria: ``R @ R.T == I`` e ``det(R) == +1``.

    Uma reflexao (determinante negativo) passaria despercebida na formula de
    rotacao de tensor e produziria inercia plausivel e errada.
    """
    arr = _as_matrix3(R, name)
    if not np.allclose(arr @ arr.T, np.eye(3), atol=_ROTATION_ATOL):
        raise ValueError(f"{name} nao e ortogonal: R @ R.T difere da identidade")
    det = float(np.linalg.det(arr))
    if not np.isclose(det, 1.0, atol=_ROTATION_ATOL):
        raise ValueError(
            f"{name} tem determinante {det:.6g}, esperado +1. "
            "Determinante -1 e reflexao, nao rotacao."
        )
    return arr


def validate_inertia_tensor(
    inertia: ArrayLike,
    *,
    name: str = "inercia",
    allow_degenerate: bool = True,
) -> NDArray[np.float64]:
    """Exige tensor fisicamente valido.

    Simetrico, positivo semidefinido, e obedecendo a desigualdade triangular dos
    momentos principais (``I1 + I2 >= I3``). Corpos degenerados como massa pontual
    ou barra ideal tem autovalor nulo e sao aceitos por padrao.
    """
    arr = _as_matrix3(inertia, name)

    if not np.allclose(arr, arr.T, atol=_SYMMETRY_ATOL):
        raise ValueError(f"{name} nao e simetrico")

    eigenvalues = np.linalg.eigvalsh(arr)
    if np.any(eigenvalues < -_EIGENVALUE_ATOL):
        raise ValueError(f"{name} nao e positivo semidefinido: autovalores {eigenvalues}")
    if not allow_degenerate and np.any(eigenvalues <= _EIGENVALUE_ATOL):
        raise ValueError(f"{name} e degenerado: autovalores {eigenvalues}")

    i1, i2, i3 = np.sort(eigenvalues)
    scale = max(float(i3), 1.0)
    if i1 + i2 < i3 - 1e-9 * scale:
        raise ValueError(
            f"{name} viola a desigualdade triangular dos momentos principais: "
            f"{i1:.6g} + {i2:.6g} < {i3:.6g}"
        )
    return arr


@dataclass(frozen=True, slots=True)
class MassComponent:
    """Um componente com massa, posicao, inercia propria e orientacao propria.

    Attributes:
        name: identificador legivel, usado em mensagens de erro e na massa contabil.
        mass_kg: massa do componente.
        center_of_mass_body_m: posicao do centro de massa do componente, no
            referencial do corpo.
        inertia_about_own_cg_kg_m2: tensor de inercia sobre o proprio centro de
            massa, expresso nos EIXOS DO PROPRIO COMPONENTE.
        orientation_body_from_component: rotacao ``R`` tal que
            ``v_body = R @ v_componente``. Identidade quando os eixos coincidem.
    """

    name: str
    mass_kg: float
    center_of_mass_body_m: NDArray[np.float64]
    inertia_about_own_cg_kg_m2: NDArray[np.float64]
    orientation_body_from_component: NDArray[np.float64]

    def __post_init__(self) -> None:
        if not np.isfinite(self.mass_kg) or self.mass_kg <= 0.0:
            raise ValueError(
                f"componente {self.name!r}: massa deve ser positiva e finita, "
                f"recebeu {self.mass_kg!r}"
            )
        object.__setattr__(
            self,
            "center_of_mass_body_m",
            _as_vector3(self.center_of_mass_body_m, f"{self.name}.center_of_mass_body_m"),
        )
        object.__setattr__(
            self,
            "inertia_about_own_cg_kg_m2",
            validate_inertia_tensor(
                self.inertia_about_own_cg_kg_m2, name=f"{self.name}.inertia_about_own_cg"
            ),
        )
        object.__setattr__(
            self,
            "orientation_body_from_component",
            validate_rotation_matrix(
                self.orientation_body_from_component, name=f"{self.name}.orientation"
            ),
        )

    @classmethod
    def point_mass(cls, name: str, mass_kg: float, position_body_m: ArrayLike) -> MassComponent:
        """Massa pontual: inercia propria nula, orientacao irrelevante."""
        return cls(
            name=name,
            mass_kg=mass_kg,
            center_of_mass_body_m=np.asarray(position_body_m, dtype=np.float64),
            inertia_about_own_cg_kg_m2=np.zeros((3, 3)),
            orientation_body_from_component=np.eye(3),
        )

    @property
    def inertia_about_own_cg_in_body_axes(self) -> NDArray[np.float64]:
        """Inercia propria reexpressa nos eixos do corpo, ainda sobre o proprio centro."""
        return rotate_inertia(self.inertia_about_own_cg_kg_m2, self.orientation_body_from_component)


@dataclass(frozen=True, slots=True)
class MassProperties:
    """Propriedades agregadas, sobre um ponto de referencia explicito.

    O ponto de referencia e parte do resultado, nao um detalhe. Ver
    vault/02 - Decisoes/ADR-001 - Ponto de referencia e forma da dinamica.md:
    a dinamica e escrita sobre um ponto FIXO no corpo, nao sobre o centro de massa,
    que migra com a pose e com o combustivel.
    """

    mass_kg: float
    center_of_mass_body_m: NDArray[np.float64]
    reference_point_body_m: NDArray[np.float64]
    inertia_about_reference_kg_m2: NDArray[np.float64]

    @property
    def offset_reference_to_cg_m(self) -> NDArray[np.float64]:
        """Vetor do ponto de referencia ate o centro de massa, ``r_C/O``."""
        return self.center_of_mass_body_m - self.reference_point_body_m

    @property
    def inertia_about_cg_kg_m2(self) -> NDArray[np.float64]:
        """Inercia sobre o centro de massa agregado.

        Obtida desfazendo o teorema dos eixos paralelos a partir da referencia.
        """
        d = self.offset_reference_to_cg_m
        return self.inertia_about_reference_kg_m2 - self.mass_kg * (
            float(d @ d) * np.eye(3) - np.outer(d, d)
        )

    def inertia_about(self, point_body_m: ArrayLike) -> NDArray[np.float64]:
        """Inercia sobre um ponto arbitrario do corpo.

        Passa obrigatoriamente pelo centro de massa, porque o teorema dos eixos
        paralelos so e valido a partir do centro. Transladar direto de um ponto
        nao central para outro e o erro classico.
        """
        point = _as_vector3(point_body_m, "point_body_m")
        d = self.center_of_mass_body_m - point
        return parallel_axis(self.inertia_about_cg_kg_m2, self.mass_kg, d)


def rotate_inertia(inertia: ArrayLike, rotation: ArrayLike) -> NDArray[np.float64]:
    """Reexpressa um tensor de inercia em outros eixos.

    ``I_alvo = R @ I_origem @ R.T``

    com ``R`` tal que ``v_alvo = R @ v_origem``.

    Exemplo: uma barra ao longo do eixo x proprio tem ``diag(0, I, I)``. Girada
    90 graus em torno de z, ela aponta para o eixo y do corpo e o tensor vira
    ``diag(I, 0, I)``.
    """
    tensor = _as_matrix3(inertia, "inertia")
    R = validate_rotation_matrix(rotation)
    return R @ tensor @ R.T


def parallel_axis(
    inertia_about_cg: ArrayLike, mass_kg: float, displacement_m: ArrayLike
) -> NDArray[np.float64]:
    """Teorema dos eixos paralelos, a partir do CENTRO DE MASSA.

    ``I_ponto = I_cg + m * (|d|^2 * I3 - outer(d, d))``

    Args:
        inertia_about_cg: tensor sobre o centro de massa do corpo, ja nos eixos
            de destino.
        mass_kg: massa do corpo.
        displacement_m: vetor entre o centro de massa e o ponto. O sinal nao
            importa, porque a expressao e quadratica em ``d``.

    O nome do primeiro argumento e deliberado: o teorema **nao** vale partindo de
    um ponto que nao seja o centro de massa. Para ir de um ponto arbitrario a
    outro, volte pelo centro. Ver :meth:`MassProperties.inertia_about`.
    """
    tensor = _as_matrix3(inertia_about_cg, "inertia_about_cg")
    d = _as_vector3(displacement_m, "displacement_m")
    if not np.isfinite(mass_kg) or mass_kg <= 0.0:
        raise ValueError(f"massa deve ser positiva e finita, recebeu {mass_kg!r}")
    return tensor + mass_kg * (float(d @ d) * np.eye(3) - np.outer(d, d))


def aggregate_mass_properties(
    components: Iterable[MassComponent],
    reference_point_body_m: ArrayLike | None = None,
    *,
    validate: bool = True,
) -> MassProperties:
    """Agrega componentes em massa, centro de massa e tensor de inercia.

    A ordem das operacoes importa e e esta:

    1. massa total e centro de massa agregado
    2. por componente: rotacionar o tensor proprio para os eixos do corpo
    3. por componente: transladar do proprio centro ate o ponto de referencia
    4. somar

    Args:
        components: os componentes. Nao pode ser vazio.
        reference_point_body_m: ponto sobre o qual a inercia agregada e expressa.
            Por padrao a origem do referencial do corpo. **Nao** e o centro de
            massa, por decisao de arquitetura (ADR-001).
        validate: valida o tensor agregado ao final.

    Returns:
        As propriedades agregadas, carregando o ponto de referencia usado.
    """
    items = list(components)
    if not items:
        raise ValueError("a lista de componentes esta vazia")

    names = [c.name for c in items]
    duplicates = {n for n in names if names.count(n) > 1}
    if duplicates:
        raise ValueError(f"nomes de componente duplicados: {sorted(duplicates)}")

    reference = (
        np.zeros(3)
        if reference_point_body_m is None
        else _as_vector3(reference_point_body_m, "reference_point_body_m")
    )

    # 1. massa e centro primeiro
    mass_total = float(sum(c.mass_kg for c in items))
    weighted = np.zeros(3)
    for c in items:
        weighted += c.mass_kg * c.center_of_mass_body_m
    center_of_mass = weighted / mass_total

    # 2 e 3. rotacionar, depois transladar, componente a componente
    inertia_total = np.zeros((3, 3))
    for c in items:
        inertia_body_axes = rotate_inertia(
            c.inertia_about_own_cg_kg_m2, c.orientation_body_from_component
        )
        displacement = c.center_of_mass_body_m - reference
        inertia_total += parallel_axis(inertia_body_axes, c.mass_kg, displacement)

    # 4. simetrizar contra deriva numerica da soma
    inertia_total = 0.5 * (inertia_total + inertia_total.T)

    if validate:
        validate_inertia_tensor(inertia_total, name="inercia agregada")

    return MassProperties(
        mass_kg=mass_total,
        center_of_mass_body_m=center_of_mass,
        reference_point_body_m=reference,
        inertia_about_reference_kg_m2=inertia_total,
    )
