"""Telemetria: o registro que transforma "nao conseguiu" em diagnostico.

Ver vault/04 - Fisica/Telemetria.md

    Transformar o simulador de um sistema que informa "nao conseguiu" num
    instrumento que explica o que foi pedido, o que foi entregue, qual eixo faltou e
    qual limite estava ativo.

Dois registros ja tem forma definida, mesmo antes de existir alocador:

- ``allocator_event``, com os **quatro** modos de falha distinguidos. Com limites de
  caixa e objetivo de minimos quadrados quase sempre existe solucao admissivel,
  ainda que incapaz de produzir o wrench pedido. Por isso o evento principal e
  ``wrench_unattainable``, nao ``allocator_infeasible``.
- ``limit_activation``, porque por ADR-005 saturacao e limite de rampa sao
  telemetria, nao guarda, no produto minimo.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "AllocatorEventType",
    "TelemetryRecord",
    "TelemetryLog",
]


class AllocatorEventType(StrEnum):
    """Os quatro modos de falha da alocacao, que nao se confundem.

    Attributes:
        WRENCH_UNATTAINABLE: houve solucao, mas o comando esta fora do conjunto
            atingivel. E o evento principal e o mais comum.
        ALLOCATOR_INFEASIBLE: igualdade dura mais limites fisicos sem solucao.
        SOLVER_FAILURE: condicionamento, escala ou algoritmo. Nao e falha fisica.
        CONSTRAINT_VIOLATION: o retorno viola restricao por tolerancia numerica.
    """

    WRENCH_UNATTAINABLE = "wrench_unattainable"
    ALLOCATOR_INFEASIBLE = "allocator_infeasible"
    SOLVER_FAILURE = "solver_failure"
    CONSTRAINT_VIOLATION = "constraint_violation"


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    """Uma linha de telemetria.

    Attributes:
        time_s: instante de simulacao.
        channel: agrupador, por exemplo ``'allocator'`` ou ``'propulsion'``.
        kind: o que aconteceu.
        data: carga livre, sempre serializavel em JSON.
    """

    time_s: float
    channel: str
    kind: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "time_s": self.time_s,
            "channel": self.channel,
            "kind": self.kind,
            **{f"data.{k}": v for k, v in self.data.items()},
        }


class TelemetryLog:
    """Coletor de registros de uma execucao.

    Mantem tudo em memoria. Persistencia em Parquet entra quando pandas estiver no
    ambiente; o nucleo nao depende dele.
    """

    def __init__(self) -> None:
        self._records: list[TelemetryRecord] = []

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[TelemetryRecord]:
        return iter(self._records)

    @property
    def records(self) -> tuple[TelemetryRecord, ...]:
        return tuple(self._records)

    def record(self, time_s: float, channel: str, kind: str, **data: Any) -> TelemetryRecord:
        """Registra uma linha generica."""
        entry = TelemetryRecord(time_s=time_s, channel=channel, kind=kind, data=data)
        self._records.append(entry)
        return entry

    def limit_activation(
        self,
        time_s: float,
        *,
        actuator: str,
        limit: str,
        value: float | None = None,
    ) -> TelemetryRecord:
        """Saturacao ou limite de rampa ativado.

        Por ADR-005 isto e telemetria, nao evento por guarda, no produto minimo.
        """
        return self.record(
            time_s,
            channel="propulsion",
            kind="limit_activation",
            actuator=actuator,
            limit=limit,
            value=value,
        )

    def allocator_event(
        self,
        time_s: float,
        *,
        event_type: AllocatorEventType,
        requested_wrench: Sequence[float],
        achieved_wrench: Sequence[float],
        normalized_residual: float,
        active_constraints: Iterable[str] = (),
        trim_id: str | None = None,
    ) -> TelemetryRecord:
        """Evento de alocacao, com pedido, entrega e restricoes ativas.

        Args:
            requested_wrench: seis componentes, forca e depois torque, no
                referencial do corpo e sobre o ponto de referencia ``O``.
            achieved_wrench: idem, o que a alocacao conseguiu.
            normalized_residual: resduo escalado pela **mesma** matriz ``S`` usada na
                margem geometrica. Sem isso forca e torque nao sao comparaveis.
            active_constraints: quais limites estavam ativos na solucao.
            trim_id: qual trim estava valendo, util apos falha.
        """
        requested = list(map(float, requested_wrench))
        achieved = list(map(float, achieved_wrench))
        if len(requested) != 6 or len(achieved) != 6:
            raise ValueError(
                "wrench deve ter 6 componentes: forca (3) e torque (3), "
                f"recebeu {len(requested)} e {len(achieved)}"
            )
        if normalized_residual < 0.0:
            raise ValueError(f"normalized_residual nao pode ser negativo: {normalized_residual!r}")
        return self.record(
            time_s,
            channel="allocator",
            kind=str(event_type),
            requested_force_body_N=requested[:3],
            requested_torque_body_Nm=requested[3:],
            achieved_force_body_N=achieved[:3],
            achieved_torque_body_Nm=achieved[3:],
            normalized_residual=normalized_residual,
            active_constraints=list(active_constraints),
            trim_id=trim_id,
        )

    def filter(
        self, *, channel: str | None = None, kind: str | None = None
    ) -> tuple[TelemetryRecord, ...]:
        """Subconjunto por canal e por tipo."""
        return tuple(
            r
            for r in self._records
            if (channel is None or r.channel == channel) and (kind is None or r.kind == kind)
        )

    def write_jsonl(self, path: str | pathlib.Path) -> pathlib.Path:
        """Grava em JSON Lines, sem depender de pandas nem de pyarrow."""
        target = pathlib.Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for entry in self._records:
                payload = {
                    "time_s": entry.time_s,
                    "channel": entry.channel,
                    "kind": entry.kind,
                    "data": dict(entry.data),
                }
                handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return target

    def to_dataframe(self):  # type: ignore[no-untyped-def]
        """DataFrame achatado. Importa pandas sob demanda, nunca no import do nucleo."""
        import pandas as pd

        return pd.DataFrame([r.as_dict() for r in self._records])
