"""Ensemble judging: score one response with several judges and average them.

Averaging independent judges reduces the influence of any single model's quirks; the
spread (standard deviation) of their scores is itself a signal — wide disagreement means
the task is hard to judge and the average should be trusted less.
"""

from __future__ import annotations

import statistics

from workshop_evals.application.ports.dataset_repo import DatasetRepositoryPort
from workshop_evals.application.ports.llm_client import LLMClientPort
from workshop_evals.application.ports.model_catalog import ModelCatalogPort
from workshop_evals.domain.models import (
    CandidateConfig,
    EnsembleResult,
    EvalCase,
    JudgeScore,
    RunParams,
)
from workshop_evals.domain.scoring.judge_rubric import (
    DIMENSIONS,
    build_judge_messages,
    parse_judge_response,
)


class EnsembleJudgeService:
    def __init__(
        self,
        llm: LLMClientPort,
        models: ModelCatalogPort,
        datasets: DatasetRepositoryPort,
    ) -> None:
        self._llm = llm
        self._models = models
        self._datasets = datasets

    async def judge(
        self,
        case: EvalCase,
        candidate: CandidateConfig,
        judge_model_ids: list[str],
        judge_params: RunParams | None = None,
    ) -> EnsembleResult:
        model = self._models.get_model(candidate.model_id)
        judges = [self._models.get_model(jid) for jid in judge_model_ids]
        if model is None or not judge_model_ids or any(j is None for j in judges):
            return EnsembleResult(
                case_id=case.id, response="", error="unknown candidate model or judge"
            )

        params = judge_params or RunParams()
        completion = await self._llm.chat(
            model,
            [{"role": "user", "content": candidate.prompt_for(case.prompt)}],
            candidate.params,
        )
        response = completion.text
        messages = build_judge_messages(
            case.prompt, response, reference=case.reference, rubric=case.rubric
        )

        per_judge: list[JudgeScore] = []
        for judge in judges:
            assert judge is not None
            reply = await self._llm.chat(judge, messages, params)
            score, _justification, dims = parse_judge_response(reply.text, case.category)
            per_judge.append(JudgeScore(judge_model=judge.id, score=score, dimensions=dims))

        scores = [j.score for j in per_judge]
        ensemble_dims = {
            dim: statistics.fmean([j.dimensions.get(dim, 0.0) for j in per_judge])
            for dim in DIMENSIONS
        }
        return EnsembleResult(
            case_id=case.id,
            response=response,
            per_judge=per_judge,
            ensemble_score=statistics.fmean(scores) if scores else 0.0,
            ensemble_dimensions=ensemble_dims,
            spread=statistics.pstdev(scores) if len(scores) > 1 else 0.0,
        )
