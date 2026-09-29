"""Pairwise comparison: ask a judge which of two answers is better.

Optionally re-judges with the two answers in swapped positions. If the winning answer
changes, the judge preferred a position rather than an answer -- position bias, made
visible. This is the substrate for the workshop's judge-bias lab.
"""

from __future__ import annotations

from workshop_evals.application.ports.dataset_repo import DatasetRepositoryPort
from workshop_evals.application.ports.llm_client import LLMClientPort
from workshop_evals.application.ports.model_catalog import ModelCatalogPort
from workshop_evals.domain.models import (
    CandidateConfig,
    EvalCase,
    ModelSpec,
    PairwiseResult,
    PairwiseVerdict,
    RunParams,
)
from workshop_evals.domain.scoring.judge_rubric import (
    build_pairwise_messages,
    parse_pairwise_verdict,
)

_TO_VERDICT = {"A": PairwiseVerdict.A, "B": PairwiseVerdict.B, "tie": PairwiseVerdict.TIE}
_SWAP_BACK = {"A": "B", "B": "A", "tie": "tie"}  # map a swapped-position winner to answer terms


class ComparePairwiseService:
    def __init__(
        self,
        llm: LLMClientPort,
        models: ModelCatalogPort,
        datasets: DatasetRepositoryPort,
    ) -> None:
        self._llm = llm
        self._models = models
        self._datasets = datasets

    async def compare(
        self,
        case: EvalCase,
        candidate_a: CandidateConfig,
        candidate_b: CandidateConfig,
        judge_model_id: str,
        judge_params: RunParams | None = None,
        swap: bool = True,
    ) -> PairwiseResult:
        model_a = self._models.get_model(candidate_a.model_id)
        model_b = self._models.get_model(candidate_b.model_id)
        judge = self._models.get_model(judge_model_id)
        if model_a is None or model_b is None or judge is None:
            return PairwiseResult(
                case_id=case.id,
                prompt=case.prompt,
                model_a=candidate_a.model_id,
                model_b=candidate_b.model_id,
                response_a="",
                response_b="",
                verdict=PairwiseVerdict.TIE,
                justification="",
                judge_model=judge_model_id,
                error="unknown candidate model or judge",
            )

        params = judge_params or RunParams()
        response_a = await self._answer(
            model_a, candidate_a.prompt_override or case.prompt, candidate_a.params
        )
        response_b = await self._answer(
            model_b, candidate_b.prompt_override or case.prompt, candidate_b.params
        )

        winner, justification = await self._judge(case, response_a, response_b, judge, params)
        result = PairwiseResult(
            case_id=case.id,
            prompt=case.prompt,
            model_a=model_a.id,
            model_b=model_b.id,
            response_a=response_a,
            response_b=response_b,
            verdict=_TO_VERDICT[winner],
            justification=justification,
            judge_model=judge.id,
        )

        if swap:
            swapped_winner, _ = await self._judge(case, response_b, response_a, judge, params)
            result.swapped_verdict = _TO_VERDICT[_SWAP_BACK[swapped_winner]]
            result.position_bias = result.verdict != result.swapped_verdict

        return result

    async def _answer(self, model: ModelSpec, prompt: str, params: RunParams) -> str:
        completion = await self._llm.chat(model, [{"role": "user", "content": prompt}], params)
        return completion.text

    async def _judge(
        self, case: EvalCase, answer_a: str, answer_b: str, judge: ModelSpec, params: RunParams
    ) -> tuple[str, str]:
        messages = build_pairwise_messages(
            case.prompt, answer_a, answer_b, reference=case.reference
        )
        completion = await self._llm.chat(judge, messages, params)
        return parse_pairwise_verdict(completion.text)
