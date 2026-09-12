"""Unidades: SI no nucleo, dimensao explicita na fronteira.

Regra do projeto (vault/03 - Regras/Regras de unidades.md):

    Sufixo no nome da variavel ajuda, mas nao impede receber 150 em quilograma-forca
    onde se esperava newton. Por isso cada campo de configuracao carrega a unidade,
    o carregador valida a DIMENSAO, converte para SI e rejeita unidade incompativel.

Conversao afim: ``si = valor * factor + offset``. O offset existe para temperatura.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

__all__ = [
    "DimensionError",
    "KindError",
    "UnitError",
    "UnitSpec",
    "G0",
    "KGF_TO_N",
    "LBF_TO_N",
    "RHO_SEA_LEVEL_ISA",
    "R_DRY_AIR",
    "T_SEA_LEVEL_ISA",
    "P_SEA_LEVEL_ISA",
    "dimension_of",
    "to_si",
    "from_si",
    "convert",
    "require_dimension",
    "require_kind",
    "kind_of",
    "normalized_thrust_rate",
    "si_unit_for",
    "known_units",
]


class UnitError(ValueError):
    """Unidade desconhecida."""


class DimensionError(ValueError):
    """Unidade valida, dimensao errada para o campo."""


class KindError(ValueError):
    """Unidade e dimensao validas, tipo semantico errado para o campo.

    O caso classico: hertz onde se espera taxa normalizada de empuxo. Ambos sao
    ``s^-1``, entao analise dimensional nao pega.
    """


# --------------------------------------------------------------------------- #
# Constantes canonicas
# --------------------------------------------------------------------------- #

G0: Final[float] = 9.80665
"""Aceleracao da gravidade padrao [m/s^2]."""

KGF_TO_N: Final[float] = 9.80665
LBF_TO_N: Final[float] = 4.4482216152605

R_DRY_AIR: Final[float] = 287.05287
"""Constante especifica do ar seco [J/(kg*K)], valor da atmosfera padrao."""

T_SEA_LEVEL_ISA: Final[float] = 288.15
"""Temperatura ao nivel do mar, ISA [K]."""

P_SEA_LEVEL_ISA: Final[float] = 101325.0
"""Pressao ao nivel do mar, ISA [Pa]."""

RHO_SEA_LEVEL_ISA: Final[float] = P_SEA_LEVEL_ISA / (R_DRY_AIR * T_SEA_LEVEL_ISA)
"""Densidade do ar ao nivel do mar, ISA [kg/m^3].

⚠ **Derivada, nao tabelada.** O valor convencional 1,225 e arredondado, e usa-lo
como constante independente faz o modelo discordar de si mesmo em cerca de nove
partes por milhao: o cenario de referencia deixaria de ter razao de densidade
exatamente 1,0, que e uma propriedade que o codigo afirma.

Confere com 1,225 em quatro algarismos significativos, que e a precisao com que a
norma publica o valor.
"""


# --------------------------------------------------------------------------- #
# Registro de unidades
# --------------------------------------------------------------------------- #


@dataclass(frozen=True, slots=True)
class UnitSpec:
    """Como converter uma unidade para SI, e o que ela significa.

    ``si = valor * factor + offset``

    ⚠ Duas camadas, deliberadamente separadas:

    - ``dimension`` governa a **legalidade da conversao**. Duas unidades so se
      convertem entre si quando compartilham dimensao.
    - ``kind`` governa a **compatibilidade de campo**, que e semantica e nao
      dimensional.

    A distincao importa porque hertz, recproco de segundo normalizado e radiano
    por segundo sao todos ``s^-1`` em analise dimensional pura. Recusar frequencia
    de controlador onde se espera taxa normalizada de autoridade **nao pode** ser
    feito por dimensao. E o erro dimensionalmente correto, que e a categoria mais
    sorrateira.

    Quando ``kind`` nao e dado, vale a propria dimensao.
    """

    dimension: str
    factor: float
    offset: float = 0.0
    kind: str | None = None

    @property
    def quantity_kind(self) -> str:
        return self.kind if self.kind is not None else self.dimension


_MIN: Final[float] = 60.0
_H: Final[float] = 3600.0

_UNITS: Final[dict[str, UnitSpec]] = {
    # massa
    "kg": UnitSpec("mass", 1.0),
    "g": UnitSpec("mass", 1e-3),
    "t": UnitSpec("mass", 1e3),
    "lb": UnitSpec("mass", 0.45359237),
    "oz": UnitSpec("mass", 0.028349523125),
    # comprimento
    "m": UnitSpec("length", 1.0),
    "mm": UnitSpec("length", 1e-3),
    "cm": UnitSpec("length", 1e-2),
    "km": UnitSpec("length", 1e3),
    "in": UnitSpec("length", 0.0254),
    "ft": UnitSpec("length", 0.3048),
    "nmi": UnitSpec("length", 1852.0),
    # tempo
    "s": UnitSpec("time", 1.0),
    "ms": UnitSpec("time", 1e-3),
    "us": UnitSpec("time", 1e-6),
    "min": UnitSpec("time", _MIN),
    "h": UnitSpec("time", _H),
    # forca
    "N": UnitSpec("force", 1.0),
    "kN": UnitSpec("force", 1e3),
    "kgf": UnitSpec("force", KGF_TO_N),
    "lbf": UnitSpec("force", LBF_TO_N),
    # taxa de empuxo: o limite de rampa e tao decisivo quanto a constante de tempo
    "N/s": UnitSpec("force_rate", 1.0),
    "kN/s": UnitSpec("force_rate", 1e3),
    "kgf/s": UnitSpec("force_rate", KGF_TO_N),
    # taxa normalizada: derivada DECLARADA, nunca a grandeza fisica do deck.
    # Dimensao propria para nao ser confundida com frequencia.
    "1/s": UnitSpec("normalized_rate", 1.0, kind="normalized_thrust_rate"),
    # torque
    "N*m": UnitSpec("torque", 1.0),
    "N.m": UnitSpec("torque", 1.0),
    "kgf*m": UnitSpec("torque", KGF_TO_N),
    # momento angular
    "N*m*s": UnitSpec("angular_momentum", 1.0),
    "kg*m^2/s": UnitSpec("angular_momentum", 1.0),
    # angulo
    "rad": UnitSpec("angle", 1.0),
    "deg": UnitSpec("angle", 0.017453292519943295),
    # velocidade angular
    "rad/s": UnitSpec("angular_velocity", 1.0, kind="angular_frequency"),
    "deg/s": UnitSpec("angular_velocity", 0.017453292519943295),
    "rpm": UnitSpec("angular_velocity", 0.10471975511965977, kind="angular_frequency"),
    # aceleracao angular
    "rad/s^2": UnitSpec("angular_acceleration", 1.0),
    "deg/s^2": UnitSpec("angular_acceleration", 0.017453292519943295),
    # velocidade
    "m/s": UnitSpec("velocity", 1.0),
    "km/h": UnitSpec("velocity", 1.0 / 3.6),
    "ft/s": UnitSpec("velocity", 0.3048),
    "kt": UnitSpec("velocity", 0.5144444444444445),
    "ft/min": UnitSpec("velocity", 0.3048 / _MIN),
    "mph": UnitSpec("velocity", 0.44704),
    # aceleracao
    "m/s^2": UnitSpec("acceleration", 1.0),
    "g0": UnitSpec("acceleration", G0),
    # temperatura
    "K": UnitSpec("temperature", 1.0),
    "degC": UnitSpec("temperature", 1.0, 273.15),
    "degF": UnitSpec("temperature", 5.0 / 9.0, 273.15 - 32.0 * 5.0 / 9.0),
    # pressao
    "Pa": UnitSpec("pressure", 1.0),
    "hPa": UnitSpec("pressure", 100.0),
    "kPa": UnitSpec("pressure", 1e3),
    "bar": UnitSpec("pressure", 1e5),
    "psi": UnitSpec("pressure", 6894.757293168361),
    # densidade
    "kg/m^3": UnitSpec("density", 1.0),
    # area e volume
    "m^2": UnitSpec("area", 1.0),
    "cm^2": UnitSpec("area", 1e-4),
    "m^3": UnitSpec("volume", 1.0),
    "L": UnitSpec("volume", 1e-3),
    # inercia
    "kg*m^2": UnitSpec("inertia", 1.0),
    "g*cm^2": UnitSpec("inertia", 1e-7),
    # vazao massica
    "kg/s": UnitSpec("mass_flow", 1.0),
    "kg/min": UnitSpec("mass_flow", 1.0 / _MIN),
    "kg/h": UnitSpec("mass_flow", 1.0 / _H),
    "g/min": UnitSpec("mass_flow", 1e-3 / _MIN),
    "g/s": UnitSpec("mass_flow", 1e-3),
    # vazao volumetrica
    "m^3/s": UnitSpec("volume_flow", 1.0),
    "L/min": UnitSpec("volume_flow", 1e-3 / _MIN),
    "mL/min": UnitSpec("volume_flow", 1e-6 / _MIN),
    # energia
    "J": UnitSpec("energy", 1.0),
    "kJ": UnitSpec("energy", 1e3),
    "MJ": UnitSpec("energy", 1e6),
    "Wh": UnitSpec("energy", _H),
    "kWh": UnitSpec("energy", 1e3 * _H),
    # potencia
    "W": UnitSpec("power", 1.0),
    "kW": UnitSpec("power", 1e3),
    "hp": UnitSpec("power", 745.6998715822702),
    # frequencia
    "Hz": UnitSpec("frequency", 1.0, kind="frequency"),
    "kHz": UnitSpec("frequency", 1e3, kind="frequency"),
    # densidade energetica
    "Wh/kg": UnitSpec("specific_energy", _H),
    "J/kg": UnitSpec("specific_energy", 1.0),
    "MJ/kg": UnitSpec("specific_energy", 1e6),
    # consumo especifico de empuxo: kg por kgf por hora
    "kg/(kgf*h)": UnitSpec("tsfc", 1.0 / (KGF_TO_N * _H)),
    "kg/(N*s)": UnitSpec("tsfc", 1.0),
    # adimensional
    "-": UnitSpec("dimensionless", 1.0),
    "1": UnitSpec("dimensionless", 1.0),
    "%": UnitSpec("dimensionless", 1e-2),
}

_SI_UNIT_FOR: Final[dict[str, str]] = {
    "mass": "kg",
    "length": "m",
    "time": "s",
    "force": "N",
    "force_rate": "N/s",
    "normalized_rate": "1/s",
    "torque": "N*m",
    "angular_momentum": "N*m*s",
    "angle": "rad",
    "angular_velocity": "rad/s",
    "angular_acceleration": "rad/s^2",
    "velocity": "m/s",
    "acceleration": "m/s^2",
    "temperature": "K",
    "pressure": "Pa",
    "density": "kg/m^3",
    "area": "m^2",
    "volume": "m^3",
    "inertia": "kg*m^2",
    "mass_flow": "kg/s",
    "volume_flow": "m^3/s",
    "energy": "J",
    "power": "W",
    "frequency": "Hz",
    "specific_energy": "J/kg",
    "tsfc": "kg/(N*s)",
    "dimensionless": "-",
}


def _spec(unit: str) -> UnitSpec:
    try:
        return _UNITS[unit]
    except KeyError:
        raise UnitError(
            f"unidade desconhecida: {unit!r}. Conhecidas: {', '.join(sorted(_UNITS))}"
        ) from None


def known_units() -> tuple[str, ...]:
    """Todas as unidades aceitas, ordenadas."""
    return tuple(sorted(_UNITS))


def dimension_of(unit: str) -> str:
    """Dimensao fisica de uma unidade, por exemplo ``'force'`` para ``'kgf'``."""
    return _spec(unit).dimension


def si_unit_for(dimension: str) -> str:
    """Unidade SI canonica de uma dimensao."""
    try:
        return _SI_UNIT_FOR[dimension]
    except KeyError:
        raise DimensionError(f"dimensao desconhecida: {dimension!r}") from None


def to_si(value: float, unit: str) -> float:
    """Converte para SI. ``to_si(150, 'kgf')`` devolve 1471,0 N."""
    spec = _spec(unit)
    return value * spec.factor + spec.offset


def from_si(si_value: float, unit: str) -> float:
    """Converte de SI para a unidade dada. Inverso exato de :func:`to_si`."""
    spec = _spec(unit)
    return (si_value - spec.offset) / spec.factor


def convert(value: float, src: str, dst: str) -> float:
    """Converte entre unidades, exigindo que sejam da mesma dimensao."""
    d_src, d_dst = dimension_of(src), dimension_of(dst)
    if d_src != d_dst:
        raise DimensionError(f"nao da para converter {src!r} ({d_src}) para {dst!r} ({d_dst})")
    return from_si(to_si(value, src), dst)


def normalized_thrust_rate(rate_N_s: float, thrust_reference_N: float) -> float:
    """Taxa de empuxo normalizada, em 1/s, com a referencia explicita no argumento.

        lambda_dot_T = Tdot / T_ref

    Existe como **derivada declarada**, para comparar arquiteturas de tamanhos
    diferentes. A grandeza fisica do deck de propulsao continua sendo `N/s`, nunca
    esta. Uma taxa normalizada sem a referencia ao lado nao e interpretavel, e por
    isso a referencia e argumento obrigatorio em vez de constante de modulo.
    """
    if not thrust_reference_N > 0.0:
        raise ValueError(f"thrust_reference_N deve ser positivo, recebeu {thrust_reference_N!r}")
    return rate_N_s / thrust_reference_N


def kind_of(unit: str) -> str:
    """Tipo semantico da grandeza, por exemplo ``'normalized_thrust_rate'``.

    Distinto de :func:`dimension_of`. Ver o docstring de :class:`UnitSpec`.
    """
    return _spec(unit).quantity_kind


def require_kind(unit: str, expected: str) -> None:
    """Falha se a unidade nao for do tipo semantico esperado.

    E isto, e nao a dimensao, que impede hertz de entrar num campo que espera taxa
    normalizada de empuxo. Os dois sao ``s^-1``.
    """
    actual = kind_of(unit)
    if actual != expected:
        raise KindError(
            f"esperava grandeza do tipo {expected!r}, recebeu {unit!r} que e {actual!r}. "
            "Dimensao pode coincidir; o tipo semantico e que governa o campo."
        )


def require_dimension(unit: str, expected: str) -> None:
    """Falha se a unidade nao for da dimensao esperada.

    E isto que impede um campo de massa receber ``N``. A falha acontece no
    carregamento da configuracao, nao no grafico.
    """
    actual = dimension_of(unit)
    if actual != expected:
        raise DimensionError(f"esperava dimensao {expected!r}, recebeu {unit!r} que e {actual!r}")
