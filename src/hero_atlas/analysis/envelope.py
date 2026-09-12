"""Envelope de massa e empuxo: o "fecha ou nao fecha" do marco 1.

Ver vault/04 - Fisica/Forca requerida x capacidade de entrega.md

    A atmosfera NAO faz o traje precisar de mais forca para equilibrar o peso.
    Ela faz os motores entregarem menos.

Quatro grandezas distintas, porque confundi-las faz alguem ler "175 kgf instalados"
como se os motores ja tivessem sido escolhidos:

    T_efetivo_requerido   forca fisica necessaria no ar
    T_efetivo_disponivel  o que o conjunto entrega naquele cenario
    T_referencia_instalado  capacidade nominal em condicao de referencia
    lambda_T              razao entre disponivel e requerido
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..environment.atmosphere import AtmosphereState, isa
from ..model_status import PROPULSAO_INSTALADA_HOJE, ModelStatus
from ..units import G0

__all__ = [
    "MassBudget",
    "InstallationLosses",
    "ThrustEnvelope",
    "thrust_effective_required_N",
    "thrust_effective_available_N",
    "reference_thrust_needed_N",
    "solve_envelope",
    "mass_closure",
    "MassClosureResult",
    "PROVISIONAL_CONTROL_RESERVE",
]

PROVISIONAL_CONTROL_RESERVE: float = 1.10
"""Marcador provisorio, nao margem fundamentada.

    T_disponivel >= T_trim + dT_perturbacao + dT_manobra + dT_falha

Substituido no marco 2 por margem calculada a partir do conjunto de forcas
atingiveis. Existe so para o marco 1 nao ficar bloqueado.
"""


@dataclass(frozen=True, slots=True)
class MassBudget:
    """Orcamento de massa, com o consumivel separado do resto.

    O consumivel e separado porque a autonomia integra sobre ele enquanto a massa
    seca fica fixa.
    """

    pilot_kg: float
    structure_kg: float
    engines_kg: float
    consumable_kg: float
    avionics_kg: float = 0.0
    harness_kg: float = 0.0

    def __post_init__(self) -> None:
        for nome in (
            "pilot_kg",
            "structure_kg",
            "engines_kg",
            "consumable_kg",
            "avionics_kg",
            "harness_kg",
        ):
            valor = getattr(self, nome)
            if not math.isfinite(valor) or valor < 0.0:
                raise ValueError(f"{nome} deve ser finito e nao negativo, recebeu {valor!r}")
        if self.dry_kg <= 0.0:
            raise ValueError("massa seca nao pode ser zero")

    @property
    def dry_kg(self) -> float:
        """Tudo menos o consumivel."""
        return (
            self.pilot_kg + self.structure_kg + self.engines_kg + self.avionics_kg + self.harness_kg
        )

    @property
    def gross_kg(self) -> float:
        return self.dry_kg + self.consumable_kg

    @property
    def weight_N(self) -> float:
        return self.gross_kg * G0

    @property
    def consumable_fraction(self) -> float:
        return self.consumable_kg / self.gross_kg


@dataclass(frozen=True, slots=True)
class InstallationLosses:
    """Perdas entre o empuxo de catalogo e o empuxo entregue ao corpo.

    ⚠ Nenhum destes fatores tem base publicada para instalacao vestivel. Eles nao
    sao errados, sao **nao fundamentados**, e por isso o resultado carrega estado de
    modelo condicional. Ver vault/02 - Decisoes/ADR-007.

    Attributes:
        installation: perda de entrada, bocal, montagem.
        interaction: pluma contra estrutura, entre unidades, dependencia de pose.
        thermal_residual: o que a razao de densidade **nao** cobre, ou seja limite
            de temperatura de entrada da turbina. Fica entre 0,95 e 0,97 em dia
            quente, e vale 1,0 na referencia.
    """

    installation: float = 1.0
    interaction: float = 1.0
    thermal_residual: float = 1.0

    def __post_init__(self) -> None:
        for nome in ("installation", "interaction", "thermal_residual"):
            valor = getattr(self, nome)
            if not 0.0 < valor <= 1.0:
                raise ValueError(f"{nome} deve estar em (0, 1], recebeu {valor!r}")

    @property
    def combined(self) -> float:
        return self.installation * self.interaction * self.thermal_residual


def thrust_effective_required_N(
    gross_kg: float,
    *,
    nozzle_tilt_rad: float,
    control_reserve: float = PROVISIONAL_CONTROL_RESERVE,
) -> float:
    """Forca fisica necessaria no ar, em newton.

        T = m*g / cos(theta) * k_reserva

    ⚠ Nao divide por eficiencia ambiental. Atmosfera nao muda o que a fisica exige,
    muda o que os motores entregam. Ver :func:`thrust_effective_available_N`.

    ⚠ O cosseno e **modelo de ordem zero**, valido enquanto todos os bocais tiverem
    a mesma inclinacao. A partir do marco 2 a fonte de verdade e ``solve_trim``, que
    resolve com direcao, posicao e limite proprios por propulsor, e com o momento do
    peso sobre o ponto de referencia.
    """
    if not 0.0 <= nozzle_tilt_rad < math.pi / 2:
        raise ValueError(f"inclinacao {nozzle_tilt_rad} rad fora de [0, pi/2)")
    if control_reserve < 1.0:
        raise ValueError(f"reserva de controle abaixo de 1,0: {control_reserve!r}")
    return gross_kg * G0 / math.cos(nozzle_tilt_rad) * control_reserve


def thrust_effective_available_N(
    reference_thrust_N: float,
    *,
    atmosphere: AtmosphereState,
    losses: InstallationLosses,
    lapse_exponent: float = 1.0,
) -> float:
    """O que o conjunto entrega naquele cenario.

        T = T_ref * (rho/rho0)^n * eta_instalacao * eta_interacao * eta_termico

    O expoente da razao de densidade e 1,0 para turbojato estatico em primeira
    aproximacao. Vira parametro do deck quando o deck existir.
    """
    return reference_thrust_N * atmosphere.density_ratio**lapse_exponent * losses.combined


def reference_thrust_needed_N(
    required_N: float,
    *,
    atmosphere: AtmosphereState,
    losses: InstallationLosses,
    lapse_exponent: float = 1.0,
) -> float:
    """Quanto instalar em condicao de referencia para atender o requisito no cenario.

    Esta e a pergunta de dimensionamento, e e por isso que o fator ambiental aparece
    dividindo **aqui** e nao no requisito.
    """
    eta = atmosphere.density_ratio**lapse_exponent * losses.combined
    return required_N / eta


@dataclass(frozen=True, slots=True)
class ThrustEnvelope:
    """Resultado do envelope, com as quatro grandezas separadas."""

    mass: MassBudget
    atmosphere: AtmosphereState
    losses: InstallationLosses
    nozzle_tilt_rad: float
    control_reserve: float
    thrust_effective_required_N: float
    thrust_effective_available_N: float
    reference_thrust_installed_N: float
    reference_thrust_needed_N: float
    status: ModelStatus = field(default=PROPULSAO_INSTALADA_HOJE)

    @property
    def thrust_margin_ratio(self) -> float:
        """lambda_T. Abaixo de 1,0 o traje nao sustenta o proprio peso no cenario."""
        return self.thrust_effective_available_N / self.thrust_effective_required_N

    @property
    def closes(self) -> bool:
        return self.thrust_margin_ratio >= 1.0

    @property
    def thrust_to_weight_gross(self) -> float:
        """T/W bruto, sem o cosseno. E o numero que catalogos e imprensa citam."""
        return self.thrust_effective_available_N / self.mass.weight_N

    @property
    def thrust_to_weight_effective(self) -> float:
        """T/W depois do cosseno, que e o que o piloto realmente tem na vertical."""
        return self.thrust_to_weight_gross * math.cos(self.nozzle_tilt_rad)


def solve_envelope(
    mass: MassBudget,
    *,
    reference_thrust_installed_N: float,
    nozzle_tilt_rad: float,
    atmosphere: AtmosphereState | None = None,
    losses: InstallationLosses | None = None,
    control_reserve: float = PROVISIONAL_CONTROL_RESERVE,
    lapse_exponent: float = 1.0,
    status: ModelStatus = PROPULSAO_INSTALADA_HOJE,
) -> ThrustEnvelope:
    """Resolve o envelope inteiro para um veiculo num cenario."""
    atm = atmosphere if atmosphere is not None else isa()
    loss = losses if losses is not None else InstallationLosses()

    required = thrust_effective_required_N(
        mass.gross_kg, nozzle_tilt_rad=nozzle_tilt_rad, control_reserve=control_reserve
    )
    available = thrust_effective_available_N(
        reference_thrust_installed_N,
        atmosphere=atm,
        losses=loss,
        lapse_exponent=lapse_exponent,
    )
    needed = reference_thrust_needed_N(
        required, atmosphere=atm, losses=loss, lapse_exponent=lapse_exponent
    )

    return ThrustEnvelope(
        mass=mass,
        atmosphere=atm,
        losses=loss,
        nozzle_tilt_rad=nozzle_tilt_rad,
        control_reserve=control_reserve,
        thrust_effective_required_N=required,
        thrust_effective_available_N=available,
        reference_thrust_installed_N=reference_thrust_installed_N,
        reference_thrust_needed_N=needed,
        status=status,
    )


@dataclass(frozen=True, slots=True)
class MassClosureResult:
    """Resultado do laco de fechamento de massa."""

    converged: bool
    iterations: int
    gross_kg: float
    growth_factor: float
    history: tuple[float, ...]

    @property
    def is_fragile(self) -> bool:
        """Fator de crescimento acima de 4 indica conceito fragil.

        E a derivada da massa bruta em relacao a carga paga: quanto de massa total
        cada quilo de piloto arrasta consigo.
        """
        return self.growth_factor > 4.0


def mass_closure(
    *,
    pilot_kg: float,
    fixed_kg: float,
    structure_fraction: float,
    engine_kg_per_N: float,
    consumable_kg_per_N: float,
    nozzle_tilt_rad: float,
    control_reserve: float = PROVISIONAL_CONTROL_RESERVE,
    tolerance_kg: float = 1e-3,
    max_iterations: int = 200,
) -> MassClosureResult:
    """Laco de ponto fixo: motor e combustivel dependem do empuxo, que depende da massa.

        m_{k+1} = m_piloto + m_fixo + f_estrutura*m_k + (c_motor + c_consumivel)*T(m_k)

    Convergir significa que o conceito fecha. Divergir significa que cada quilo
    adicionado exige mais empuxo do que ele proprio paga, que e a fronteira de
    inviabilidade.
    """
    if not 0.0 <= structure_fraction < 1.0:
        raise ValueError(f"fracao estrutural fora de [0, 1): {structure_fraction!r}")

    massa = pilot_kg + fixed_kg
    historico = [massa]

    for iteracao in range(1, max_iterations + 1):
        empuxo = thrust_effective_required_N(
            massa, nozzle_tilt_rad=nozzle_tilt_rad, control_reserve=control_reserve
        )
        nova = (
            pilot_kg
            + fixed_kg
            + structure_fraction * massa
            + (engine_kg_per_N + consumable_kg_per_N) * empuxo
        )
        historico.append(nova)

        if not math.isfinite(nova) or nova > 1e6:
            return MassClosureResult(
                converged=False,
                iterations=iteracao,
                gross_kg=float("inf"),
                growth_factor=float("inf"),
                history=tuple(historico),
            )

        if abs(nova - massa) < tolerance_kg:
            return MassClosureResult(
                converged=True,
                iterations=iteracao,
                gross_kg=nova,
                growth_factor=nova / pilot_kg,
                history=tuple(historico),
            )
        massa = nova

    return MassClosureResult(
        converged=False,
        iterations=max_iterations,
        gross_kg=massa,
        growth_factor=massa / pilot_kg,
        history=tuple(historico),
    )
