"""Driven port for persisting matrix runs while they execute and after they finish."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from workshop_evals.domain.models import Run


@runtime_checkable
class RunRepositoryPort(Protocol):
    def save(self, run: Run) -> None:
        """Create or replace a run."""
        ...

    def get(self, run_id: str) -> Run | None:
        """Return a run by id, or None if unknown."""
        ...
