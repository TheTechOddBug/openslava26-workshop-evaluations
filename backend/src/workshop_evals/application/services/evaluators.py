"""Concrete evaluators, one per mechanism, plus a factory that registers them all.

Each class adapts a pure scoring function (or a judge call) to the common Evaluator
interface. Deterministic evaluators ignore the context; the judge uses the injected client.
"""

from __future__ import annotations

from workshop_evals.application.services.evaluator import (
    EvaluationContext,
    EvaluatorRegistry,
    EvaluatorSpec,
)
from workshop_evals.domain.models import EvalCase, EvalMethod, EvalTier, Score
from workshop_evals.domain.scoring import (
    code_exec,
    deterministic,
    judge_rubric,
    similarity,
    sql_exec,
)


class ExactMatchEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.EXACT_MATCH,
        tier=EvalTier.DETERMINISTIC,
        label="Exact match",
        description="Checks the answer against accepted reference variants.",
        required_fields=frozenset({"reference"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = deterministic.exact_match(response, case.reference or "")
        return Score(method=self.spec.method, value=value, passed=value >= 1.0, detail=detail)


class NumericEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.NUMERIC,
        tier=EvalTier.DETERMINISTIC,
        label="Numeric tolerance",
        description="Extracts the final number and compares within a tolerance.",
        required_fields=frozenset({"reference"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = deterministic.numeric(response, case.reference or "")
        return Score(method=self.spec.method, value=value, passed=value >= 1.0, detail=detail)


class RegexEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.REGEX,
        tier=EvalTier.DETERMINISTIC,
        label="Regex",
        description="Matches the response against a regular expression.",
        required_fields=frozenset({"reference"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = deterministic.regex_match(response, case.reference or "")
        return Score(method=self.spec.method, value=value, passed=value >= 1.0, detail=detail)


class JsonSchemaEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.JSON_SCHEMA,
        tier=EvalTier.DETERMINISTIC,
        label="JSON schema",
        description="Validates that the response is JSON matching a schema.",
        required_fields=frozenset({"json_schema"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = deterministic.json_schema_match(response, case.json_schema or {})
        return Score(method=self.spec.method, value=value, passed=value >= 1.0, detail=detail)


class CodeExecEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.CODE_EXEC,
        tier=EvalTier.DETERMINISTIC,
        label="Code execution",
        description="Runs the generated code against unit tests.",
        required_fields=frozenset({"tests"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        code = code_exec.extract_code(response)
        value, detail = code_exec.run_code(code, case.tests or "")
        return Score(method=self.spec.method, value=value, passed=value >= 1.0, detail=detail)


class SqlExecEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.SQL_EXEC,
        tier=EvalTier.DETERMINISTIC,
        label="SQL execution",
        description="Runs the query against a schema and compares result sets.",
        required_fields=frozenset({"reference", "sql_schema"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        query = sql_exec.extract_sql(response)
        value, detail = sql_exec.run_sql(query, case.reference or "", case.sql_schema or "")
        if value is None:
            return Score(method=self.spec.method, value=0.0, passed=None, detail=detail)
        return Score(method=self.spec.method, value=value, passed=value >= 1.0, detail=detail)


class BleuEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.BLEU,
        tier=EvalTier.SIMILARITY,
        label="BLEU",
        description="N-gram overlap with a reference (translation-style metric).",
        required_fields=frozenset({"reference"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = similarity.bleu(response, case.reference or "")
        return Score(method=self.spec.method, value=value, detail=detail)


class RougeLEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.ROUGE_L,
        tier=EvalTier.SIMILARITY,
        label="ROUGE-L",
        description="Longest-common-subsequence overlap with a reference.",
        required_fields=frozenset({"reference"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = similarity.rouge_l(response, case.reference or "")
        return Score(method=self.spec.method, value=value, detail=detail)


class FuzzyEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.FUZZY,
        tier=EvalTier.SIMILARITY,
        label="Fuzzy ratio",
        description="Character-level similarity ratio with a reference.",
        required_fields=frozenset({"reference"}),
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        value, detail = similarity.fuzzy(response, case.reference or "")
        return Score(method=self.spec.method, value=value, detail=detail)


class LlmJudgeEvaluator:
    spec = EvaluatorSpec(
        method=EvalMethod.LLM_JUDGE,
        tier=EvalTier.LLM_JUDGE,
        label="LLM as judge",
        description="A model scores the response on a five-dimension rubric.",
        required_fields=frozenset(),  # reference-free capable: applies to any case
        needs_judge=True,
    )

    async def evaluate(self, case: EvalCase, response: str, ctx: EvaluationContext) -> Score:
        if ctx.judge_client is None or ctx.judge_model is None:
            return Score(
                method=self.spec.method,
                value=0.0,
                passed=None,
                detail="no judge model selected",
            )
        messages = judge_rubric.build_judge_messages(
            prompt=case.prompt, response=response, reference=case.reference, rubric=case.rubric
        )
        completion = await ctx.judge_client.chat(ctx.judge_model, messages, ctx.judge_params)
        if completion.error:
            return Score(method=self.spec.method, value=0.0, passed=None, detail=completion.error)
        if not completion.text.strip():
            return Score(
                method=self.spec.method,
                value=0.0,
                passed=None,
                detail=(
                    "The judge returned no content. A reasoning model can spend its whole token "
                    "budget thinking and never emit the verdict — pick a non-reasoning judge or "
                    "raise max tokens."
                ),
            )
        value, justification, dims = judge_rubric.parse_judge_response(
            completion.text, case.category
        )
        return Score(
            method=self.spec.method,
            value=value,
            detail=justification,
            dimensions=dims,
            judge_model=ctx.judge_model.id,
            usage=completion.usage,
        )


def default_registry() -> EvaluatorRegistry:
    registry = EvaluatorRegistry()
    for evaluator in (
        ExactMatchEvaluator(),
        NumericEvaluator(),
        RegexEvaluator(),
        JsonSchemaEvaluator(),
        CodeExecEvaluator(),
        SqlExecEvaluator(),
        BleuEvaluator(),
        RougeLEvaluator(),
        FuzzyEvaluator(),
        LlmJudgeEvaluator(),
    ):
        registry.register(evaluator)
    return registry
