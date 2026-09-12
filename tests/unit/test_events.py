"""Agenda de eventos: fontes periodicas, limite de passo, consumo."""

from __future__ import annotations

import pytest

from hero_atlas.sim import EventSchedule, PeriodicSource, ScheduledEvent

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------- #
# Fonte periodica
# --------------------------------------------------------------------------- #


def test_proximo_disparo_e_estritamente_maior():
    """Um instante que coincide com t ja e o disparo corrente, nao o proximo."""
    fonte = PeriodicSource.at_rate("tick", rate_hz=100.0)

    assert fonte.next_after(0.0) == pytest.approx(0.01)
    assert fonte.next_after(0.005) == pytest.approx(0.01)
    assert fonte.next_after(0.01) == pytest.approx(0.02)


def test_fonte_com_fase():
    fonte = PeriodicSource(kind="tick", period_s=0.01, phase_s=0.005)

    assert fonte.next_after(0.0) == pytest.approx(0.005)
    assert fonte.next_after(0.005) == pytest.approx(0.015)
    assert fonte.is_due_at(0.005) is True
    assert fonte.is_due_at(0.0) is False


def test_antes_da_fase_nao_ha_disparo():
    fonte = PeriodicSource(kind="tick", period_s=0.01, phase_s=0.1)
    assert fonte.is_due_at(0.05) is False
    assert fonte.next_after(0.0) == pytest.approx(0.1)


def test_at_rate_converte_taxa_em_periodo():
    assert PeriodicSource.at_rate("tick", rate_hz=200.0).period_s == pytest.approx(0.005)


def test_taxa_invalida_falha():
    with pytest.raises(ValueError, match="rate_hz"):
        PeriodicSource.at_rate("tick", rate_hz=0.0)


def test_periodo_invalido_falha():
    with pytest.raises(ValueError, match="period_s"):
        PeriodicSource(kind="tick", period_s=-1.0)


# --------------------------------------------------------------------------- #
# Evento pontual
# --------------------------------------------------------------------------- #


def test_evento_exige_instante_finito():
    with pytest.raises(ValueError, match="finito"):
        ScheduledEvent(time_s=float("inf"), kind="falha")


def test_evento_exige_tipo():
    with pytest.raises(ValueError, match="kind"):
        ScheduledEvent(time_s=1.0, kind="")


# --------------------------------------------------------------------------- #
# Agenda
# --------------------------------------------------------------------------- #


def test_evento_pontual_e_consumido_uma_vez():
    agenda = EventSchedule()
    agenda.add(ScheduledEvent(time_s=1.0, kind="falha"))

    assert agenda.pending_count() == 1
    primeiro = agenda.events_due_at(1.0)
    segundo = agenda.events_due_at(1.0)

    assert len(primeiro) == 1
    assert segundo == ()
    assert agenda.pending_count() == 0


def test_fonte_periodica_nao_e_consumida():
    agenda = EventSchedule()
    agenda.add_periodic(PeriodicSource.at_rate("tick", rate_hz=100.0))

    assert len(agenda.events_due_at(0.01)) == 1
    assert len(agenda.events_due_at(0.02)) == 1


def test_proximo_instante_considera_pontuais_e_periodicos():
    agenda = EventSchedule()
    agenda.add_periodic(PeriodicSource.at_rate("tick", rate_hz=100.0))
    agenda.add(ScheduledEvent(time_s=0.0035, kind="falha"))

    assert agenda.next_time_after(0.0) == pytest.approx(0.0035)
    assert agenda.next_time_after(0.004) == pytest.approx(0.01)


def test_sem_eventos_nao_ha_proximo_instante():
    assert EventSchedule().next_time_after(0.0) is None


def test_limite_de_passo_pelo_maximo():
    agenda = EventSchedule()
    plano = agenda.plan_step(0.0, max_step_s=0.01, t_final_s=1.0)

    assert plano.dt_s == pytest.approx(0.01)
    assert plano.limited_by == "max_step"


def test_limite_de_passo_por_evento():
    agenda = EventSchedule()
    agenda.add(ScheduledEvent(time_s=0.003, kind="falha"))

    plano = agenda.plan_step(0.0, max_step_s=0.01, t_final_s=1.0)

    assert plano.dt_s == pytest.approx(0.003)
    assert plano.limited_by == "event"


def test_limite_de_passo_pelo_instante_final():
    agenda = EventSchedule()
    plano = agenda.plan_step(0.0, max_step_s=0.01, t_final_s=0.004)

    assert plano.dt_s == pytest.approx(0.004)
    assert plano.limited_by == "final"


def test_passo_nulo_no_instante_final():
    agenda = EventSchedule()
    plano = agenda.plan_step(1.0, max_step_s=0.01, t_final_s=1.0)

    assert plano.dt_s == 0.0
    assert plano.limited_by == "final"


def test_passo_maximo_invalido_falha():
    with pytest.raises(ValueError, match="max_step_s"):
        EventSchedule().plan_step(0.0, max_step_s=0.0, t_final_s=1.0)


def test_t_next_soma_o_passo():
    plano = EventSchedule().plan_step(0.5, max_step_s=0.01, t_final_s=1.0)
    assert plano.t_next_s == pytest.approx(0.51)


def test_add_many_agenda_varios():
    agenda = EventSchedule()
    agenda.add_many([ScheduledEvent(time_s=t, kind=f"e{i}") for i, t in enumerate([0.1, 0.2, 0.3])])
    assert agenda.pending_count() == 3


def test_tolerancia_invalida_falha():
    with pytest.raises(ValueError, match="tol_s"):
        EventSchedule(tol_s=0.0)


def test_fontes_periodicas_sao_expostas():
    agenda = EventSchedule()
    fonte = PeriodicSource.at_rate("tick", rate_hz=100.0)
    agenda.add_periodic(fonte)

    assert agenda.periodic_sources == (fonte,)


def test_payload_do_evento_periodico_identifica_a_origem():
    agenda = EventSchedule()
    agenda.add_periodic(PeriodicSource.at_rate("controller_tick", rate_hz=100.0))

    (evento,) = agenda.events_due_at(0.01)

    assert evento.payload["source"] == "periodic"
    assert evento.payload["period_s"] == pytest.approx(0.01)
