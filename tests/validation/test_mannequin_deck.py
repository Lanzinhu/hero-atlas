"""Manequim do piloto: invariantes físicas e banda de sanidade contra o corpo inteiro.

Ver docs/sources/matsuo-1995-inercia-corpo-inteiro.md e
docs/sources/de-leva-1996-segmentos-NAO-VERIFICADO.md

⚠ Estes testes **não precisam do FreeCAD instalado**. Eles leem os decks versionados em
``docs/decks/manequim/``, gerados por ``tools/freecad_mannequin.py``. Se o gerador mudar,
os decks precisam ser regenerados, e estes testes dizem se a mudança alterou algo que
não devia.

O que é testado, em ordem de força:

1. **Invariantes que não dependem de fonte nenhuma:** massa total, simetria lateral,
   tensor simétrico e positivo definido.
2. **Direção do efeito da pose:** braços à frente movem o centro para frente e criam
   produto de inércia. Isso é física, não tabela.
3. **Banda de sanidade** contra a regressão de Matsuo et al. (1995). ⚠ É banda, não
   validação: a regressão é de adolescentes deitados, extrapolada para um adulto, e o
   mapeamento entre os eixos dela e os do projeto não está definido no resumo.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hero_atlas.airframe.cad_deck import load_cad_deck
from hero_atlas.airframe.mass_properties import aggregate_mass_properties

pytestmark = pytest.mark.validation

PASTA = Path(__file__).resolve().parents[2] / "docs" / "decks" / "manequim"
MASSA_KG = 80.0
ESTATURA_M = 1.75

# Matsuo et al. 1995, J Biomech 28:219-223, resumo verificado via Europe PMC.
IMX_MATSUO = 3.44 * ESTATURA_M**2 + 0.144 * MASSA_KG - 8.04
IMY_MATSUO = 3.52 * ESTATURA_M**2 + 0.125 * MASSA_KG - 7.78

BANDA_SANIDADE = 0.15
"""Tolerância contra a média das duas regressões. ⚠ Escolha declarada, maior que o erro de
estimativa de 5% da própria regressão, porque há extrapolação de população e de postura."""


def agregado(pose: str):
    deck = load_cad_deck(PASTA / f"manequim_{pose}.json")
    return deck, aggregate_mass_properties(deck.to_mass_components())


@pytest.fixture(scope="module", params=["anatomica", "pairado"])
def pose(request):
    return request.param


# ---------------------------------------------------------------------------
# 1. Invariantes, sem fonte externa
# ---------------------------------------------------------------------------


def test_massa_total_e_exatamente_a_declarada(pose: str) -> None:
    _, ag = agregado(pose)
    assert ag.mass_kg == pytest.approx(MASSA_KG, abs=1e-6)


def test_quatorze_segmentos(pose: str) -> None:
    deck, _ = agregado(pose)
    assert len(deck.components) == 14


def test_simetria_lateral(pose: str) -> None:
    """Corpo simétrico em y: centro no plano médio e produtos com y nulos."""
    _, ag = agregado(pose)
    tensor = ag.inertia_about_cg_kg_m2
    assert abs(ag.center_of_mass_body_m[1]) < 1e-3
    assert abs(tensor[0, 1]) < 1e-3
    assert abs(tensor[1, 2]) < 1e-3


def test_tensor_simetrico_e_positivo_definido(pose: str) -> None:
    _, ag = agregado(pose)
    tensor = ag.inertia_about_cg_kg_m2
    assert np.allclose(tensor, tensor.T, atol=1e-9)
    assert np.all(np.linalg.eigvalsh(tensor) > 0.0)


def test_eixo_longitudinal_e_o_de_menor_inercia(pose: str) -> None:
    """Um corpo alto e estreito gira mais fácil em torno do próprio eixo vertical."""
    _, ag = agregado(pose)
    tensor = ag.inertia_about_cg_kg_m2
    assert tensor[2, 2] < tensor[0, 0]
    assert tensor[2, 2] < tensor[1, 1]


# ---------------------------------------------------------------------------
# 2. Direção do efeito da pose
# ---------------------------------------------------------------------------


def test_bracos_a_frente_movem_o_centro_para_frente() -> None:
    _, anat = agregado("anatomica")
    _, pair = agregado("pairado")
    assert pair.center_of_mass_body_m[0] > anat.center_of_mass_body_m[0] + 0.010


def test_bracos_a_frente_criam_produto_de_inercia() -> None:
    """A pose de pairado quebra a simetria frente-trás, e aparece Ixz.

    ⚠ A varredura de atraso do passo 5 usou tensor **diagonal**, então ignorou este
    termo. Este teste existe para o termo não voltar a ser esquecido em silêncio.
    """
    _, anat = agregado("anatomica")
    _, pair = agregado("pairado")
    assert abs(pair.inertia_about_cg_kg_m2[0, 2]) > abs(anat.inertia_about_cg_kg_m2[0, 2])
    assert abs(pair.inertia_about_cg_kg_m2[0, 2]) > 0.1


def test_bracos_abertos_aumentam_a_inercia_longitudinal() -> None:
    """Massa longe do eixo vertical: a inércia em torno dele sobe."""
    _, anat = agregado("anatomica")
    _, pair = agregado("pairado")
    assert pair.inertia_about_cg_kg_m2[2, 2] > anat.inertia_about_cg_kg_m2[2, 2]


# ---------------------------------------------------------------------------
# 3. Banda de sanidade contra Matsuo, só na pose comparável
# ---------------------------------------------------------------------------


def test_inercia_transversal_na_banda_de_matsuo() -> None:
    """⚠ Banda, não validação. Ver o docstring do módulo.

    Compara contra a **média** das duas regressões, porque o resumo não define qual eixo
    é o frontal e qual o sagital, e escolher um pareamento seria afirmar o que a fonte
    não diz.
    """
    _, ag = agregado("anatomica")
    tensor = ag.inertia_about_cg_kg_m2
    referencia = 0.5 * (IMX_MATSUO + IMY_MATSUO)
    for valor in (tensor[0, 0], tensor[1, 1]):
        assert abs(valor - referencia) / referencia < BANDA_SANIDADE


def test_centro_de_massa_em_altura_plausivel() -> None:
    """Metade da estatura, com folga larga. ⚠ Sem fonte verificada para o valor exato."""
    _, ag = agregado("anatomica")
    altura_mm = 1250.0 - ag.center_of_mass_body_m[2] * 1000.0
    fracao = altura_mm / (ESTATURA_M * 1000.0)
    assert 0.50 < fracao < 0.62
