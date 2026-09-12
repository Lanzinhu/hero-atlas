"""Marco 3: atuador de empuxo com atraso, constante de tempo, rampa e saturacao.

Ver vault/02 - Decisoes/ADR-005 - Saturacao e rampa sao telemetria.md

Este arquivo carrega o teste mais importante do modulo: a forma fechada de
:func:`step_response_time_s` e conferida contra a **integracao numerica da propria
lei** de :func:`thrust_rate_N_s`. Se as duas divergirem, uma das duas esta errada, e
um envelope de atraso errado contamina toda conclusao sobre estabilidade.

O segundo grupo verifica a recusa de pequeno sinal. Nao e teste de implementacao: e
teste de que o codigo **nao inventa** o numero que ninguem publica.
"""

from __future__ import annotations

import math

import pytest

from hero_atlas.propulsion.actuator import (
    ActuatorEnvelope,
    ActuatorLimit,
    CommandDelayLine,
    UnknownSmallStepDynamicsError,
    project_thrust_N,
    small_step_response_time_s,
    step_response_time_s,
    thrust_rate_N_s,
)

pytestmark = pytest.mark.validation


def envelope(**alteracoes: object) -> ActuatorEnvelope:
    """Envelope de referencia, com a faixa de uma microturbina de classe 35 kgf.

    ⚠ Os valores sao **plausiveis, nao medidos**. A faixa de empuxo vem da classe
    escolhida na varredura de geometria; constantes de tempo e rampas sao hipoteses
    de trabalho que existem para exercitar a lei, nunca para representar hardware.
    """
    base: dict[str, object] = dict(
        thrust_min_N=34.0,
        thrust_max_N=343.0,
        tau_up_s=0.35,
        tau_down_s=0.30,
        rate_up_max_N_s=120.0,
        rate_down_max_N_s=150.0,
    )
    base.update(alteracoes)
    return ActuatorEnvelope(**base)  # type: ignore[arg-type]


def integra_ate_fracao(
    env: ActuatorEnvelope,
    inicial_N: float,
    comandado_N: float,
    fracao: float,
    dt: float = 1e-5,
    t_max: float = 60.0,
) -> float:
    """Integra a lei de :func:`thrust_rate_N_s` ate cruzar a fracao do degrau.

    Euler explicito com passo pequeno, deliberadamente ingenuo: o objetivo e nao
    compartilhar nenhuma algebra com a forma fechada que esta sendo verificada.
    """
    alvo = inicial_N + fracao * (comandado_N - inicial_N)
    subindo = comandado_N > inicial_N
    t, empuxo = 0.0, inicial_N
    for _ in range(int(t_max / dt)):
        taxa = thrust_rate_N_s(thrust_N=empuxo, commanded_N=comandado_N, envelope=env).rate_N_s
        proximo = empuxo + dt * taxa
        if (subindo and proximo >= alvo) or (not subindo and proximo <= alvo):
            return t + dt * (alvo - empuxo) / (proximo - empuxo)
        empuxo, t = proximo, t + dt
    return math.inf


# ---------------------------------------------------------------------------
# A verificacao central: forma fechada contra integracao da propria lei
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("nome", "inicial", "comandado", "fracao"),
    [
        ("degrau grande subindo, rampa domina", 34.0, 343.0, 0.90),
        ("degrau pequeno subindo, exponencial domina", 170.0, 187.0, 0.90),
        ("degrau medio, as duas fases", 100.0, 250.0, 0.90),
        ("degrau grande descendo", 343.0, 34.0, 0.90),
        ("degrau pequeno descendo", 190.0, 173.0, 0.90),
        ("fracao de constante de tempo", 170.0, 180.0, 0.632),
        ("fracao alta", 120.0, 300.0, 0.99),
    ],
)
def test_forma_fechada_bate_com_integracao_numerica(
    nome: str, inicial: float, comandado: float, fracao: float
) -> None:
    env = envelope()
    fechada = step_response_time_s(
        initial_N=inicial, commanded_N=comandado, envelope=env, fraction=fracao
    )
    numerica = integra_ate_fracao(env, inicial, comandado, fracao)
    assert fechada == pytest.approx(numerica, rel=2e-4), nome


def test_rampa_folgada_recupera_a_exponencial_pura() -> None:
    """Com rampa enorme, o tempo vira ``-tau*ln(1-f)`` exatamente."""
    env = envelope(rate_up_max_N_s=1e9, rate_down_max_N_s=1e9)
    t = step_response_time_s(initial_N=50.0, commanded_N=300.0, envelope=env, fraction=0.632)
    assert t == pytest.approx(-0.35 * math.log(1 - 0.632), rel=1e-12)


def test_rampa_apertada_recupera_a_rampa_pura() -> None:
    """Com constante de tempo minuscula, o tempo vira ``f*D/R`` exatamente."""
    env = envelope(tau_up_s=1e-9)
    t = step_response_time_s(initial_N=34.0, commanded_N=343.0, envelope=env, fraction=0.90)
    assert t == pytest.approx(0.90 * (343.0 - 34.0) / 120.0, rel=1e-6)


def test_atraso_de_transporte_soma_e_nao_multiplica() -> None:
    sem = step_response_time_s(initial_N=100.0, commanded_N=250.0, envelope=envelope())
    com = step_response_time_s(
        initial_N=100.0, commanded_N=250.0, envelope=envelope(transport_delay_s=0.08)
    )
    assert com - sem == pytest.approx(0.08, abs=1e-12)


def test_degrau_nulo_devolve_so_o_atraso() -> None:
    t = step_response_time_s(
        initial_N=200.0, commanded_N=200.0, envelope=envelope(transport_delay_s=0.08)
    )
    assert t == pytest.approx(0.08)


def test_subida_e_descida_usam_constantes_diferentes() -> None:
    """Assimetria nao e detalhe: subir e descer sao processos fisicos distintos."""
    env = envelope(rate_up_max_N_s=1e9, rate_down_max_N_s=1e9)
    sobe = step_response_time_s(initial_N=170.0, commanded_N=180.0, envelope=env, fraction=0.632)
    desce = step_response_time_s(initial_N=180.0, commanded_N=170.0, envelope=env, fraction=0.632)
    assert sobe == pytest.approx(0.35 * -math.log(1 - 0.632), rel=1e-12)
    assert desce == pytest.approx(0.30 * -math.log(1 - 0.632), rel=1e-12)
    assert sobe > desce


# ---------------------------------------------------------------------------
# Saturacao e rampa como telemetria, conforme ADR-005
# ---------------------------------------------------------------------------


def test_comando_acima_do_maximo_satura_e_registra() -> None:
    r = thrust_rate_N_s(thrust_N=200.0, commanded_N=500.0, envelope=envelope())
    assert r.steady_state_N == pytest.approx(343.0)
    assert ActuatorLimit.COMMAND_ABOVE_MAX in r.limits


def test_comando_abaixo_da_marcha_lenta_satura_e_registra() -> None:
    r = thrust_rate_N_s(thrust_N=200.0, commanded_N=0.0, envelope=envelope())
    assert r.steady_state_N == pytest.approx(34.0)
    assert ActuatorLimit.COMMAND_BELOW_IDLE in r.limits


def test_rampa_de_subida_corta_e_registra() -> None:
    r = thrust_rate_N_s(thrust_N=34.0, commanded_N=343.0, envelope=envelope())
    assert r.rate_N_s == pytest.approx(120.0)
    assert ActuatorLimit.RATE_UP in r.limits


def test_rampa_de_descida_corta_e_registra() -> None:
    r = thrust_rate_N_s(thrust_N=343.0, commanded_N=34.0, envelope=envelope())
    assert r.rate_N_s == pytest.approx(-150.0)
    assert ActuatorLimit.RATE_DOWN in r.limits


def test_degrau_pequeno_nao_ativa_limite_nenhum() -> None:
    r = thrust_rate_N_s(thrust_N=170.0, commanded_N=175.0, envelope=envelope())
    assert r.limits == ()
    assert r.rate_N_s == pytest.approx(5.0 / 0.35)


def test_empuxo_abaixo_do_piso_sempre_sobe_sozinho() -> None:
    """A saturacao de comando ja garante o retorno: nao existe ramo de piso na taxa.

    Como ``T_ss`` e forcado para dentro de ``[T_min, T_max]``, um empuxo abaixo do
    piso tem erro positivo qualquer que seja o comando, entao a derivada ja aponta
    para dentro. Este teste existe para impedir que alguem "conserte" isso
    reintroduzindo um ramo inalcancavel na derivada.
    """
    for comando in (0.0, 34.0, 200.0):
        r = thrust_rate_N_s(thrust_N=33.0, commanded_N=comando, envelope=envelope())
        assert r.rate_N_s > 0.0, f"comando {comando} deveria empurrar para cima"


def test_projecao_de_estado_age_depois_do_passo() -> None:
    """A projecao age sobre o estado, com registro, conforme ADR-005."""
    env = envelope()
    valor, limite = project_thrust_N(33.0, env)
    assert valor == pytest.approx(env.thrust_min_N)
    assert limite is ActuatorLimit.THRUST_FLOOR

    valor, limite = project_thrust_N(400.0, env)
    assert valor == pytest.approx(env.thrust_max_N)
    assert limite is ActuatorLimit.THRUST_CEILING

    valor, limite = project_thrust_N(200.0, env)
    assert valor == pytest.approx(200.0)
    assert limite is ActuatorLimit.NONE


def test_cruzamento_entre_rampa_e_exponencial() -> None:
    """O limite de rampa manda exatamente enquanto ``|e| > Tdot_max * tau``."""
    env = envelope()
    cruzamento = env.rate_up_max_N_s * env.tau_up_s
    assert env.is_rate_limited_for(cruzamento * 1.01)
    assert not env.is_rate_limited_for(cruzamento * 0.99)
    assert env.is_rate_limited_for(-env.rate_down_max_N_s * env.tau_down_s * 1.01)


def test_tempo_de_varredura_de_faixa_e_cota_inferior() -> None:
    env = envelope()
    so_rampa = env.full_range_slew_time_s
    real = step_response_time_s(
        initial_N=env.thrust_min_N, commanded_N=env.thrust_max_N, envelope=env, fraction=0.99
    )
    assert so_rampa < real


# ---------------------------------------------------------------------------
# A recusa: o numero que ninguem publica nao pode ser inventado
# ---------------------------------------------------------------------------


def test_pequeno_sinal_sem_dado_declarado_e_recusado() -> None:
    with pytest.raises(UnknownSmallStepDynamicsError, match="pequeno sinal"):
        small_step_response_time_s(thrust_N=170.0, envelope=envelope())


def test_pequeno_sinal_parcialmente_declarado_ainda_e_recusado() -> None:
    """Declarar so uma das direcoes nao libera: subida e descida sao independentes."""
    with pytest.raises(UnknownSmallStepDynamicsError):
        small_step_response_time_s(thrust_N=170.0, envelope=envelope(tau_small_step_up_s=0.9))


def test_pequeno_sinal_declarado_usa_a_constante_declarada() -> None:
    env = envelope(tau_small_step_up_s=0.9, tau_small_step_down_s=0.8)
    t = small_step_response_time_s(thrust_N=170.0, envelope=env, fraction=0.632)
    assert t == pytest.approx(-0.9 * math.log(1 - 0.632), rel=1e-12)


def test_incognita_de_pequeno_sinal_domina_a_resposta() -> None:
    """O achado que justifica o projeto, em forma de teste.

    Com a constante de pequeno sinal variando dentro de uma faixa plausivel, o tempo
    de resposta a uma correcao de atitude muda por um fator maior que dois. Nenhum
    outro parametro do envelope tem essa alavanca perto do trim, e e exatamente esse
    o parametro que o catalogo nao traz.
    """
    tempos = [
        small_step_response_time_s(
            thrust_N=170.0,
            envelope=envelope(tau_small_step_up_s=tau, tau_small_step_down_s=tau),
        )
        for tau in (0.35, 0.60, 0.90, 1.50)
    ]
    assert tempos == sorted(tempos)
    assert tempos[-1] / tempos[0] > 2.0


# ---------------------------------------------------------------------------
# Linha de atraso: causalidade verificada, nao presumida
# ---------------------------------------------------------------------------


def linha_senoidal(freq_Hz: float = 1.5, dt: float = 0.002, n: int = 400) -> CommandDelayLine:
    linha = CommandDelayLine(initial_value=170.0)
    for k in range(n):
        t = k * dt
        linha.push(t, 170.0 + 30.0 * math.sin(2 * math.pi * freq_Hz * t))
    return linha


def test_interpolacao_cubica_recupera_sinal_suave() -> None:
    linha = linha_senoidal()
    agora, atraso = 0.798, 0.05
    obtido = linha.delayed_value(now_s=agora, delay_s=atraso)
    esperado = 170.0 + 30.0 * math.sin(2 * math.pi * 1.5 * (agora - atraso))
    assert obtido == pytest.approx(esperado, abs=1e-6)


def test_consulta_a_comando_futuro_e_recusada() -> None:
    """O estagio intermediario de Runge-Kutta cai adiante no tempo.

    Sem esta checagem o erro passa silencioso e a trajetoria fica suave e errada, que
    e o modo de falha mais caro deste projeto.
    """
    linha = linha_senoidal()
    with pytest.raises(ValueError, match="causal"):
        linha.value_at(0.80, now_s=0.79)


def test_historico_fora_de_ordem_e_recusado() -> None:
    linha = CommandDelayLine(initial_value=100.0)
    linha.push(0.10, 120.0)
    with pytest.raises(ValueError, match="fora de ordem"):
        linha.push(0.05, 130.0)


def test_reescrita_no_mesmo_instante_substitui() -> None:
    linha = CommandDelayLine(initial_value=100.0)
    linha.push(0.10, 120.0)
    linha.push(0.10, 125.0)
    assert linha.values == [125.0]


def test_antes_do_historico_devolve_retencao_inicial() -> None:
    linha = linha_senoidal()
    assert linha.value_at(-1.0, now_s=0.5) == pytest.approx(170.0)


def test_atraso_menor_que_o_passo_e_recusado() -> None:
    """Regra do plano: atraso continuo menor que o passo maximo e proibido."""
    linha = CommandDelayLine(initial_value=100.0)
    with pytest.raises(ValueError, match="menor que o passo"):
        linha.validate_against_step(delay_s=0.001, max_step_s=0.002)
    linha.validate_against_step(delay_s=0.020, max_step_s=0.002)
    linha.validate_against_step(delay_s=0.0, max_step_s=0.002)


def test_so_usa_amostras_ja_visiveis() -> None:
    """Consultar o passado de um instante anterior nao pode enxergar o futuro dele."""
    linha = linha_senoidal()
    antigo = linha.value_at(0.30, now_s=0.32)
    completo = linha.value_at(0.30, now_s=0.79)
    assert antigo == pytest.approx(completo, abs=2e-3)


def test_poda_preserva_a_consulta() -> None:
    linha = linha_senoidal()
    antes = linha.delayed_value(now_s=0.700, delay_s=0.05)
    linha.trim(before_s=0.50)
    assert linha.delayed_value(now_s=0.700, delay_s=0.05) == pytest.approx(antes)


# ---------------------------------------------------------------------------
# Validacao do envelope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alteracao",
    [
        {"tau_up_s": 0.0},
        {"tau_down_s": -1.0},
        {"rate_up_max_N_s": 0.0},
        {"rate_down_max_N_s": float("inf")},
        {"transport_delay_s": -0.1},
        {"thrust_min_N": 400.0},
        {"small_step_fraction": 0.0},
        {"small_step_fraction": 1.5},
        {"tau_small_step_up_s": 0.0},
    ],
)
def test_envelope_invalido_e_recusado(alteracao: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        envelope(**alteracao)


def test_rampa_infinita_e_recusada_com_motivo() -> None:
    with pytest.raises(ValueError, match="afirmacao fisica falsa"):
        envelope(rate_up_max_N_s=float("inf"))
