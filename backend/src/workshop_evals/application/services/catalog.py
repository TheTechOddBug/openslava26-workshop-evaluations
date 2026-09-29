"""Read-only catalogue: the models, datasets and evaluators the UI can pick from."""

from __future__ import annotations

from dataclasses import dataclass

from workshop_evals.application.ports.dataset_repo import DatasetRepositoryPort
from workshop_evals.application.ports.model_catalog import ModelCatalogPort
from workshop_evals.application.services.evaluator import EvaluatorRegistry
from workshop_evals.domain.models import EvalMethod, ModelSpec


@dataclass(frozen=True)
class DatasetSummary:
    category: str
    count: int
    methods: list[str]  # eval methods that apply to at least one case in the category


class CatalogService:
    def __init__(
        self,
        models: ModelCatalogPort,
        datasets: DatasetRepositoryPort,
        registry: EvaluatorRegistry,
    ) -> None:
        self._models = models
        self._datasets = datasets
        self._registry = registry

    def list_models(self) -> list[ModelSpec]:
        return self._models.list_models()

    def list_evaluators(self) -> list[dict]:
        """Evaluator catalogue metadata, ordered by tier then method."""
        specs = [ev.spec for ev in self._registry.all()]
        return [
            {
                "method": s.method.value,
                "tier": s.tier.value,
                "label": s.label,
                "description": s.description,
                "required_fields": sorted(s.required_fields),
                "needs_judge": s.needs_judge,
            }
            for s in specs
        ]

    def list_datasets(self) -> list[DatasetSummary]:
        summaries: list[DatasetSummary] = []
        for category in self._datasets.list_categories():
            cases = self._datasets.get_cases(category)
            methods: set[str] = set()
            for case in cases:
                for ev in self._registry.applicable(case):
                    methods.add(ev.spec.method.value)
            summaries.append(
                DatasetSummary(category=category, count=len(cases), methods=sorted(methods))
            )
        return summaries

    def applicable_methods(self, case_id: str) -> list[EvalMethod]:
        case = self._datasets.get_case(case_id)
        if case is None:
            return []
        return [ev.spec.method for ev in self._registry.applicable(case)]
