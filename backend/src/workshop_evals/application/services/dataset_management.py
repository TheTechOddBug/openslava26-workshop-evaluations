"""Manage the dataset catalogue from the UI: add, edit, enable, remove cases.

The shipped JSONL base is never modified; user changes go to a gitignored overlay that
overrides the base by id. Base cases can be disabled but not deleted.
"""

from __future__ import annotations

from workshop_evals.application.ports.dataset_repo import DatasetRepositoryPort
from workshop_evals.domain.models import EvalCase


class DatasetManagementService:
    def __init__(self, datasets: DatasetRepositoryPort) -> None:
        self._datasets = datasets

    def list_all(self) -> list[dict]:
        """Every case (including disabled), each tagged with its source."""
        return [c.model_dump(mode="json") for c in self._datasets.all_cases()]

    def upsert(self, case: EvalCase) -> dict:
        return self._datasets.upsert_case(case).model_dump(mode="json")

    def remove(self, case_id: str) -> bool:
        return self._datasets.remove_case(case_id)

    def set_enabled(self, case_id: str, enabled: bool) -> dict | None:
        updated = self._datasets.set_enabled(case_id, enabled)
        return updated.model_dump(mode="json") if updated else None
