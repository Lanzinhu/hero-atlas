"""Atuador de empuxo: atraso de transporte, constante de tempo, rampa e saturacao.

Ver ADR-003, ADR-005 e ADR-007.

Este e o modulo em torno do qual o projeto inteiro gira. A cadeia e

    u(t)  ->  u(t - T_d)  ->  T_ss saturado  ->  T(t) por equacao diferencial  ->  F(t)

e nenhuma dessas setas e identidade. O alocador **nao** promete empuxo instantaneo;
a equacao diferencial aqui e a unica autoridade sobre ``T_real(t)``.

A lei, conforme ADR-005::

    e     = T_ss - T
    tau   = tau_subida se e > 0, senao tau_descida
    Tdot  = clip( e / tau , -Tdot_descida_max , +Tdot_subida_max )

com ``T`` projetado em ``[T_min, T_max]`` em excesso numerico pequeno, e ativacao de
limite **registrada como telemetria**, nao tratada como guarda.

⚠ **A incognita central do projeto mora aqui.** O catalogo de microturbina publica
resposta a degrau **grande**, de 1 a 3 segundos entre marcha lenta e maximo. O que
decide estabilizacao e a resposta a degrau **pequeno** perto do trim, que nenhum
fabricante publica. Extrapolar a constante de tempo de degrau grande para degrau
pequeno e uma hipotese sem base, e por isso :func:`small_step_response_time_s`
**recusa** calcular quando o envelope nao declara o valor de pequeno sinal. Ver
:class:`UnknownSmallStepDynamicsError`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

__all__ = [
    "ActuatorLimit",
    "ActuatorEnvelope",
    "ActuatorResponse",
    "UnknownSmallStepDynamicsError",
    "CommandDelayLine",
    "thrust_rate_N_s",
    "project_thrust_N",
    "step_response_time_s",
    "small_step_response_time_s",
    "SMALL_STEP_FRACTION_DEFAULT",
]

SMALL_STEP_FRACTION_DEFAULT: float = 0.05
"""Fracao de ``T_max`` abaixo da qual um degrau conta como pequeno.

Cinco por cento e a ordem de grandeza de uma correcao de atitude em pairado, nao um
valor medido. Entra como parametro de sensibilidade, nunca como constante fisica.
"""


class ActuatorLimit(StrEnum):
    """Qual limite esta ativo neste instante. Telemetria, nao guarda."""

    NONE = "none"
    RATE_UP = "rate_up"
    RATE_DOWN = "rate_down"
    COMMAND_ABOVE_MAX = "command_above_max"
    COMMAND_BELOW_IDLE = "command_below_idle"
    THRUST_FLOOR = "thrust_floor"
    THRUST_CEILING = "thrust_ceiling"


class UnknownSmallStepDynamicsError(RuntimeError):
    """Pediu resposta de degrau pequeno sem o envelope declarar dinamica de pequeno sinal.

    Nao e falta de implementacao: e falta de **dado**. Nenhum fabricante de
    microturbina publica constante de tempo perto do ponto de operacao, e usar a de
    degrau grande no lugar produziria um numero plausivel e sem base, exatamente o
    tipo de erro que este projeto existe para nao cometer.
    """


@dataclass(frozen=True, slots=True)
class ActuatorEnvelope:
    """Os sete parametros de dinamica de empuxo, mais a dinamica de pequeno sinal.

    Conforme ADR-007, o deck declara **envelope de dinamica**, nao um atraso escalar::

        Theta = [ T_d , tau_subida , tau_descida , Tdot_up_max , Tdot_down_max ,
                  T_min , T_max ]

    Attributes:
        thrust_min_N: marcha lenta. O empuxo nao vai a zero num motor em operacao.
        thrust_max_N: teto fisico.
        tau_up_s: constante de tempo subindo, para degrau **grande**.
        tau_down_s: constante de tempo descendo, para degrau **grande**. Costuma
            diferir da de subida, e tratar as duas como iguais e hipotese, nao
            simplificacao inocente.
        rate_up_max_N_s: rampa maxima de subida.
        rate_down_max_N_s: rampa maxima de descida, valor positivo.
        transport_delay_s: atraso puro de transporte, antes de qualquer resposta.
        tau_small_step_up_s: constante de tempo subindo para degrau **pequeno**.
            ``None`` significa **desconhecido**, que e o estado real da evidencia
            para microturbina. Nao e o mesmo que igual ao de degrau grande.
        tau_small_step_down_s: idem, descendo.
        small_step_fraction: o que conta como degrau pequeno, em fracao de
            ``thrust_max_N``.
    """

    thrust_min_N: float
    thrust_max_N: float
    tau_up_s: float
    tau_down_s: float
    rate_up_max_N_s: float
    rate_down_max_N_s: float
    transport_delay_s: float = 0.0
    tau_small_step_up_s: float | None = None
    tau_small_step_down_s: float | None = None
    small_step_fraction: float = SMALL_STEP_FRACTION_DEFAULT

    def __post_init__(self) -> None:
        if not 0.0 <= self.thrust_min_N < self.thrust_max_N:
            raise ValueError(
                f"faixa de empuxo invalida: [{self.thrust_min_N}, {self.thrust_max_N}]"
            )
        for nome in ("tau_up_s", "tau_down_s"):
            valor = getattr(self, nome)
            if not math.isfinite(valor) or valor <= 0.0:
                raise ValueError(f"{nome} precisa ser positivo e finito, recebeu {valor!r}")
        for nome in ("rate_up_max_N_s", "rate_down_max_N_s"):
            valor = getattr(self, nome)
            if not math.isfinite(valor) or valor <= 0.0:
                raise ValueError(
                    f"{nome} precisa ser positivo e finito, recebeu {valor!r}. "
                    "Rampa infinita nao e 'sem limite': e afirmacao fisica falsa."
                )
        if not math.isfinite(self.transport_delay_s) or self.transport_delay_s < 0.0:
            raise ValueError("transport_delay_s precisa ser finito e nao negativo")
        for nome in ("tau_small_step_up_s", "tau_small_step_down_s"):
            valor = getattr(self, nome)
            if valor is not None and (not math.isfinite(valor) or valor <= 0.0):
                raise ValueError(f"{nome}, quando declarado, precisa ser positivo e finito")
        if not 0.0 < self.small_step_fraction <= 1.0:
            raise ValueError("small_step_fraction em (0, 1]")

    @property
    def thrust_span_N(self) -> float:
        return self.thrust_max_N - self.thrust_min_N

    @property
    def small_step_N(self) -> float:
        """Amplitude que separa degrau pequeno de degrau grande."""
        return self.small_step_fraction * self.thrust_max_N

    @property
    def declares_small_step_dynamics(self) -> bool:
        """Se o envelope tem dinamica de pequeno sinal declarada, nas duas direcoes."""
        return self.tau_small_step_up_s is not None and self.tau_small_step_down_s is not None

    @property
    def full_range_slew_time_s(self) -> float:
        """Tempo so de rampa para atravessar a faixa inteira subindo.

        Cota inferior do tempo de resposta a degrau grande: ignora constante de tempo
        e atraso de transporte, entao o valor real e sempre maior.
        """
        return self.thrust_span_N / self.rate_up_max_N_s

    def is_rate_limited_for(self, error_N: float) -> bool:
        """Se um erro de empuxo deste tamanho satura a rampa em vez da constante de tempo.

        O cruzamento esta em ``|e| = Tdot_max * tau``: acima disso manda a rampa,
        abaixo manda a exponencial. Saber de qual lado se esta muda qual parametro
        vale a pena medir.
        """
        if error_N >= 0.0:
            return error_N > self.rate_up_max_N_s * self.tau_up_s
        return -error_N > self.rate_down_max_N_s * self.tau_down_s


@dataclass(frozen=True, slots=True)
class ActuatorResponse:
    """Derivada de empuxo e qual limite a produziu."""

    rate_N_s: float
    limits: tuple[ActuatorLimit, ...]
    steady_state_N: float

    @property
    def limited(self) -> bool:
        return bool(self.limits)


def thrust_rate_N_s(
    *,
    thrust_N: float,
    commanded_N: float,
    envelope: ActuatorEnvelope,
) -> ActuatorResponse:
    """Derivada do empuxo, com saturacao de comando e corte de rampa.

    ⚠ ``commanded_N`` ja deve vir **atrasado** pela linha de transporte. Este modulo
    nao aplica ``transport_delay_s`` aqui, porque atraso e estado com historico e nao
    cabe numa funcao sem memoria. Ver :class:`CommandDelayLine`.

    O empuxo atual pode estar fora da faixa por excesso numerico do integrador. Nesse
    caso a derivada empurra de volta para dentro e o limite e registrado, em vez de
    disparar evento: conforme ADR-005, saturacao e telemetria no produto minimo.
    """
    limites: list[ActuatorLimit] = []

    estacionario = commanded_N
    if estacionario > envelope.thrust_max_N:
        estacionario = envelope.thrust_max_N
        limites.append(ActuatorLimit.COMMAND_ABOVE_MAX)
    elif estacionario < envelope.thrust_min_N:
        estacionario = envelope.thrust_min_N
        limites.append(ActuatorLimit.COMMAND_BELOW_IDLE)

    erro = estacionario - thrust_N
    tau = envelope.tau_up_s if erro >= 0.0 else envelope.tau_down_s
    taxa = erro / tau

    if taxa > envelope.rate_up_max_N_s:
        taxa = envelope.rate_up_max_N_s
        limites.append(ActuatorLimit.RATE_UP)
    elif taxa < -envelope.rate_down_max_N_s:
        taxa = -envelope.rate_down_max_N_s
        limites.append(ActuatorLimit.RATE_DOWN)

    return ActuatorResponse(rate_N_s=taxa, limits=tuple(limites), steady_state_N=estacionario)


def project_thrust_N(thrust_N: float, envelope: ActuatorEnvelope) -> tuple[float, ActuatorLimit]:
    """Projeta o empuxo de volta na faixa fisica, e diz se precisou.

    Conforme ADR-005, excesso numerico pequeno do integrador e **projetado com
    registro**, nao tratado como guarda: guarda na fronteira dispara repetidamente e
    nao ha evento fisico acontecendo.

    ⚠ Esta funcao existe separada de :func:`thrust_rate_N_s` porque a projecao age
    sobre o **estado**, depois do passo, e nao sobre a derivada. Uma versao anterior
    tentava fazer as duas coisas na mesma funcao, com dois ramos que a saturacao de
    comando tornava **inalcancaveis**: como ``T_ss`` ja e forcado para dentro de
    ``[T_min, T_max]``, um empuxo abaixo do piso sempre tem erro positivo e ja sobe
    sozinho. Codigo morto que aparenta ser protecao e pior que protecao ausente.
    """
    if thrust_N < envelope.thrust_min_N:
        return envelope.thrust_min_N, ActuatorLimit.THRUST_FLOOR
    if thrust_N > envelope.thrust_max_N:
        return envelope.thrust_max_N, ActuatorLimit.THRUST_CEILING
    return thrust_N, ActuatorLimit.NONE


def step_response_time_s(
    *,
    initial_N: float,
    commanded_N: float,
    envelope: ActuatorEnvelope,
    fraction: float = 0.90,
    tau_up_s: float | None = None,
    tau_down_s: float | None = None,
) -> float:
    """Tempo ate atingir ``fraction`` de um degrau, em forma fechada.

    Resolve exatamente a mesma lei de :func:`thrust_rate_N_s`, com duas fases:
    rampa constante enquanto o erro e grande, exponencial depois. O cruzamento esta
    em ``|e| = Tdot_max * tau``.

    Sendo ``D`` a amplitude do degrau, ``R`` a rampa, ``tau`` a constante de tempo,
    ``e_f = (1 - fraction) * D`` o erro restante no alvo e ``e_c = R * tau``::

        D <= e_c          ->  t = -tau * ln(1 - fraction)
        e_f >= e_c        ->  t = fraction * D / R
        caso contrario    ->  t = (D - e_c)/R + tau * ln(e_c / e_f)

    e soma-se ``transport_delay_s`` em todos os casos.

    Args:
        fraction: fracao do degrau. ``0.90`` e a convencao de catalogo; ``0.632``
            recupera a constante de tempo quando nao ha rampa ativa.
        tau_up_s: sobrepoe a constante de tempo de subida, para avaliar o mesmo
            envelope com dinamica de pequeno sinal. Ver
            :func:`small_step_response_time_s`.
    """
    if not 0.0 < fraction < 1.0:
        raise ValueError("fraction precisa estar em (0, 1)")

    amplitude = commanded_N - initial_N
    if amplitude == 0.0:
        return envelope.transport_delay_s

    subindo = amplitude > 0.0
    modulo = abs(amplitude)
    if subindo:
        tau = envelope.tau_up_s if tau_up_s is None else tau_up_s
        rampa = envelope.rate_up_max_N_s
    else:
        tau = envelope.tau_down_s if tau_down_s is None else tau_down_s
        rampa = envelope.rate_down_max_N_s

    erro_alvo = (1.0 - fraction) * modulo
    erro_cruzamento = rampa * tau

    if modulo <= erro_cruzamento:
        tempo = -tau * math.log(1.0 - fraction)
    elif erro_alvo >= erro_cruzamento:
        tempo = fraction * modulo / rampa
    else:
        tempo = (modulo - erro_cruzamento) / rampa + tau * math.log(erro_cruzamento / erro_alvo)

    return tempo + envelope.transport_delay_s


def small_step_response_time_s(
    *,
    thrust_N: float,
    envelope: ActuatorEnvelope,
    step_N: float | None = None,
    fraction: float = 0.90,
) -> float:
    """Tempo de resposta a degrau **pequeno** em torno do ponto de operacao.

    Este e o numero que decide se a arquitetura estabiliza, e e o numero que ninguem
    publica.

    Raises:
        UnknownSmallStepDynamicsError: se o envelope nao declarar
            ``tau_small_step_up_s`` e ``tau_small_step_down_s``. A recusa e
            deliberada: substituir pela constante de degrau grande daria um numero
            com aparencia de resultado e nenhuma evidencia por tras.
    """
    if not envelope.declares_small_step_dynamics:
        raise UnknownSmallStepDynamicsError(
            "envelope sem dinamica de pequeno sinal declarada. O catalogo de "
            "microturbina publica degrau grande, de marcha lenta a maximo, e a "
            "constante perto do ponto de operacao nao segue dele. Declare "
            "'tau_small_step_up_s' e 'tau_small_step_down_s' como hipotese de "
            "sensibilidade, com procedencia, ou trate o resultado como indeterminado."
        )

    amplitude = envelope.small_step_N if step_N is None else abs(step_N)
    return step_response_time_s(
        initial_N=thrust_N,
        commanded_N=thrust_N + amplitude,
        envelope=envelope,
        fraction=fraction,
        tau_up_s=envelope.tau_small_step_up_s,
        tau_down_s=envelope.tau_small_step_down_s,
    )


@dataclass(slots=True)
class CommandDelayLine:
    """Historico de comando com consulta atrasada, causal por construcao.

    O atraso de transporte e estado com memoria, nao ganho. Esta classe guarda o que
    foi comandado e devolve o que o motor esta vendo agora.

    ⚠ **Causalidade e verificada, nao presumida.** :meth:`value_at` recusa consultar
    instante posterior a ``now``, porque isso seria usar comando ainda nao emitido.
    Num integrador de Runge-Kutta o estagio intermediario cai em ``t + dt/2``, e sem
    essa checagem o erro passa silencioso e a trajetoria fica suave e errada.

    ⚠ Conforme o plano, atraso continuo menor que o passo maximo e **proibido**:
    interpolar um atraso mais curto que o proprio passo nao tem informacao para se
    sustentar. Use :meth:`validate_against_step` no inicio da simulacao.
    """

    initial_value: float
    times_s: list[float] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    interpolation_order: int = 3

    def __post_init__(self) -> None:
        if self.interpolation_order not in (1, 3):
            raise ValueError("ordem de interpolacao suportada: 1 (linear) ou 3 (cubica)")

    def push(self, time_s: float, value: float) -> None:
        """Registra um comando emitido. Os instantes precisam ser nao decrescentes."""
        if self.times_s and time_s < self.times_s[-1]:
            raise ValueError(
                f"comando fora de ordem: {time_s} depois de {self.times_s[-1]}. "
                "O historico e causal e nao aceita reescrita do passado."
            )
        if self.times_s and time_s == self.times_s[-1]:
            self.values[-1] = value
            return
        self.times_s.append(time_s)
        self.values.append(value)

    def validate_against_step(self, *, delay_s: float, max_step_s: float) -> None:
        """Recusa atraso continuo menor que o passo maximo de integracao."""
        if delay_s <= 0.0:
            return
        if delay_s < max_step_s:
            raise ValueError(
                f"atraso continuo de {delay_s} s menor que o passo maximo de "
                f"{max_step_s} s. O historico nao tem amostras suficientes entre os "
                "dois instantes para sustentar a interpolacao. Reduza o passo ou "
                "modele o atraso como retencao de ordem zero."
            )

    def value_at(self, query_s: float, *, now_s: float) -> float:
        """Comando vigente no instante ``query_s``, visto de ``now_s``.

        Antes do inicio do historico devolve :attr:`initial_value`, que e a retencao
        declarada e nao uma extrapolacao.
        """
        if query_s > now_s + 1e-12:
            raise ValueError(
                f"consulta causal violada: pediu {query_s} s estando em {now_s} s. "
                "Comando futuro nao existe."
            )
        if not self.times_s:
            return self.initial_value

        tempos = np.asarray(self.times_s, dtype=np.float64)
        valores = np.asarray(self.values, dtype=np.float64)

        visiveis = int(np.searchsorted(tempos, now_s + 1e-12, side="right"))
        if visiveis == 0:
            return self.initial_value
        tempos = tempos[:visiveis]
        valores = valores[:visiveis]

        if query_s <= tempos[0]:
            return self.initial_value
        if query_s >= tempos[-1]:
            return float(valores[-1])

        indice = int(np.searchsorted(tempos, query_s, side="right"))
        if self.interpolation_order == 1 or tempos.size < 4:
            t0, t1 = tempos[indice - 1], tempos[indice]
            v0, v1 = valores[indice - 1], valores[indice]
            if t1 == t0:
                return float(v1)
            return float(v0 + (v1 - v0) * (query_s - t0) / (t1 - t0))

        inicio = max(0, min(indice - 2, tempos.size - 4))
        return float(_lagrange(tempos[inicio : inicio + 4], valores[inicio : inicio + 4], query_s))

    def delayed_value(self, *, now_s: float, delay_s: float) -> float:
        """Atalho para ``value_at(now_s - delay_s, now_s=now_s)``."""
        return self.value_at(now_s - delay_s, now_s=now_s)

    def trim(self, *, before_s: float) -> None:
        """Descarta historico anterior a ``before_s``, mantendo margem de interpolacao."""
        if len(self.times_s) <= 4:
            return
        corte = int(np.searchsorted(np.asarray(self.times_s), before_s, side="right")) - 4
        if corte > 0:
            del self.times_s[:corte]
            del self.values[:corte]


def _lagrange(nodes: NDArray[np.float64], values: NDArray[np.float64], x: float) -> float:
    """Interpolacao de Lagrange sobre quatro nos. Suficiente e sem dependencia nova."""
    total = 0.0
    for i in range(nodes.size):
        termo = values[i]
        for j in range(nodes.size):
            if i != j:
                termo *= (x - nodes[j]) / (nodes[i] - nodes[j])
        total += termo
    return float(total)
