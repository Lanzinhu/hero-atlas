"""Deck de CAD: conversao de unidade e as recusas que impedem deck silenciosamente errado.

⚠ Estes testes **nao precisam do FreeCAD instalado**, e isso e deliberado. O nucleo le
um arquivo; quem escreve o arquivo roda noutro processo, noutra versao de Python. Se a
suite passasse a exigir FreeCAD, o isolamento do nucleo teria sido perdido sem ninguem
perceber.

O grupo mais importante e o da **conferencia analitica**. A conversao do tensor tem um
fator que, se esquecido, produz inercia plausivel e errada, e simulacao com inercia
errada roda liso e mente.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pytest

from hero_atlas.airframe.cad_deck import (
    CadComponentRecord,
    CadDeck,
    CadDeckError,
    inertia_from_freecad,
    load_cad_deck,
)
from hero_atlas.airframe.mass_properties import aggregate_mass_properties

pytestmark = pytest.mark.validation


def caixa_freecad(a_mm: float, b_mm: float, c_mm: float) -> tuple[np.ndarray, float]:
    """Tensor que o FreeCAD devolve para uma caixa, com densidade unitaria.

    Com densidade um, a "massa" embutida e o volume em milimetro cubico, entao

        I_xx = V * (b^2 + c^2) / 12      com tudo em milimetro
    """
    volume = a_mm * b_mm * c_mm
    tensor = np.diag(
        [
            volume * (b_mm**2 + c_mm**2) / 12.0,
            volume * (a_mm**2 + c_mm**2) / 12.0,
            volume * (a_mm**2 + b_mm**2) / 12.0,
        ]
    )
    return tensor, volume


# ---------------------------------------------------------------------------
# Conversao de unidade, conferida contra solucao analitica
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a_mm", "b_mm", "c_mm", "massa_kg"),
    [
        (100.0, 200.0, 300.0, 1.0),
        (100.0, 200.0, 300.0, 7.5),
        (50.0, 50.0, 50.0, 2.2),
        (400.0, 30.0, 30.0, 0.8),
    ],
)
def test_caixa_bate_com_a_solucao_analitica(
    a_mm: float, b_mm: float, c_mm: float, massa_kg: float
) -> None:
    tensor, volume = caixa_freecad(a_mm, b_mm, c_mm)
    obtido = inertia_from_freecad(tensor, mass_kg=massa_kg, volume_mm3=volume)

    a, b, c = a_mm / 1000.0, b_mm / 1000.0, c_mm / 1000.0
    esperado = np.diag(
        [
            massa_kg * (b**2 + c**2) / 12.0,
            massa_kg * (a**2 + c**2) / 12.0,
            massa_kg * (a**2 + b**2) / 12.0,
        ]
    )
    assert obtido == pytest.approx(esperado, rel=1e-12)


def test_cilindro_bate_com_a_solucao_analitica() -> None:
    """Segunda forma, independente da caixa, para nao casar erro com erro."""
    raio_mm, altura_mm, massa_kg = 60.0, 299.0, 2.2
    volume = math.pi * raio_mm**2 * altura_mm
    lateral = volume * (3.0 * raio_mm**2 + altura_mm**2) / 12.0
    axial = volume * raio_mm**2 / 2.0
    tensor = np.diag([lateral, lateral, axial])

    obtido = inertia_from_freecad(tensor, mass_kg=massa_kg, volume_mm3=volume)
    r, h = raio_mm / 1000.0, altura_mm / 1000.0
    esperado = np.diag(
        [
            massa_kg * (3.0 * r**2 + h**2) / 12.0,
            massa_kg * (3.0 * r**2 + h**2) / 12.0,
            massa_kg * r**2 / 2.0,
        ]
    )
    assert obtido == pytest.approx(esperado, rel=1e-12)


def test_a_conversao_escala_com_a_massa_e_nao_com_o_volume() -> None:
    """Dobrar a massa dobra a inercia; dobrar o volume com a mesma massa nao."""
    tensor, volume = caixa_freecad(100.0, 200.0, 300.0)
    leve = inertia_from_freecad(tensor, mass_kg=1.0, volume_mm3=volume)
    pesado = inertia_from_freecad(tensor, mass_kg=2.0, volume_mm3=volume)
    assert pesado == pytest.approx(2.0 * leve)


def test_esquecer_o_volume_seria_um_erro_grande_e_silencioso() -> None:
    """Prende a ordem de grandeza do erro que a conversao evita.

    Sem dividir pelo volume, a inercia sai errada por um fator da ordem da densidade.
    Nada na simulacao acusa: ela roda lisa e o veiculo so fica preguicoso demais.
    """
    tensor, volume = caixa_freecad(100.0, 200.0, 300.0)
    certo = inertia_from_freecad(tensor, mass_kg=1.0, volume_mm3=volume)
    errado = tensor * 1.0e-6  # sem dividir pelo volume
    assert np.max(errado) / np.max(certo) > 1.0e5


@pytest.mark.parametrize("volume", [0.0, -1.0, float("nan"), float("inf")])
def test_volume_invalido_e_recusado(volume: float) -> None:
    """Volume nulo costuma significar solido aberto ou malha nao fechada no CAD."""
    with pytest.raises(CadDeckError, match="[Vv]olume"):
        inertia_from_freecad(np.eye(3), mass_kg=1.0, volume_mm3=volume)


@pytest.mark.parametrize("massa", [0.0, -2.0, float("nan")])
def test_massa_invalida_e_recusada(massa: float) -> None:
    with pytest.raises(CadDeckError, match="[Mm]assa"):
        inertia_from_freecad(np.eye(3), mass_kg=massa, volume_mm3=1000.0)


def test_tensor_de_forma_errada_e_recusado() -> None:
    with pytest.raises(CadDeckError, match=r"\(3, 3\)"):
        inertia_from_freecad(np.eye(4), mass_kg=1.0, volume_mm3=1000.0)


# ---------------------------------------------------------------------------
# O deck, e as recusas
# ---------------------------------------------------------------------------


def registro(nome: str = "peca", **mudancas) -> CadComponentRecord:
    tensor, volume = caixa_freecad(100.0, 200.0, 300.0)
    base = dict(
        name=nome,
        mass_kg=1.0,
        volume_mm3=volume,
        center_of_mass_mm=np.array([50.0, 100.0, 150.0]),
        inertia_matrix_freecad=tensor,
        orientation_body_from_component=np.eye(3),
    )
    base.update(mudancas)
    return CadComponentRecord(**base)  # type: ignore[arg-type]


def deck(**mudancas) -> CadDeck:
    base = dict(
        source_document="teste.FCStd",
        exported_at="2026-09-12T00:00:00",
        z_axis_down=True,
        components=(registro(),),
    )
    base.update(mudancas)
    return CadDeck(**base)  # type: ignore[arg-type]


def test_milimetro_vira_metro_no_centro() -> None:
    componente = registro().to_mass_component()
    assert componente.center_of_mass_body_m == pytest.approx([0.05, 0.10, 0.15])


def test_deck_com_z_para_cima_e_recusado() -> None:
    """Consertar na leitura esconderia o problema de quem abrir o arquivo de CAD."""
    with pytest.raises(CadDeckError, match="z para BAIXO"):
        deck(z_axis_down=False)


def test_deck_vazio_e_recusado() -> None:
    with pytest.raises(CadDeckError, match="nenhum componente"):
        deck(components=())


def test_nome_repetido_e_recusado() -> None:
    with pytest.raises(CadDeckError, match="repetidos"):
        deck(components=(registro("a"), registro("a")))


def test_versao_desconhecida_de_esquema_e_recusada() -> None:
    with pytest.raises(CadDeckError, match="versao"):
        deck(schema_version=99)


def test_reconciliacao_avisa_em_vez_de_substituir() -> None:
    """A fonte de verdade e a massa contabil, nao o CAD.

    O CAD produz propriedades de uma geometria assumida: material errado, parede fina
    demais, peca faltando. Divergencia pede olho humano, nao substituicao silenciosa.
    """
    d = deck(components=(registro(mass_kg=10.0),))
    assert d.reconcile(10.1) is None
    aviso = d.reconcile(15.0)
    assert aviso is not None
    assert "massa contabil" in aviso
    assert "33" in aviso or "-5.00" in aviso


def test_deck_alimenta_o_agregador() -> None:
    """O caminho inteiro: deck, componentes, agregacao."""
    tensor, volume = caixa_freecad(100.0, 100.0, 100.0)
    d = deck(
        components=(
            registro(
                "esq",
                volume_mm3=volume,
                inertia_matrix_freecad=tensor,
                center_of_mass_mm=np.array([0.0, -500.0, 0.0]),
                mass_kg=2.0,
            ),
            registro(
                "dir",
                volume_mm3=volume,
                inertia_matrix_freecad=tensor,
                center_of_mass_mm=np.array([0.0, 500.0, 0.0]),
                mass_kg=2.0,
            ),
        )
    )
    agregado = aggregate_mass_properties(d.to_mass_components())
    assert agregado.mass_kg == pytest.approx(4.0)
    assert agregado.center_of_mass_body_m == pytest.approx([0.0, 0.0, 0.0], abs=1e-12)
    # eixos paralelos: 2 pecas de 2 kg a 0,5 m do centro contribuem 2*m*d^2 em x e z
    assert agregado.inertia_about_cg_kg_m2[0, 0] == pytest.approx(
        2.0 * (2.0 * (0.1**2 + 0.1**2) / 12.0) + 2.0 * 2.0 * 0.5**2, rel=1e-12
    )


# ---------------------------------------------------------------------------
# Leitura de arquivo
# ---------------------------------------------------------------------------


def test_arquivo_ausente_e_recusado(tmp_path) -> None:
    with pytest.raises(CadDeckError, match="nao encontrado"):
        load_cad_deck(tmp_path / "nao-existe.json")


def test_json_invalido_e_recusado(tmp_path) -> None:
    caminho = tmp_path / "ruim.json"
    caminho.write_text("{isto nao e json", encoding="utf-8")
    with pytest.raises(CadDeckError, match="nao e JSON"):
        load_cad_deck(caminho)


def test_componente_sem_campo_obrigatorio_e_recusado(tmp_path) -> None:
    caminho = tmp_path / "incompleto.json"
    caminho.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "z_axis_down": True,
                "components": [{"name": "x", "mass_kg": 1.0}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(CadDeckError, match="malformado"):
        load_cad_deck(caminho)


def test_ciclo_completo_de_arquivo(tmp_path) -> None:
    tensor, volume = caixa_freecad(100.0, 200.0, 300.0)
    caminho = tmp_path / "deck.json"
    caminho.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "source_document": "x.FCStd",
                "exported_at": "2026-09-12T10:00:00",
                "z_axis_down": True,
                "components": [
                    {
                        "name": "caixa",
                        "mass_kg": 1.0,
                        "volume_mm3": volume,
                        "center_of_mass_mm": [50.0, 100.0, 150.0],
                        "inertia_matrix": tensor.tolist(),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    d = load_cad_deck(caminho)
    assert d.total_mass_kg == pytest.approx(1.0)
    componente = d.to_mass_components()[0]
    assert componente.inertia_about_own_cg_kg_m2[0, 0] == pytest.approx(
        (0.2**2 + 0.3**2) / 12.0, rel=1e-12
    )
