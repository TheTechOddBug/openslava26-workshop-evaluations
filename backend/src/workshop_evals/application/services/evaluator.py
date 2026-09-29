"""The evaluator abstraction: one uniform interface for every scoring mechanism.

Deterministic evaluators are pure and ignore the context; judge-based ones use the
injected LLM client. Treating them alike is what lets the frontend offer the whole
progression -- from an exact match to an ensemble of judges -- as a single list, and
apply any applicable mechanism to any case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from workshop_evals.application.ports.llm_client import LLMClientPort
from workshop_evals.domain.models import (
    EvalCase,
    EvalMethod,
    EvalTier,
    ModelSpec,
    RunParams,
    Score,
)


@dataclass(frozen=True)
class EvaluatorSpec:
    """Catalogue metadata for one mechanism, surfaced to the UI."""

    method: EvalMethod
    tier: EvalTier
    label: str
    description: str
    required_fields: frozenset[str] = frozenset()
    needs_judge: bool = False


@dataclass
class EvaluationContext:
    """Extra inputs a judge-based evaluator needs; empty for deterministic ones."""

    judge_client: LLMClientPort | None = None
    judge_model: ModelSpec | None = None
    judge_params: RunParams = field(default_factory=RunParams)


@runtime_checkable
class Evaluator(Protocol):
    spec: EvaluatorSpec

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        """Score a model response for a case and return a normalised [0, 1] result."""
        ...


class EvaluatorRegistry:
    """Holds one evaluator per method and answers 'which apply to this case?'."""

    def __init__(self) -> None:
        self._by_method: dict[EvalMethod, Evaluator] = {}

    def register(self, evaluator: Evaluator) -> None:
        self._by_method[evaluator.spec.method] = evaluator

    def get(self, method: EvalMethod) -> Evaluator:
        if method not in self._by_method:
            raise KeyError(f"no evaluator registered for method '{method.value}'")
        return self._by_method[method]

    def all(self) -> list[Evaluator]:
        return list(self._by_method.values())

    def applicable(self, case: EvalCase) -> list[Evaluator]:
        """Evaluators whose required fields are all present on the case."""
        present = case.available_fields()
        return [ev for ev in self._by_method.values() if ev.spec.required_fields <= present]
