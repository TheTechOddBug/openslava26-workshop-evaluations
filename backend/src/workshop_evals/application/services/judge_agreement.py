"""Meta-evaluation: how much does a judge agree with a stronger reference judge?

Given a finished run whose cells were scored by one judge, this re-scores a sample of the
same responses with a second (reference) judge and measures agreement. It answers the
question the workshop's hardest lab poses: can we trust the judge at all?
"""

from __future__ import annotations

import random

from workshop_evals.application.ports.dataset_repo import DatasetRepositoryPort
from workshop_evals.application.ports.llm_client import LLMClientPort
from workshop_evals.application.ports.model_catalog import ModelCatalogPort
from workshop_evals.application.ports.run_repo import RunRepositoryPort
from workshop_evals.domain.models import EvalMethod, JudgeAgreement, RunParams
from workshop_evals.domain.scoring.judge_rubric import (
    DIMENSIONS,
    build_judge_messages,
    parse_judge_response,
)
from workshop_evals.domain.statistics import (
    agreement_verdict,
    mae,
    pearson,
    rank_agreement,
    spearman,
)


class JudgeAgreementService:
    def __init__(
        self,
        llm: LLMClientPort,
        models: ModelCatalogPort,
        datasets: DatasetRepositoryPort,
        runs: RunRepositoryPort,
    ) -> None:
        self._llm = llm
        self._models = models
        self._datasets = datasets
        self._runs = runs

    async def compare_on_run(
        self,
        run_id: str,
        reference_judge_id: str,
        sample_size: int = 20,
        judge_params: RunParams | None = None,
    ) -> JudgeAgreement:
        run = self._runs.get(run_id)
        if run is None:
            raise LookupError(f"unknown run '{run_id}'")
        reference = self._models.get_model(reference_judge_id)
        if reference is None:
            raise LookupError(f"unknown judge model '{reference_judge_id}'")

        graded = self._collect_graded_cells(run)
        if not graded:
            raise ValueError("run has no LLM-judge scores to compare against")

        sample = _deterministic_sample(graded, sample_size, seed=run_id)
        params = judge_params or RunParams()

        xs: list[float] = []
        ys: list[float] = []
        by_dim: dict[str, tuple[list[float], list[float]]] = {d: ([], []) for d in DIMENSIONS}

        for case_id, response, dims_first in sample:
            case = self._datasets.get_case(case_id)
            if case is None:
                continue
            messages = build_judge_messages(
                case.prompt, response, reference=case.reference, rubric=case.rubric
            )
            completion = await self._llm.chat(reference, messages, params)
            _, _, dims_ref = parse_judge_response(completion.text, case.category)
            for dim in DIMENSIONS:
                a = dims_first.get(dim)
                b = dims_ref.get(dim)
                if a is not None and b is not None:
                    xs.append(a)
                    ys.append(b)
                    by_dim[dim][0].append(a)
                    by_dim[dim][1].append(b)

        mae_overall = mae(xs, ys)
        pearson_r = pearson(xs, ys)
        return JudgeAgreement(
            pearson=pearson_r,
            spearman=spearman(xs, ys),
            rank_agreement=rank_agreement(xs, ys),
            mae_overall=mae_overall,
            mae_by_dimension={d: mae(a, b) for d, (a, b) in by_dim.items() if a},
            verdict=agreement_verdict(pearson_r, mae_overall),
            sample_size=len(sample),
        )

    @staticmethod
    def _collect_graded_cells(run) -> list[tuple[str, str, dict[str, float]]]:
        graded: list[tuple[str, str, dict[str, float]]] = []
        for cell in run.results:
            if not cell.response:
                continue
            for score in cell.scores:
                if score.method == EvalMethod.LLM_JUDGE and score.dimensions:
                    graded.append((cell.case_id, cell.response, score.dimensions))
                    break
        return graded


def _deterministic_sample(
    items: list[tuple[str, str, dict[str, float]]], k: int, seed: str
) -> list[tuple[str, str, dict[str, float]]]:
    ordered = sorted(items, key=lambda it: it[0])
    if k <= 0 or k >= len(ordered):
        return ordered
    rng = random.Random(seed)
    return rng.sample(ordered, k)
