"""Telemetria: os quatro modos de falha da alocacao e a ativacao de limite."""

from __future__ import annotations

import json

import pytest

from hero_atlas.io import AllocatorEventType, TelemetryLog

pytestmark = pytest.mark.unit


def test_registro_generico():
    log = TelemetryLog()
    log.record(1.5, channel="dynamics", kind="trim_solved", residual=1e-9)

    assert len(log) == 1
    (entrada,) = log.records
    assert entrada.time_s == 1.5
    assert entrada.channel == "dynamics"
    assert entrada.data["residual"] == 1e-9


def test_os_quatro_modos_de_falha_sao_distintos():
    """Com limites de caixa e minimos quadrados quase sempre existe solucao
    admissivel, ainda que incapaz de produzir o wrench pedido. Por isso o evento
    principal e wrench_unattainable, nao allocator_infeasible.
    """
    assert len(set(AllocatorEventType)) == 4
    assert AllocatorEventType.WRENCH_UNATTAINABLE != AllocatorEventType.ALLOCATOR_INFEASIBLE
    assert AllocatorEventType.SOLVER_FAILURE != AllocatorEventType.CONSTRAINT_VIOLATION


def test_evento_de_alocacao_separa_pedido_de_entrega():
    log = TelemetryLog()
    log.allocator_event(
        12.475,
        event_type=AllocatorEventType.WRENCH_UNATTAINABLE,
        requested_wrench=[0.0, 35.0, 1220.0, 45.0, -20.0, 8.0],
        achieved_wrench=[0.0, 18.0, 1175.0, 31.0, -16.0, 2.0],
        normalized_residual=0.41,
        active_constraints=["engine_2_thrust_max", "engine_4_ramp_up_max"],
        trim_id="post_failure_trim_003",
    )

    (entrada,) = log.filter(channel="allocator")
    assert entrada.kind == "wrench_unattainable"
    assert entrada.data["requested_force_body_N"] == [0.0, 35.0, 1220.0]
    assert entrada.data["requested_torque_body_Nm"] == [45.0, -20.0, 8.0]
    assert entrada.data["achieved_torque_body_Nm"] == [31.0, -16.0, 2.0]
    assert entrada.data["normalized_residual"] == 0.41
    assert entrada.data["trim_id"] == "post_failure_trim_003"
    assert "engine_2_thrust_max" in entrada.data["active_constraints"]


def test_wrench_precisa_de_seis_componentes():
    log = TelemetryLog()
    with pytest.raises(ValueError, match="6 componentes"):
        log.allocator_event(
            0.0,
            event_type=AllocatorEventType.SOLVER_FAILURE,
            requested_wrench=[1.0, 2.0, 3.0],
            achieved_wrench=[1.0, 2.0, 3.0],
            normalized_residual=0.0,
        )


def test_residuo_negativo_e_rejeitado():
    log = TelemetryLog()
    with pytest.raises(ValueError, match="normalized_residual"):
        log.allocator_event(
            0.0,
            event_type=AllocatorEventType.WRENCH_UNATTAINABLE,
            requested_wrench=[0.0] * 6,
            achieved_wrench=[0.0] * 6,
            normalized_residual=-0.1,
        )


def test_ativacao_de_limite_e_telemetria_nao_guarda():
    """Por ADR-005, saturacao e limite de rampa sao telemetria no produto minimo."""
    log = TelemetryLog()
    log.limit_activation(8.22, actuator="engine_3", limit="thrust_rate_up_max", value=430.0)

    (entrada,) = log.filter(channel="propulsion", kind="limit_activation")
    assert entrada.data["actuator"] == "engine_3"
    assert entrada.data["limit"] == "thrust_rate_up_max"


def test_filtro_por_canal_e_por_tipo():
    log = TelemetryLog()
    log.limit_activation(1.0, actuator="e1", limit="thrust_max")
    log.record(2.0, channel="dynamics", kind="trim_solved")
    log.record(3.0, channel="dynamics", kind="event_applied")

    assert len(log.filter(channel="dynamics")) == 2
    assert len(log.filter(kind="trim_solved")) == 1
    assert len(log.filter(channel="dynamics", kind="event_applied")) == 1
    assert len(log.filter()) == 3


def test_grava_jsonl_sem_pandas(tmp_path):
    """O nucleo nao depende de pandas nem de pyarrow."""
    log = TelemetryLog()
    log.record(1.0, channel="propulsion", kind="spool_up", engine="e1")
    log.record(2.0, channel="propulsion", kind="flameout", engine="e3")

    destino = log.write_jsonl(tmp_path / "runs" / "telemetry.jsonl")
    linhas = destino.read_text(encoding="utf-8").strip().splitlines()

    assert len(linhas) == 2
    primeira = json.loads(linhas[0])
    assert primeira["time_s"] == 1.0
    assert primeira["data"]["engine"] == "e1"


def test_log_e_iteravel():
    log = TelemetryLog()
    log.record(1.0, channel="a", kind="x")
    log.record(2.0, channel="b", kind="y")

    assert [e.time_s for e in log] == [1.0, 2.0]


def test_as_dict_achata_a_carga():
    log = TelemetryLog()
    entrada = log.record(1.0, channel="allocator", kind="ok", residual=0.5)

    achatado = entrada.as_dict()
    assert achatado["time_s"] == 1.0
    assert achatado["data.residual"] == 0.5
