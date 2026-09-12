"""Agenda de eventos e limite de passo do integrador.

Regra do projeto (vault/03 - Regras/Regras de tempo e eventos.md):

    O integrador nunca atravessa um evento agendado sem dividir o passo.

        t_{n+1} = min( t_n + dt_max , t_evento_agendado , t_final )

Este modulo cobre apenas **eventos agendados**, que sao conhecidos antes de integrar
o intervalo. Eventos por guarda, que dependem do estado evoluindo dentro do passo,
entram no marco 3 junto com o integrador.

Por que isto e um entregavel do marco 0: o teste de alinhamento de evento, classe C
de vault/05 - Verificacao/Tres classes de teste.md, ja e verificavel aqui, sem
nenhuma dinamica. Se uma falha agendada em 0,1050 s for aplicada em 0,1100 s, o
simulador ganhou 5 ms de atraso de graca, e um estudo cuja pergunta central e sobre
margem de atraso vira ficcao.
"""

from __future__ import annotations

import heapq
import itertools
import math
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ScheduledEvent",
    "PeriodicSource",
    "EventSchedule",
    "StepPlan",
    "DEFAULT_TIME_TOL_S",
]

DEFAULT_TIME_TOL_S: float = 1e-9
"""Tolerancia de coincidencia temporal.

Dois instantes dentro desta janela sao o mesmo instante. Precisa ser bem menor que
qualquer periodo de amostragem do projeto e bem maior que o erro de ponto flutuante
acumulado em algumas horas de simulacao.
"""


@dataclass(frozen=True, slots=True)
class ScheduledEvent:
    """Evento de instante conhecido antes da integracao.

    Attributes:
        time_s: instante em que o evento deve ser aplicado.
        kind: rotulo, por exemplo ``'controller_tick'`` ou ``'engine_failure'``.
        priority: ordem entre eventos do mesmo instante. Menor aplica primeiro.
        payload: dados livres do evento.
    """

    time_s: float
    kind: str
    priority: int = 0
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not math.isfinite(self.time_s):
            raise ValueError(f"time_s deve ser finito, recebeu {self.time_s!r}")
        if not self.kind:
            raise ValueError("kind nao pode ser vazio")


@dataclass(frozen=True, slots=True)
class PeriodicSource:
    """Fonte de eventos recorrentes, por exemplo controlador a 100 Hz.

    Nao expande para uma lista infinita: o proximo instante e calculado sob demanda.

    Attributes:
        kind: rotulo do evento gerado.
        period_s: periodo entre disparos.
        phase_s: instante do primeiro disparo.
        priority: ordem entre eventos do mesmo instante.
    """

    kind: str
    period_s: float
    phase_s: float = 0.0
    priority: int = 0

    def __post_init__(self) -> None:
        if not math.isfinite(self.period_s) or self.period_s <= 0.0:
            raise ValueError(f"period_s deve ser positivo, recebeu {self.period_s!r}")
        if not math.isfinite(self.phase_s):
            raise ValueError(f"phase_s deve ser finito, recebeu {self.phase_s!r}")

    @classmethod
    def at_rate(
        cls, kind: str, rate_hz: float, *, phase_s: float = 0.0, priority: int = 0
    ) -> PeriodicSource:
        """Constroi a partir da taxa, que e como a configuracao declara."""
        if not math.isfinite(rate_hz) or rate_hz <= 0.0:
            raise ValueError(f"rate_hz deve ser positivo, recebeu {rate_hz!r}")
        return cls(kind=kind, period_s=1.0 / rate_hz, phase_s=phase_s, priority=priority)

    def next_after(self, t_s: float, *, tol_s: float = DEFAULT_TIME_TOL_S) -> float:
        """Menor instante de disparo estritamente maior que ``t_s``.

        Um instante que coincide com ``t_s`` dentro da tolerancia ja e o disparo
        corrente, nao o proximo.
        """
        k = math.floor((t_s + tol_s - self.phase_s) / self.period_s) + 1
        k = max(k, 0)
        return self.phase_s + k * self.period_s

    def is_due_at(self, t_s: float, *, tol_s: float = DEFAULT_TIME_TOL_S) -> bool:
        """Se ha disparo em ``t_s``."""
        if t_s < self.phase_s - tol_s:
            return False
        k = round((t_s - self.phase_s) / self.period_s)
        if k < 0:
            return False
        return abs(self.phase_s + k * self.period_s - t_s) <= tol_s


@dataclass(frozen=True, slots=True)
class StepPlan:
    """O que o integrador deve fazer a partir de um instante.

    Attributes:
        t_s: instante corrente.
        dt_s: passo a integrar. Zero apenas quando ``t_s`` ja e o instante final.
        events_due: eventos a aplicar **em** ``t_s``, antes de integrar.
        limited_by: o que determinou o passo, para diagnostico.
    """

    t_s: float
    dt_s: float
    events_due: tuple[ScheduledEvent, ...]
    limited_by: str

    @property
    def t_next_s(self) -> float:
        return self.t_s + self.dt_s


class EventSchedule:
    """Agenda de eventos agendados, com calculo do limite de passo.

    Mantem eventos pontuais num heap e fontes periodicas calculadas sob demanda.
    """

    def __init__(self, *, tol_s: float = DEFAULT_TIME_TOL_S) -> None:
        if not math.isfinite(tol_s) or tol_s <= 0.0:
            raise ValueError(f"tol_s deve ser positivo, recebeu {tol_s!r}")
        self._tol_s = tol_s
        self._heap: list[tuple[float, int, int, ScheduledEvent]] = []
        self._counter = itertools.count()
        self._periodic: list[PeriodicSource] = []

    @property
    def tol_s(self) -> float:
        return self._tol_s

    @property
    def periodic_sources(self) -> tuple[PeriodicSource, ...]:
        return tuple(self._periodic)

    def add(self, event: ScheduledEvent) -> None:
        """Agenda um evento pontual."""
        heapq.heappush(self._heap, (event.time_s, event.priority, next(self._counter), event))

    def add_many(self, events: Iterable[ScheduledEvent]) -> None:
        for event in events:
            self.add(event)

    def add_periodic(self, source: PeriodicSource) -> None:
        """Registra uma fonte recorrente, por exemplo o tick do controlador."""
        self._periodic.append(source)

    def pending_count(self) -> int:
        """Quantos eventos pontuais ainda estao na agenda."""
        return len(self._heap)

    def next_time_after(self, t_s: float) -> float | None:
        """Proximo instante de evento estritamente maior que ``t_s``.

        ``None`` quando nao ha evento futuro e nao ha fonte periodica.
        """
        candidates: list[float] = []

        for time_s, _priority, _seq, _event in self._heap:
            if time_s > t_s + self._tol_s:
                candidates.append(time_s)

        for source in self._periodic:
            candidates.append(source.next_after(t_s, tol_s=self._tol_s))

        return min(candidates) if candidates else None

    def events_due_at(self, t_s: float) -> tuple[ScheduledEvent, ...]:
        """Eventos que ocorrem em ``t_s``, dentro da tolerancia.

        Eventos pontuais sao **consumidos**. Fontes periodicas geram um evento novo
        a cada chamada e continuam ativas.
        """
        due: list[tuple[int, int, ScheduledEvent]] = []

        while self._heap and self._heap[0][0] <= t_s + self._tol_s:
            _time_s, priority, seq, event = heapq.heappop(self._heap)
            due.append((priority, seq, event))

        for source in self._periodic:
            if source.is_due_at(t_s, tol_s=self._tol_s):
                due.append(
                    (
                        source.priority,
                        -1,
                        ScheduledEvent(
                            time_s=t_s,
                            kind=source.kind,
                            priority=source.priority,
                            payload={"source": "periodic", "period_s": source.period_s},
                        ),
                    )
                )

        due.sort(key=lambda item: (item[0], item[1]))
        return tuple(event for _priority, _seq, event in due)

    def plan_step(self, t_s: float, max_step_s: float, t_final_s: float) -> StepPlan:
        """Decide o passo a partir de ``t_s``, sem pular fronteira discreta.

            dt = min( t + dt_max , t_evento_seguinte , t_final ) - t

        Os eventos devidos em ``t_s`` sao consumidos e devolvidos no plano, para
        serem aplicados **antes** de integrar.
        """
        if not math.isfinite(max_step_s) or max_step_s <= 0.0:
            raise ValueError(f"max_step_s deve ser positivo, recebeu {max_step_s!r}")

        events_due = self.events_due_at(t_s)

        if t_s >= t_final_s - self._tol_s:
            return StepPlan(t_s=t_s, dt_s=0.0, events_due=events_due, limited_by="final")

        t_candidate = t_s + max_step_s
        limited_by = "max_step"

        next_event = self.next_time_after(t_s)
        if next_event is not None and next_event < t_candidate - self._tol_s:
            t_candidate = next_event
            limited_by = "event"

        if t_final_s < t_candidate - self._tol_s:
            t_candidate = t_final_s
            limited_by = "final"

        return StepPlan(
            t_s=t_s,
            dt_s=t_candidate - t_s,
            events_due=events_due,
            limited_by=limited_by,
        )

    def iter_steps(
        self, t_start_s: float, t_final_s: float, max_step_s: float
    ) -> Iterator[StepPlan]:
        """Percorre a simulacao inteira, um plano de passo por vez.

        O ultimo plano tem ``dt_s == 0`` e carrega os eventos devidos no instante
        final, para que nada agendado exatamente no fim seja perdido.
        """
        t_s = t_start_s
        guard = 0
        max_iterations = int(1e8)

        while True:
            plan = self.plan_step(t_s, max_step_s, t_final_s)
            yield plan
            if plan.dt_s <= 0.0:
                return
            t_s = plan.t_next_s

            guard += 1
            if guard > max_iterations:  # pragma: no cover
                raise RuntimeError("iter_steps nao convergiu: passo nulo persistente")
