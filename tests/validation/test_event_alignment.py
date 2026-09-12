"""Classe C: alinhamento de evento.

Ver vault/05 - Verificacao/Tres classes de teste.md

    Falha agendada em t = 0,105 s, passo maximo de 10 ms, controlador a 100 Hz.
    O evento tem que ser aplicado em 0,105 s, nao adiado para 0,110 s.

    O simulador nao pode ganhar nem perder 5 ms de atraso porque a malha temporal
    foi inconvenientemente escolhida.

Num estudo cuja pergunta central e sobre margem de atraso, ganhar 5 ms de graca nao
e detalhe de implementacao: e a diferenca entre concluir que o traje e controlavel e
concluir que nao e.
"""

from __future__ import annotations

import numpy as np
import pytest

from hero_atlas.sim import EventSchedule, PeriodicSource, ScheduledEvent

pytestmark = pytest.mark.validation


def test_falha_em_0105_e_aplicada_em_0105_e_nao_em_0110():
    """O caso canonico, exatamente como descrito na regra."""
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))
    schedule.add(ScheduledEvent(time_s=0.105, kind="engine_failure", payload={"engine": 3}))

    aplicados: list[tuple[float, str]] = []
    for plan in schedule.iter_steps(t_start_s=0.0, t_final_s=0.2, max_step_s=0.010):
        for event in plan.events_due:
            aplicados.append((plan.t_s, event.kind))

    falhas = [t for t, kind in aplicados if kind == "engine_failure"]

    assert len(falhas) == 1, "a falha tem que ser aplicada exatamente uma vez"
    assert falhas[0] == pytest.approx(0.105, abs=1e-12), (
        f"falha aplicada em {falhas[0]:.6f} s. "
        "Adiar para a fronteira do passo concede atraso nao declarado."
    )


def test_nenhum_passo_atravessa_um_evento_agendado():
    """A regra estrutural: o integrador nunca pula uma fronteira discreta."""
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))
    schedule.add_periodic(PeriodicSource.at_rate("imu_tick", rate_hz=200.0))
    schedule.add_many(
        [
            ScheduledEvent(time_s=0.105, kind="engine_failure"),
            ScheduledEvent(time_s=0.1234, kind="gust_start"),
            ScheduledEvent(time_s=0.1777, kind="gust_end"),
        ]
    )

    instantes_de_evento = {0.105, 0.1234, 0.1777}
    instantes_de_evento |= {round(k * 0.010, 10) for k in range(0, 21)}
    instantes_de_evento |= {round(k * 0.005, 10) for k in range(0, 41)}

    for plan in schedule.iter_steps(t_start_s=0.0, t_final_s=0.2, max_step_s=0.010):
        if plan.dt_s <= 0.0:
            continue
        inicio, fim = plan.t_s, plan.t_next_s
        atravessados = [t for t in instantes_de_evento if inicio + 1e-12 < t < fim - 1e-12]
        assert not atravessados, f"passo de {inicio:.6f} a {fim:.6f} atravessou {atravessados}"


def test_passo_nunca_excede_o_maximo():
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))
    max_step = 0.010

    for plan in schedule.iter_steps(t_start_s=0.0, t_final_s=0.5, max_step_s=max_step):
        assert plan.dt_s <= max_step + 1e-12


def test_simulacao_termina_exatamente_no_instante_final():
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))
    t_final = 0.1234

    ultimo = None
    for plan in schedule.iter_steps(t_start_s=0.0, t_final_s=t_final, max_step_s=0.010):
        ultimo = plan

    assert ultimo is not None
    assert ultimo.dt_s == 0.0
    assert ultimo.t_s == pytest.approx(t_final, abs=1e-12)


def test_passo_irregular_e_esperado_e_registrado():
    """Dividir na fronteira torna o passo nao uniforme. Isso e correto, e e por isso
    que limite de rampa e filtro discreto sao avaliados contra o proprio periodo
    declarado, nunca contra o passo instantaneo do integrador.
    """
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))
    schedule.add(ScheduledEvent(time_s=0.105, kind="engine_failure"))

    passos = [
        plan.dt_s
        for plan in schedule.iter_steps(t_start_s=0.0, t_final_s=0.15, max_step_s=0.010)
        if plan.dt_s > 0.0
    ]

    assert not np.allclose(passos, passos[0]), "o passo deveria ser irregular aqui"
    assert any(np.isclose(dt, 0.005, atol=1e-9) for dt in passos), (
        "esperava um passo de 5 ms entre 0,100 e 0,105"
    )


def test_evento_no_instante_inicial_nao_e_perdido():
    """Um tick em t=0 e devido em t=0, nao em t=periodo."""
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))
    schedule.add(ScheduledEvent(time_s=0.0, kind="arm"))

    primeiro = next(schedule.iter_steps(t_start_s=0.0, t_final_s=0.05, max_step_s=0.010))
    tipos = {event.kind for event in primeiro.events_due}

    assert "arm" in tipos
    assert "controller_tick" in tipos


def test_evento_no_instante_final_nao_e_perdido():
    schedule = EventSchedule()
    schedule.add(ScheduledEvent(time_s=0.2, kind="fim_de_cenario"))

    aplicados = [
        (plan.t_s, event.kind)
        for plan in schedule.iter_steps(t_start_s=0.0, t_final_s=0.2, max_step_s=0.010)
        for event in plan.events_due
    ]

    assert (0.2, "fim_de_cenario") in [(round(t, 10), kind) for t, kind in aplicados]


def test_prioridade_ordena_eventos_do_mesmo_instante():
    """Reconfiguracao de atuador tem que vir antes do tick do controlador."""
    schedule = EventSchedule()
    schedule.add_many(
        [
            ScheduledEvent(time_s=0.05, kind="controller_tick", priority=10),
            ScheduledEvent(time_s=0.05, kind="engine_failure", priority=0),
            ScheduledEvent(time_s=0.05, kind="reconfigure", priority=1),
        ]
    )

    plan = schedule.plan_step(0.05, max_step_s=0.01, t_final_s=0.1)
    ordem = [event.kind for event in plan.events_due]

    assert ordem == ["engine_failure", "reconfigure", "controller_tick"]


@pytest.mark.parametrize(
    ("rate_hz", "t_final"),
    [(100.0, 1.0), (200.0, 0.5), (50.0, 2.0), (333.0, 0.3)],
)
def test_contagem_de_ticks_bate_com_a_taxa(rate_hz: float, t_final: float):
    """Sem tick perdido nem tick duplicado ao longo de toda a simulacao."""
    schedule = EventSchedule()
    schedule.add_periodic(PeriodicSource.at_rate("tick", rate_hz=rate_hz))

    ticks = sum(
        1
        for plan in schedule.iter_steps(0.0, t_final, max_step_s=0.010)
        for event in plan.events_due
        if event.kind == "tick"
    )

    esperado = int(np.floor(t_final * rate_hz + 1e-9)) + 1  # inclui t = 0
    assert ticks == esperado
