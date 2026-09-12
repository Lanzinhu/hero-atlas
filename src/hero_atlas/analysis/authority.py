"""Mapa de autoridade: o que a geometria consegue produzir, antes de qualquer controle.

Ver vault/06 - Marcos/Marco 2 - Trim e autoridade.md

Este modulo responde perguntas de **condicao geometrica**, nao de proposta de
arquitetura fisica:

    Para quais valores de (envergadura, altura, inclinacao, posicao, centro de massa)
    o espaco coluna da matriz de alocacao contem os wrenches de trim exigidos?

O resultado e um mapa, nao uma recomendacao de hardware.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..airframe.geometry import PropulsionGeometry, allocation_matrix
from ..model_status import PROPULSAO_INSTALADA_HOJE, ModelStatus
from .trim import InfeasibilityCause, solve_trim

__all__ = [
    "AuthorityMap",
    "WrenchAxis",
    "analyse_authority",
    "can_produce",
    "cg_window",
    "lateral_cg_authority",
    "single_failure_survey",
    "thrust_null_space",
]

WrenchAxis = ("Fx", "Fy", "Fz", "Mx", "My", "Mz")
"""Rotulos das seis linhas da matriz de alocacao."""

_SINGULAR_TOL = 1e-9


def thrust_null_space(geometry: PropulsionGeometry) -> NDArray[np.float64]:
    """Combinacoes de empuxo que produzem wrench **nulo**.

    Cada vetor devolvido e uma carga interna: os propulsores brigam entre si e o
    resultado se cancela exatamente. Cada dimensao aqui e **um grau de liberdade de
    atuador desperdicado**, e explica por que contar propulsores superestima
    autoridade.

    Forma ``(N, k)``, com ``k`` a dimensao do nucleo.
    """
    W = allocation_matrix(geometry)
    _u, s, vt = np.linalg.svd(W)
    posto = int(np.sum(s > _SINGULAR_TOL * max(s[0], 1.0)))
    return vt[posto:, :].T


@dataclass(frozen=True, slots=True)
class AuthorityMap:
    """O que a geometria pode e o que nao pode, sem falar de controlador ainda."""

    rank: int
    singular_values: NDArray[np.float64]
    unreachable_directions: NDArray[np.float64]
    null_space: NDArray[np.float64]
    zero_rows: tuple[str, ...]
    condition_number: float
    status: ModelStatus = PROPULSAO_INSTALADA_HOJE

    @property
    def full_rank(self) -> bool:
        """Se os seis graus de wrench sao alcancaveis independentemente."""
        return self.rank == 6

    @property
    def wasted_actuator_freedoms(self) -> int:
        """Quantos graus de liberdade de atuador nao produzem efeito nenhum.

        Contar propulsores superestima autoridade exatamente nesta quantidade.
        """
        return self.null_space.shape[1]

    @property
    def smallest_nonzero_singular(self) -> float:
        """A direcao mais fraca ainda atingivel.

        Pequena significa que aquela direcao existe no papel mas exige empuxo
        desproporcional, o que a torna inutil na pratica.
        """
        s = self.singular_values
        validos = s[s > _SINGULAR_TOL * max(s[0], 1.0)]
        return float(validos[-1]) if validos.size else 0.0

    def dominant_axes(self, direction_index: int = 0) -> tuple[tuple[str, float], ...]:
        """Quais eixos de wrench compoem uma direcao inatingivel."""
        if direction_index >= self.unreachable_directions.shape[1]:
            return ()
        v = self.unreachable_directions[:, direction_index]
        ordem = np.argsort(-np.abs(v))
        return tuple((WrenchAxis[i], float(v[i])) for i in ordem if abs(v[i]) > 1e-3)


def analyse_authority(
    geometry: PropulsionGeometry, *, status: ModelStatus = PROPULSAO_INSTALADA_HOJE
) -> AuthorityMap:
    """Decompoe a matriz de alocacao e devolve o que ela consegue produzir."""
    W = allocation_matrix(geometry)
    u, s, vt = np.linalg.svd(W)
    escala = max(s[0], 1.0) if s.size else 1.0
    posto = int(np.sum(s > _SINGULAR_TOL * escala))

    validos = s[s > _SINGULAR_TOL * escala]
    condicao = float(validos[0] / validos[-1]) if validos.size else float("inf")

    linhas_nulas = tuple(WrenchAxis[i] for i in range(6) if np.allclose(W[i, :], 0.0, atol=1e-12))

    return AuthorityMap(
        rank=posto,
        singular_values=s,
        unreachable_directions=u[:, posto:],
        null_space=vt[posto:, :].T,
        zero_rows=linhas_nulas,
        condition_number=condicao,
        status=status,
    )


def cg_window(
    geometry: PropulsionGeometry,
    *,
    mass_kg: float,
    axis: int,
    span_m: tuple[float, float] = (-0.30, 0.50),
    step_m: float = 0.005,
    fixed_cg_m: ArrayLike = (0.0, 0.0, 0.0),
) -> tuple[float, float] | None:
    """Faixa de posicao de centro de massa que admite trim, ao longo de um eixo.

    ⚠ O resultado e condicionado a **pairado nivelado, sem aceleracao lateral, com
    a geometria nominal e os atuadores disponiveis**. Nao e uma propriedade do
    conceito em geral.

    Args:
        axis: 0 longitudinal, 1 lateral, 2 vertical.
        fixed_cg_m: onde ficam os outros dois eixos durante a varredura.

    Returns:
        ``(minimo, maximo)`` ou ``None`` quando nenhuma posicao admite trim.
    """
    if axis not in (0, 1, 2):
        raise ValueError("eixo precisa ser 0, 1 ou 2")

    base = np.asarray(fixed_cg_m, dtype=np.float64).copy()
    viaveis: list[float] = []

    for valor in np.arange(span_m[0], span_m[1] + step_m, step_m):
        centro = base.copy()
        centro[axis] = float(valor)
        if solve_trim(geometry, mass_kg=mass_kg, center_of_mass_body_m=centro).feasible:
            viaveis.append(float(valor))

    return (min(viaveis), max(viaveis)) if viaveis else None


def single_failure_survey(
    geometry: PropulsionGeometry,
    *,
    mass_kg: float,
    center_of_mass_body_m: ArrayLike,
) -> dict[str, InfeasibilityCause]:
    """Existe trim estatico apos perder **cada** propulsor, um de cada vez.

    ⚠ Este resultado vem do solver, nao do posto. Remover um atuador pode manter o
    posto e ainda assim preservar ou destruir um trim particular; so resolvendo se
    descobre. Concluir de "posto 4 com cinco atuadores" seria raciocinio invalido.

    Returns:
        nome do propulsor -> causa da inviabilidade, ou ``NONE`` quando ha trim.
    """
    resultado: dict[str, InfeasibilityCause] = {}
    for bocal in geometry.nozzles:
        degradada = geometry.fail(bocal.name)
        solucao = solve_trim(
            degradada, mass_kg=mass_kg, center_of_mass_body_m=center_of_mass_body_m
        )
        resultado[bocal.name] = solucao.cause
    return resultado


def can_produce(geometry: PropulsionGeometry, wrench: ArrayLike, *, tol: float = 1e-8) -> bool:
    """Se um wrench esta no espaco coluna, ignorando limites de empuxo.

    Responde a pergunta **geometrica**: existe algum vetor de empuxos, por maior que
    seja, que produza esta combinacao de forca e momento? Separa impossibilidade de
    arquitetura de falta de capacidade, que e a distincao que o ADR-007 exige.
    """
    alvo = np.asarray(wrench, dtype=np.float64)
    if alvo.shape != (6,):
        raise ValueError(f"wrench deve ter 6 componentes, recebeu {alvo.shape}")
    W = allocation_matrix(geometry)
    solucao, *_ = np.linalg.lstsq(W, alvo, rcond=None)
    return bool(np.linalg.norm(W @ solucao - alvo) <= tol * max(1.0, float(np.linalg.norm(alvo))))


def lateral_cg_authority(geometry: PropulsionGeometry) -> bool:
    """Se a geometria consegue rolagem pura, sem forca lateral.

    ⚠ **E o filtro que elimina a maior parte das arquiteturas de traje.**

    Um centro de massa deslocado lateralmente exige momento de rolagem **sem** forca
    lateral. Numa arquitetura de pares simetricos, isso vem dos graus de liberdade
    antissimetricos, que precisam gerar tres grandezas: forca lateral, rolagem e
    guinada.

    Dois pares dao no maximo dois graus antissimetricos, e dois nao cobrem tres.

    ⚠ **E contagem de pares nao basta.** Na familia varrida, tres pares diferindo
    apenas em altura, ou apenas em envergadura, ou nos dois juntos, continuam sem
    rolagem pura. Diferenca de **inclinacao** foi o que bastou.

    ⚠ **A condicao geral e diversidade das colunas, nao um parametro especifico.**
    A propriedade matematica e o posto da matriz de alocacao; qualquer geometria que
    gere colunas independentes serve, e a varredura so testou uma familia.

    ⚠ E **posto nao e margem**. As variantes que conseguem rolagem pura tem menor
    valor singular cerca de cinco a dez vezes menor que as que nao conseguem: a
    direcao existe, e exige redistribuicao enorme de empuxo para ser usada. Ver
    :attr:`AuthorityMap.smallest_nonzero_singular`.

    Verificado em tools/sweep_geometry.py.
    """
    return can_produce(geometry, [0.0, 0.0, 0.0, 1.0, 0.0, 0.0])
