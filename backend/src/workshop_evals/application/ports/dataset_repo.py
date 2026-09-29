"""Driven port for reading the evaluation datasets (test cases)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from workshop_evals.domain.models import EvalCase


@runtime_checkable
class DatasetRepositoryPort(Protocol):
    def list_categories(self) -> list[str]:
        """Return the available category names, sorted."""
        ...

    def get_cases(self, category: str) -> list[EvalCase]:
        """Return every case in a category."""
        ...

    def get_case(self, case_id: str) -> EvalCase | None:
        """Return a single case by id, or None if unknown."""
        ...

    def all_cases(self) -> list[EvalCase]:
        """Return every case across all categories, including disabled ones, for management."""
        ...

    def upsert_case(self, case: EvalCase) -> EvalCase:
        """Add or replace a user-managed case; persisted to the overlay."""
        ...

    def remove_case(self, case_id: str) -> bool:
        """Delete a user-added case. Returns False for base (file) cases."""
        ...

    def set_enabled(self, case_id: str, enabled: bool) -> EvalCase | None:
        """Enable or disable a case, or None if unknown."""
        ...
