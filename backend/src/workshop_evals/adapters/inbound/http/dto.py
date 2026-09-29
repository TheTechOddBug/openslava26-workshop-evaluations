"""Request bodies for the HTTP API. Responses reuse the domain models directly."""

from __future__ import annotations

from pydantic import BaseModel, Field

from workshop_evals.domain.models import CandidateConfig, EvalCase, EvalMethod, RunParams


class EvaluateRequest(BaseModel):
    """Score a single response. Provide a dataset `case_id`, or an inline case."""

    model_id: str
    methods: list[EvalMethod]
    params: RunParams = Field(default_factory=RunParams)
    judge_model_id: str | None = None
    judge_params: RunParams = Field(default_factory=RunParams)

    # Either reference an existing case...
    case_id: str | None = None
    prompt_override: str | None = None

    # ...or describe one inline.
    prompt: str | None = None
    reference: str | None = None
    rubric: list[str] | None = None
    tests: str | None = None
    sql_schema: str | None = None

    def build_inline_case(self) -> EvalCase:
        if not self.prompt:
            raise ValueError("either 'case_id' or 'prompt' is required")
        return EvalCase(
            id="inline",
            category="inline",
            prompt=self.prompt,
            default_method=self.methods[0] if self.methods else EvalMethod.LLM_JUDGE,
            reference=self.reference,
            rubric=self.rubric,
            tests=self.tests,
            sql_schema=self.sql_schema,
        )

    def as_candidate(self) -> CandidateConfig:
        return CandidateConfig(
            model_id=self.model_id,
            params=self.params,
            prompt_override=self.prompt_override,
        )


class RunRequest(BaseModel):
    """Launch a matrix run: cases x candidates x methods."""

    case_ids: list[str]
    candidates: list[CandidateConfig]
    methods: list[EvalMethod]
    judge_model_id: str | None = None
    judge_params: RunParams = Field(default_factory=RunParams)


class JudgeAgreementRequest(BaseModel):
    """Re-judge a sample of a run's responses with a reference judge and measure agreement."""

    run_id: str
    reference_judge_model_id: str
    sample_size: int = 20
    judge_params: RunParams = Field(default_factory=RunParams)


class CompareRequest(BaseModel):
    """Pairwise A/B comparison of two candidates on one case, judged by a model."""

    model_a: str
    model_b: str
    judge_model_id: str
    params_a: RunParams = Field(default_factory=RunParams)
    params_b: RunParams = Field(default_factory=RunParams)
    prompt_override_a: str | None = None
    prompt_override_b: str | None = None
    judge_params: RunParams = Field(default_factory=RunParams)
    swap: bool = True
    # case source: a dataset case_id, or an inline prompt
    case_id: str | None = None
    prompt: str | None = None
    reference: str | None = None

    def candidate_a(self) -> CandidateConfig:
        return CandidateConfig(
            model_id=self.model_a, params=self.params_a, prompt_override=self.prompt_override_a
        )

    def candidate_b(self) -> CandidateConfig:
        return CandidateConfig(
            model_id=self.model_b, params=self.params_b, prompt_override=self.prompt_override_b
        )

    def build_inline_case(self) -> EvalCase:
        if not self.prompt:
            raise ValueError("either 'case_id' or 'prompt' is required")
        return EvalCase(
            id="inline",
            category="inline",
            prompt=self.prompt,
            default_method=EvalMethod.LLM_JUDGE_PAIRWISE,
            reference=self.reference,
        )


class DiscoverRequest(BaseModel):
    base_url: str


class EnabledRequest(BaseModel):
    enabled: bool


class CredentialRequest(BaseModel):
    env_name: str
    value: str


class EnsembleRequest(BaseModel):
    """Score one candidate response with several judges and average them."""

    model_id: str
    judge_model_ids: list[str]
    params: RunParams = Field(default_factory=RunParams)
    prompt_override: str | None = None
    judge_params: RunParams = Field(default_factory=RunParams)
    case_id: str | None = None
    prompt: str | None = None
    reference: str | None = None
    rubric: list[str] | None = None

    def candidate(self) -> CandidateConfig:
        return CandidateConfig(
            model_id=self.model_id, params=self.params, prompt_override=self.prompt_override
        )

    def build_inline_case(self) -> EvalCase:
        if not self.prompt:
            raise ValueError("either 'case_id' or 'prompt' is required")
        return EvalCase(
            id="inline",
            category="inline",
            prompt=self.prompt,
            default_method=EvalMethod.ENSEMBLE_JUDGE,
            reference=self.reference,
            rubric=self.rubric,
        )
