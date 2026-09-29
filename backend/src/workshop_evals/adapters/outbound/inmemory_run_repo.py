"""In-memory store for runs. Enough for a workshop; swap for SQLite to persist."""

from __future__ import annotations

from workshop_evals.domain.models import Run


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    def save(self, run: Run) -> None:
        self._runs[run.id] = run

    def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)
