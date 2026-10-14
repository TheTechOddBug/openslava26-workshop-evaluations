"""Core domain types shared across the evaluation engine.

A run is a matrix: cases x (model + params) x evaluators. A single cell couples one
case with one model response and the scores produced by one or more evaluators. Cases
deliberately carry several optional reference fields so the same prompt can be graded by
several mechanisms at once -- that divergence is the whole point of the workshop.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EvalMethod(StrEnum):
    """Evaluation mechanisms, ordered from the simplest to the most involved."""

    EXACT_MATCH = "exact_match"
    NUMERIC = "numeric"
    REGEX = "regex"
    JSON_SCHEMA = "json_schema"
    CODE_EXEC = "code_exec"
    SQL_EXEC = "sql_exec"
    BLEU = "bleu"
    ROUGE_L = "rouge_l"
    FUZZY = "fuzzy"
    LLM_JUDGE = "llm_judge"
    LLM_JUDGE_PAIRWISE = "llm_judge_pairwise"
    ENSEMBLE_JUDGE = "ensemble_judge"


class EvalTier(StrEnum):
    """Grouping used by the UI to present mechanisms as a progression."""

    DETERMINISTIC = "deterministic"
    SIMILARITY = "similarity"
    LLM_JUDGE = "llm_judge"
    ADVANCED = "advanced"


class Provider(StrEnum):
    OPENAI_COMPAT = "openai_compat"
    ANTHROPIC = "anthropic"
    FAKE = "fake"


class ModelRole(StrEnum):
    CANDIDATE = "candidate"
    JUDGE = "judge"
    BOTH = "both"


class ModelSpec(BaseModel):
    """A model the backend can call, local or remote."""

    id: str
    display_name: str
    provider: Provider
    model_id: str
    base_url: str | None = None
    api_key_env: str | None = None
    role: ModelRole = ModelRole.BOTH
    supports_reasoning: bool = False
    enabled: bool = True
    source: str | None = None  # "file" or "user"; set by the catalogue, not persisted from files

    def usable_as_judge(self) -> bool:
        return self.role in (ModelRole.JUDGE, ModelRole.BOTH)

    def usable_as_candidate(self) -> bool:
        return self.role in (ModelRole.CANDIDATE, ModelRole.BOTH)


class RunParams(BaseModel):
    """Inference parameters. Adapters translate and drop what a provider ignores."""

    temperature: float = 0.0
    max_tokens: int = 1024
    top_p: float | None = None
    top_k: int | None = None
    reasoning_effort: str | None = None  # low | medium | high | none
    seed: int | None = None
    stop: list[str] | None = None
    presence_penalty: float | None = None
    frequency_penalty: float | None = None


class EvalCase(BaseModel):
    """One test item. Optional reference fields decide which evaluators apply."""

    id: str
    category: str
    prompt: str
    default_method: EvalMethod
    reference: str | None = None  # accepted answer(s); '|' separates variants
    tests: str | None = None  # python asserts, for code execution
    sql_schema: str | None = None  # DDL + seed data, for sql execution
    json_schema: dict | None = None  # for structural validation
    rubric: list[str] | None = None  # criteria hints for a judge
    subcategory: str | None = None
    lang: str | None = None
    max_tokens: int | None = None
    enabled: bool = True
    source: str | None = None  # "file" or "user"; set by the repository, not persisted from files

    def available_fields(self) -> set[str]:
        """Reference fields actually present -- used to decide evaluator applicability."""
        present: set[str] = set()
        for name in ("reference", "tests", "sql_schema", "json_schema", "rubric"):
            if getattr(self, name) is not None:
                present.add(name)
        return present


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0


class Completion(BaseModel):
    """What an LLM client returns for a single call."""

    text: str
    usage: Usage = Field(default_factory=Usage)
    model_id: str | None = None
    error: str | None = None


class Score(BaseModel):
    """The outcome of applying one evaluator to one response."""

    method: EvalMethod
    value: float  # normalised to [0, 1]
    passed: bool | None = None
    detail: str = ""
    dimensions: dict[str, float] | None = None
    judge_model: str | None = None
    usage: Usage | None = None


class CellResult(BaseModel):
    """One cell of the result matrix."""

    case_id: str
    model_id: str
    label: str | None = None  # candidate label, distinguishes same model with different prompts
    params: RunParams
    response: str
    usage: Usage = Field(default_factory=Usage)
    scores: list[Score] = Field(default_factory=list)
    error: str | None = None


class AgreementVerdict(StrEnum):
    RELIABLE = "reliable"
    QUESTIONABLE = "questionable"
    UNRELIABLE = "unreliable"


class JudgeAgreement(BaseModel):
    """Meta-evaluation: how well one judge agrees with a stronger reference judge."""

    pearson: float
    spearman: float
    rank_agreement: float
    mae_overall: float
    mae_by_dimension: dict[str, float] = Field(default_factory=dict)
    verdict: AgreementVerdict
    sample_size: int


# Marks where a prompt override takes the case's own prompt.
PROMPT_PLACEHOLDER = "{prompt}"


class CandidateConfig(BaseModel):
    """One column of the matrix: a model, its params, and an optional prompt override.

    The prompt override lets a run compare a naive prompt against a refined one on the
    same case -- the "a better prompt lets a smaller model catch up" demonstration.
    """

    model_id: str
    params: RunParams = Field(default_factory=RunParams)
    prompt_override: str | None = None
    label: str | None = None

    def prompt_for(self, case_prompt: str) -> str:
        """The prompt this candidate sends for a case.

        Without an override it is the case's own prompt. Each ``{prompt}`` in the
        override is replaced by the case's prompt, so one refined template runs across
        many cases; an override without the placeholder is sent as written. Plain
        replacement, not ``str.format``, so braces elsewhere in the override are kept.
        """
        override = (self.prompt_override or "").strip()
        if not override:
            return case_prompt
        return override.replace(PROMPT_PLACEHOLDER, case_prompt)


class MatrixSpec(BaseModel):
    """The selection that defines a run: cases x candidates x evaluators."""

    case_ids: list[str]
    candidates: list[CandidateConfig]
    methods: list[EvalMethod]
    judge_model_id: str | None = None
    judge_params: RunParams = Field(default_factory=RunParams)


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Run(BaseModel):
    """A matrix run and its accumulating results."""

    id: str
    status: RunStatus = RunStatus.PENDING
    spec: MatrixSpec
    results: list[CellResult] = Field(default_factory=list)
    total_cells: int = 0
    completed_cells: int = 0
    error: str | None = None
    created_at: str | None = None


class PairwiseVerdict(StrEnum):
    A = "a"
    B = "b"
    TIE = "tie"


class PairwiseResult(BaseModel):
    """Outcome of asking a judge which of two answers is better.

    When positions are swapped and the winning answer changes, the judge preferred a
    position rather than an answer -- that is position bias, made visible.
    """

    case_id: str
    prompt: str
    model_a: str
    model_b: str
    response_a: str
    response_b: str
    verdict: PairwiseVerdict
    justification: str
    judge_model: str
    swapped_verdict: PairwiseVerdict | None = None
    position_bias: bool | None = None
    error: str | None = None


class JudgeScore(BaseModel):
    judge_model: str
    score: float
    dimensions: dict[str, float] = Field(default_factory=dict)


class EnsembleResult(BaseModel):
    """One response scored by several judges, plus their average and disagreement."""

    case_id: str
    response: str
    per_judge: list[JudgeScore] = Field(default_factory=list)
    ensemble_score: float = 0.0
    ensemble_dimensions: dict[str, float] = Field(default_factory=dict)
    spread: float = 0.0  # standard deviation of the per-judge scores
    error: str | None = None
