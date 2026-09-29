"""Use case: run one cell, or a whole matrix of cells, and score the responses.

A cell is one case answered by one candidate configuration, then scored by every requested
mechanism that applies to that case. A matrix is the cartesian product of cases and
candidates. Cells run sequentially: a shared local model server (Ollama) swaps models in
and out one at a time, so serial execution is both correct and predictable. Concurrency for
purely hosted runs is a later refinement.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from workshop_evals.application.ports.dataset_repo import DatasetRepositoryPort
from workshop_evals.application.ports.llm_client import LLMClientPort
from workshop_evals.application.ports.model_catalog import ModelCatalogPort
from workshop_evals.application.ports.run_repo import RunRepositoryPort
from workshop_evals.application.services.evaluator import EvaluationContext, EvaluatorRegistry
from workshop_evals.domain.models import (
    CandidateConfig,
    CellResult,
    EvalCase,
    EvalMethod,
    MatrixSpec,
    ModelSpec,
    Run,
    RunParams,
    RunStatus,
    Score,
)


class RunEvaluationService:
    def __init__(
        self,
        llm: LLMClientPort,
        models: ModelCatalogPort,
        datasets: DatasetRepositoryPort,
        registry: EvaluatorRegistry,
        runs: RunRepositoryPort,
    ) -> None:
        self._llm = llm
        self._models = models
        self._datasets = datasets
        self._registry = registry
        self._runs = runs

    async def evaluate_cell(
        self,
        case: EvalCase,
        candidate: CandidateConfig,
        methods: list[EvalMethod],
        judge_model_id: str | None = None,
        judge_params: RunParams | None = None,
    ) -> CellResult:
        model = self._models.get_model(candidate.model_id)
        if model is None:
            return _error_cell(case, candidate, f"unknown model '{candidate.model_id}'")

        prompt = candidate.prompt_override or case.prompt
        messages = [{"role": "user", "content": prompt}]
        completion = await self._llm.chat(model, messages, candidate.params)
        if completion.error:
            return _error_cell(case, candidate, completion.error)

        ctx = self._build_context(methods, judge_model_id, judge_params)
        applicable = {ev.spec.method for ev in self._registry.applicable(case)}
        scores: list[Score] = []
        for method in methods:
            if method not in applicable:
                continue  # mechanism does not apply to this case (missing reference field)
            evaluator = self._registry.get(method)
            score = await evaluator.evaluate(case, completion.text, ctx)
            if evaluator.spec.needs_judge and ctx.judge_model and ctx.judge_model.id == model.id:
                score.detail = f"self-evaluation: judge equals candidate. {score.detail}".strip()
            scores.append(score)

        return CellResult(
            case_id=case.id,
            model_id=model.id,
            label=candidate.label or model.id,
            params=candidate.params,
            response=completion.text,
            usage=completion.usage,
            scores=scores,
        )

    def create_run(self, spec: MatrixSpec) -> Run:
        """Register a pending run and return it immediately; execution happens later."""
        run = Run(
            id=uuid.uuid4().hex,
            spec=spec,
            status=RunStatus.PENDING,
            total_cells=len(spec.case_ids) * len(spec.candidates),
            created_at=datetime.now(UTC).isoformat(),
        )
        self._runs.save(run)
        return run

    async def execute_run(self, run_id: str) -> None:
        """Run every cell in the background, saving after each so progress is pollable."""
        run = self._runs.get(run_id)
        if run is None:
            return
        run.status = RunStatus.RUNNING
        self._runs.save(run)
        spec = run.spec
        try:
            for case_id in spec.case_ids:
                case = self._datasets.get_case(case_id)
                if case is None:
                    run.completed_cells += len(spec.candidates)
                    self._runs.save(run)
                    continue
                for candidate in spec.candidates:
                    cell = await self.evaluate_cell(
                        case, candidate, spec.methods, spec.judge_model_id, spec.judge_params
                    )
                    run.results.append(cell)
                    run.completed_cells += 1
                    self._runs.save(run)
            run.status = RunStatus.COMPLETED
        except Exception as exc:  # keep partial results; surface the failure
            run.status = RunStatus.FAILED
            run.error = str(exc)
        self._runs.save(run)

    def _build_context(
        self,
        methods: list[EvalMethod],
        judge_model_id: str | None,
        judge_params: RunParams | None,
    ) -> EvaluationContext:
        needs_judge = any(self._registry.get(m).spec.needs_judge for m in methods)
        judge_model: ModelSpec | None = None
        if needs_judge and judge_model_id:
            judge_model = self._models.get_model(judge_model_id)
        return EvaluationContext(
            judge_client=self._llm,
            judge_model=judge_model,
            judge_params=judge_params or RunParams(),
        )


def _error_cell(case: EvalCase, candidate: CandidateConfig, message: str) -> CellResult:
    return CellResult(
        case_id=case.id,
        model_id=candidate.model_id,
        label=candidate.label or candidate.model_id,
        params=candidate.params,
        response="",
        error=message,
    )
