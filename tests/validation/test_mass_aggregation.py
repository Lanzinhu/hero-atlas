"""Casos analiticos de agregacao de massa.

Ver vault/05 - Verificacao/Casos analiticos.md

Estes testes existem porque somar tensores de inercia sem rotacionar e sem transladar
produz um simulador que voa lindamente no grafico. Cada caso aqui tem solucao fechada
conhecida, entao o teste nao depende de nenhuma outra parte do codigo estar certa.
"""

from __future__ import annotations

import numpy as np
import pytest

from hero_atlas.airframe import (
    MassComponent,
    aggregate_mass_properties,
    parallel_axis,
    rotate_inertia,
)

pytestmark = pytest.mark.validation

ATOL = 1e-12


def rot_z(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rot_x(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


# --------------------------------------------------------------------------- #
# Rotacao de tensor
# --------------------------------------------------------------------------- #


def test_rotacao_de_barra_em_90_graus_troca_os_eixos():
    """Barra no eixo x proprio, girada 90 graus em z, passa a ser barra no eixo y.

    ``diag(0, I, I)``  ->  ``diag(I, 0, I)``

    O eixo de inercia nula acompanha a barra. Se este teste falhar com os valores
    trocados, ha confusao entre ``R`` e a transposta de ``R``.
    """
    inertia_value = 7.5
    rod_along_x = np.diag([0.0, inertia_value, inertia_value])

    rotated = rotate_inertia(rod_along_x, rot_z(np.pi / 2))

    expected = np.diag([inertia_value, 0.0, inertia_value])
    np.testing.assert_allclose(rotated, expected, atol=ATOL)


def test_rotacao_preserva_traco_e_autovalores():
    """Rotacao e mudanca de base: os momentos principais sao invariantes."""
    inertia = np.array([[2.0, 0.3, -0.1], [0.3, 5.0, 0.2], [-0.1, 0.2, 6.0]])
    rotation = rot_z(0.7) @ rot_x(-0.4)

    rotated = rotate_inertia(inertia, rotation)

    assert np.isclose(np.trace(rotated), np.trace(inertia), atol=ATOL)
    np.testing.assert_allclose(np.linalg.eigvalsh(rotated), np.linalg.eigvalsh(inertia), atol=1e-10)


def test_rotacao_identidade_nao_altera_nada():
    inertia = np.diag([1.0, 2.0, 3.0])
    np.testing.assert_allclose(rotate_inertia(inertia, np.eye(3)), inertia, atol=ATOL)


def test_rotacao_rejeita_reflexao():
    """Determinante -1 e reflexao. Passaria despercebida e daria inercia plausivel."""
    reflection = np.diag([1.0, 1.0, -1.0])
    with pytest.raises(ValueError, match="determinante"):
        rotate_inertia(np.eye(3), reflection)


# --------------------------------------------------------------------------- #
# Teorema dos eixos paralelos
# --------------------------------------------------------------------------- #


def test_massa_pontual_deslocada_no_eixo_x():
    """Massa pontual a distancia L no eixo x: ``m * diag(0, L^2, L^2)``.

    Inercia nula em torno do proprio eixo de deslocamento.
    """
    mass, length = 3.0, 2.0

    inertia = parallel_axis(np.zeros((3, 3)), mass, np.array([length, 0.0, 0.0]))

    expected = mass * np.diag([0.0, length**2, length**2])
    np.testing.assert_allclose(inertia, expected, atol=ATOL)


def test_esfera_solida_transladada():
    """Esfera de raio r: ``(2/5) m r^2`` no centro, mais ``m d^2`` perpendicular."""
    mass, radius, distance = 4.0, 0.5, 1.3
    inertia_cg = (2.0 / 5.0) * mass * radius**2 * np.eye(3)

    inertia = parallel_axis(inertia_cg, mass, np.array([distance, 0.0, 0.0]))

    base = (2.0 / 5.0) * mass * radius**2
    expected = np.diag([base, base + mass * distance**2, base + mass * distance**2])
    np.testing.assert_allclose(inertia, expected, atol=ATOL)


def test_deslocamento_nulo_e_identidade():
    inertia = np.diag([1.0, 2.0, 3.0])
    np.testing.assert_allclose(parallel_axis(inertia, 5.0, np.zeros(3)), inertia, atol=ATOL)


def test_sinal_do_deslocamento_nao_importa():
    """A expressao e quadratica em ``d``."""
    inertia = np.diag([1.0, 2.0, 3.0])
    d = np.array([0.3, -0.7, 1.1])
    np.testing.assert_allclose(
        parallel_axis(inertia, 2.0, d), parallel_axis(inertia, 2.0, -d), atol=ATOL
    )


def test_translacao_encadeada_nao_vale_fora_do_centro():
    """O erro classico: transladar de um ponto nao central para outro.

    Aplicar o teorema duas vezes em sequencia, sem voltar pelo centro de massa,
    da resultado diferente do correto. Este teste documenta a diferenca em vez de
    deixa-la aparecer como um voo bonito e falso.
    """
    mass = 2.0
    inertia_cg = np.diag([0.1, 0.2, 0.3])
    first = np.array([1.0, 0.0, 0.0])
    second = np.array([1.0, 1.0, 0.0])

    correto = parallel_axis(inertia_cg, mass, second)
    encadeado_errado = parallel_axis(parallel_axis(inertia_cg, mass, first), mass, second - first)

    assert not np.allclose(correto, encadeado_errado, atol=1e-9)


# --------------------------------------------------------------------------- #
# Agregacao com solucao fechada
# --------------------------------------------------------------------------- #


def test_haltere_de_duas_massas_pontuais():
    """Duas massas ``m`` em ``+-L/2`` no eixo x, sobre o centro.

    ``diag(0, m L^2 / 2, m L^2 / 2)``
    """
    mass, length = 1.5, 0.8
    components = [
        MassComponent.point_mass("esq", mass, [-length / 2, 0.0, 0.0]),
        MassComponent.point_mass("dir", mass, [+length / 2, 0.0, 0.0]),
    ]

    props = aggregate_mass_properties(components)

    assert np.isclose(props.mass_kg, 2 * mass, atol=ATOL)
    np.testing.assert_allclose(props.center_of_mass_body_m, np.zeros(3), atol=ATOL)
    expected = np.diag([0.0, mass * length**2 / 2, mass * length**2 / 2])
    np.testing.assert_allclose(props.inertia_about_reference_kg_m2, expected, atol=ATOL)


def test_quatro_massas_nos_cantos_de_um_quadrado():
    """Quatro massas ``m`` em ``(+-a/2, +-a/2, 0)``, sobre o centro.

    ``diag(m a^2, m a^2, 2 m a^2)``, com produtos de inercia nulos por simetria.
    """
    mass, side = 0.75, 1.2
    half = side / 2
    components = [
        MassComponent.point_mass(f"m{i}", mass, [sx * half, sy * half, 0.0])
        for i, (sx, sy) in enumerate([(+1, +1), (+1, -1), (-1, +1), (-1, -1)])
    ]

    props = aggregate_mass_properties(components)
    inertia = props.inertia_about_reference_kg_m2

    expected = np.diag([mass * side**2, mass * side**2, 2 * mass * side**2])
    np.testing.assert_allclose(inertia, expected, atol=ATOL)

    off_diagonal = inertia - np.diag(np.diag(inertia))
    np.testing.assert_allclose(off_diagonal, np.zeros((3, 3)), atol=ATOL)


def test_barra_montada_a_partir_de_duas_meias_barras():
    """O caso mais completo: exercita rotacao, translacao e soma de uma vez.

    Uma barra uniforme de massa ``M`` e comprimento ``L`` tem ``M L^2 / 12`` nos
    eixos transversais. Montada a partir de duas meias-barras de massa ``M/2`` e
    comprimento ``L/2``, centradas em ``+-L/4``, o agregado tem que dar exatamente
    a mesma coisa.

    Se a translacao estiver faltando, o resultado sai ``M L^2 / 48``, quatro vezes
    menor, e um numero quatro vezes menor de inercia e um traje que responde quatro
    vezes rapido demais.
    """
    total_mass, total_length = 6.0, 2.0
    half_mass, half_length = total_mass / 2, total_length / 2

    # Meia barra ao longo de x: inercia nula em x, uniforme nos transversais.
    half_rod_inertia = half_mass * half_length**2 / 12
    inertia_own = np.diag([0.0, half_rod_inertia, half_rod_inertia])

    components = [
        MassComponent(
            name="metade_esquerda",
            mass_kg=half_mass,
            center_of_mass_body_m=np.array([-total_length / 4, 0.0, 0.0]),
            inertia_about_own_cg_kg_m2=inertia_own,
            orientation_body_from_component=np.eye(3),
        ),
        MassComponent(
            name="metade_direita",
            mass_kg=half_mass,
            center_of_mass_body_m=np.array([+total_length / 4, 0.0, 0.0]),
            inertia_about_own_cg_kg_m2=inertia_own,
            orientation_body_from_component=np.eye(3),
        ),
    ]

    props = aggregate_mass_properties(components)

    full_rod = total_mass * total_length**2 / 12
    expected = np.diag([0.0, full_rod, full_rod])
    np.testing.assert_allclose(props.inertia_about_reference_kg_m2, expected, atol=1e-12)
    assert np.isclose(props.mass_kg, total_mass, atol=ATOL)


def test_componente_com_eixos_proprios_girados_da_o_mesmo_resultado():
    """A mesma barra, com a inercia declarada em eixos proprios girados 90 graus.

    A matriz de orientacao compensa. Se o codigo usar a transposta de ``R`` no lugar
    de ``R``, este teste falha e o anterior passa, que e exatamente a assinatura do
    bug mais dificil de achar nesta area.
    """
    total_mass, total_length = 6.0, 2.0
    half_mass, half_length = total_mass / 2, total_length / 2
    half_rod_inertia = half_mass * half_length**2 / 12

    # Nos eixos proprios a barra esta no eixo y do componente, nao no x.
    inertia_own_rotated = np.diag([half_rod_inertia, 0.0, half_rod_inertia])
    # R leva o eixo y do componente ao eixo x do corpo.
    orientation = rot_z(-np.pi / 2)

    components = [
        MassComponent(
            name=name,
            mass_kg=half_mass,
            center_of_mass_body_m=np.array([sign * total_length / 4, 0.0, 0.0]),
            inertia_about_own_cg_kg_m2=inertia_own_rotated,
            orientation_body_from_component=orientation,
        )
        for name, sign in [("metade_esquerda", -1), ("metade_direita", +1)]
    ]

    props = aggregate_mass_properties(components)

    full_rod = total_mass * total_length**2 / 12
    expected = np.diag([0.0, full_rod, full_rod])
    np.testing.assert_allclose(props.inertia_about_reference_kg_m2, expected, atol=1e-12)


def test_ponto_de_referencia_deslocado_e_volta_pelo_centro():
    """``inertia_about_cg`` desfaz exatamente o teorema, e ``inertia_about`` refaz.

    O ponto de referencia e parte do resultado, nao um detalhe: por ADR-001 a
    dinamica e escrita sobre um ponto fixo, nao sobre o centro que migra.
    """
    mass, length = 1.5, 0.8
    offset = np.array([0.37, -0.21, 0.05])
    components = [
        MassComponent.point_mass("esq", mass, [-length / 2, 0.0, 0.0]),
        MassComponent.point_mass("dir", mass, [+length / 2, 0.0, 0.0]),
    ]

    about_origin = aggregate_mass_properties(components)
    about_offset = aggregate_mass_properties(components, reference_point_body_m=offset)

    # O centro de massa nao depende de onde se olha.
    np.testing.assert_allclose(
        about_origin.center_of_mass_body_m, about_offset.center_of_mass_body_m, atol=ATOL
    )
    # A inercia sobre o centro tambem nao.
    np.testing.assert_allclose(
        about_origin.inertia_about_cg_kg_m2,
        about_offset.inertia_about_cg_kg_m2,
        atol=1e-12,
    )
    # E dar a volta reproduz o valor sobre a referencia deslocada.
    np.testing.assert_allclose(
        about_origin.inertia_about(offset),
        about_offset.inertia_about_reference_kg_m2,
        atol=1e-12,
    )


def test_centro_de_massa_de_componentes_assimetricos():
    """Media ponderada simples, mas e o passo 1 e tudo depende dele."""
    components = [
        MassComponent.point_mass("a", 1.0, [0.0, 0.0, 0.0]),
        MassComponent.point_mass("b", 3.0, [4.0, 0.0, 0.0]),
    ]

    props = aggregate_mass_properties(components)

    np.testing.assert_allclose(props.center_of_mass_body_m, np.array([3.0, 0.0, 0.0]), atol=ATOL)
    assert np.isclose(props.mass_kg, 4.0, atol=ATOL)


def test_agregacao_independe_da_ordem_dos_componentes():
    rng = np.random.default_rng(42)
    components = [
        MassComponent.point_mass(f"m{i}", float(rng.uniform(0.5, 5.0)), rng.uniform(-1, 1, 3))
        for i in range(8)
    ]

    direto = aggregate_mass_properties(components)
    invertido = aggregate_mass_properties(list(reversed(components)))

    np.testing.assert_allclose(
        direto.inertia_about_reference_kg_m2,
        invertido.inertia_about_reference_kg_m2,
        atol=1e-12,
    )
