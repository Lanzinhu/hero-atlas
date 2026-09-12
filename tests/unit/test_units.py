"""Unidades: conversao afim e validacao de dimensao na fronteira."""

from __future__ import annotations

import pytest

from hero_atlas.units import (
    G0,
    DimensionError,
    UnitError,
    convert,
    dimension_of,
    from_si,
    known_units,
    require_dimension,
    si_unit_for,
    to_si,
)

pytestmark = pytest.mark.unit


def test_kgf_para_newton_usa_a_gravidade_padrao():
    assert to_si(1.0, "kgf") == pytest.approx(G0)
    assert to_si(150.0, "kgf") == pytest.approx(1471.0, abs=0.1)


def test_o_exemplo_de_referencia_do_projeto():
    """117 kgf de peso, que e o caso de calibracao do marco 1."""
    assert to_si(117.0, "kgf") == pytest.approx(1147.38, abs=0.01)


def test_lbf_para_newton():
    assert to_si(1.0, "lbf") == pytest.approx(4.4482216152605)
    # JB-12: 528 lbf declarados
    assert to_si(528.0, "lbf") / G0 == pytest.approx(239.4, abs=0.2)


def test_rpm_para_radianos_por_segundo():
    # 35 mil rpm e o limite inferior da faixa de microturbina
    assert to_si(35_000.0, "rpm") == pytest.approx(3665.19, abs=0.01)
    # e a frequencia de eixo correspondente e 583 Hz
    assert pytest.approx(583.33, abs=0.01) == 35_000.0 / 60.0


def test_temperatura_tem_offset():
    assert to_si(0.0, "degC") == pytest.approx(273.15)
    assert to_si(15.0, "degC") == pytest.approx(288.15)  # ISA ao nivel do mar
    assert to_si(32.0, "degF") == pytest.approx(273.15)
    assert to_si(212.0, "degF") == pytest.approx(373.15)


@pytest.mark.parametrize("unit", known_units())
def test_conversao_de_ida_e_volta_e_exata(unit: str):
    for value in (-40.0, 0.0, 1.0, 1234.5):
        assert from_si(to_si(value, unit), unit) == pytest.approx(value, abs=1e-9)


def test_convert_entre_unidades_da_mesma_dimensao():
    assert convert(1.0, "km/h", "m/s") == pytest.approx(1 / 3.6)
    assert convert(1000.0, "g", "kg") == pytest.approx(1.0)
    assert convert(180.0, "deg", "rad") == pytest.approx(3.14159265, abs=1e-8)


def test_convert_recusa_dimensoes_diferentes():
    """E isto que impede um campo de massa receber newton."""
    with pytest.raises(DimensionError, match="mass"):
        convert(1.0, "kg", "N")


def test_require_dimension_e_a_guarda_da_fronteira():
    require_dimension("kgf", "force")  # nao levanta

    with pytest.raises(DimensionError) as exc:
        require_dimension("N", "mass")
    assert "mass" in str(exc.value)
    assert "force" in str(exc.value)


def test_unidade_desconhecida_falha_com_lista():
    with pytest.raises(UnitError, match="unidade desconhecida"):
        to_si(1.0, "furlongs_por_quinzena")


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("kgf", "force"),
        ("kg", "mass"),
        ("rpm", "angular_velocity"),
        ("L/min", "volume_flow"),
        ("kg*m^2", "inertia"),
        ("Wh/kg", "specific_energy"),
        ("kg/(kgf*h)", "tsfc"),
        ("-", "dimensionless"),
    ],
)
def test_dimensao_das_unidades_do_projeto(unit: str, expected: str):
    assert dimension_of(unit) == expected


def test_toda_dimensao_tem_unidade_si_canonica():
    for unit in known_units():
        assert si_unit_for(dimension_of(unit))


def test_consumo_da_jetcat_p400_em_si():
    """1,04 kg/min de catalogo, que e o numero que fecha a autonomia do Gravity."""
    assert to_si(1.04, "kg/min") == pytest.approx(0.017333, abs=1e-6)


def test_tsfc_de_catalogo_converte_para_si():
    """TSFC 1,54 kg/(kgf*h) da JetCat P400 Pro."""
    si = to_si(1.54, "kg/(kgf*h)")
    assert si == pytest.approx(1.54 / (G0 * 3600.0), rel=1e-12)
