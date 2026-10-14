"""Each evaluator wraps a scoring function and returns a normalised Score."""

from __future__ import annotations

import pytest

from workshop_evals.adapters.outbound.fake_llm_client import FakeLLMClient
from workshop_evals.application.services.evaluator import EvaluationContext
from workshop_evals.application.services.evaluators import default_registry
from workshop_evals.domain.models import EvalCase, EvalMethod, ModelSpec, Provider


def _case(**kw) -> EvalCase:
    base = {"id": "c", "category": "test", "prompt": "p", "default_method": EvalMethod.EXACT_MATCH}
    base.update(kw)
    return EvalCase(**base)


REGISTRY = default_registry()


def _ev(method: EvalMethod):
    return REGISTRY.get(method)


async def test_exact_match():
    score = await _ev(EvalMethod.EXACT_MATCH).evaluate(
        _case(reference="positive"), "positive", EvaluationContext()
    )
    assert score.value == 1.0 and score.passed is True


async def test_numeric():
    score = await _ev(EvalMethod.NUMERIC).evaluate(
        _case(reference="42"), "The answer is 42", EvaluationContext()
    )
    assert score.value == 1.0


async def test_regex():
    score = await _ev(EvalMethod.REGEX).evaluate(
        _case(reference=r"\d{3}"), "code 123", EvaluationContext()
    )
    assert score.value == 1.0


async def test_json_schema():
    case = _case(json_schema={"type": "object", "required": ["a"]})
    score = await _ev(EvalMethod.JSON_SCHEMA).evaluate(case, '{"a": 1}', EvaluationContext())
    assert score.value == 1.0


async def test_code_exec():
    case = _case(tests="assert f(2) == 4")
    score = await _ev(EvalMethod.CODE_EXEC).evaluate(
        case, "def f(x):\n    return x * 2", EvaluationContext()
    )
    assert score.value == 1.0


async def test_sql_exec():
    case = _case(
        sql_schema="CREATE TABLE t(x INTEGER); INSERT INTO t VALUES (1),(2);",
        reference="SELECT x FROM t ORDER BY x",
    )
    score = await _ev(EvalMethod.SQL_EXEC).evaluate(
        case, "SELECT x FROM t ORDER BY x", EvaluationContext()
    )
    assert score.value == 1.0


@pytest.mark.parametrize("method", [EvalMethod.BLEU, EvalMethod.ROUGE_L, EvalMethod.FUZZY])
async def test_similarity_identical(method):
    score = await _ev(method).evaluate(
        _case(reference="the cat sat on the mat"), "the cat sat on the mat", EvaluationContext()
    )
    assert score.value == pytest.approx(1.0, abs=0.05)


async def test_sql_exec_invalid_reference_is_not_passed():
    case = _case(sql_schema="CREATE TABLE t(x INTEGER);", reference="NOT SQL")
    score = await _ev(EvalMethod.SQL_EXEC).evaluate(case, "SELECT x FROM t", EvaluationContext())
    assert score.passed is None  # can't be judged against a broken reference


async def test_llm_judge_uses_injected_client():
    judge_model = ModelSpec(
        id="j", display_name="Judge", provider=Provider.OPENAI_COMPAT, model_id="jm"
    )
    ctx = EvaluationContext(
        judge_client=FakeLLMClient.judge(
            {
                "correctness": 9,
                "completeness": 8,
                "robustness": 8,
                "clarity": 9,
                "efficiency": 8,
            }
        ),
        judge_model=judge_model,
    )
    score = await _ev(EvalMethod.LLM_JUDGE).evaluate(_case(rubric=["clear"]), "an answer", ctx)
    assert 0.0 < score.value <= 1.0
    assert score.dimensions is not None
    assert score.judge_model == "j"


async def test_llm_judge_without_client_is_inconclusive():
    score = await _ev(EvalMethod.LLM_JUDGE).evaluate(_case(), "answer", EvaluationContext())
    assert score.passed is None
    assert "no judge" in score.detail


async def test_llm_judge_empty_response_explains_reasoning_budget():
    judge_model = ModelSpec(
        id="j", display_name="Judge", provider=Provider.OPENAI_COMPAT, model_id="jm"
    )
    ctx = EvaluationContext(judge_client=FakeLLMClient(default="   "), judge_model=judge_model)
    score = await _ev(EvalMethod.LLM_JUDGE).evaluate(_case(rubric=["clear"]), "answer", ctx)
    assert score.passed is None
    assert "no content" in score.detail


async def test_llm_judge_does_not_grade_an_empty_candidate_response():
    judge_model = ModelSpec(
        id="j", display_name="Judge", provider=Provider.OPENAI_COMPAT, model_id="jm"
    )

    def must_not_be_called(*_args):
        raise AssertionError("the judge model must not be called for an empty response")

    ctx = EvaluationContext(
        judge_client=FakeLLMClient(handler=must_not_be_called), judge_model=judge_model
    )
    score = await _ev(EvalMethod.LLM_JUDGE).evaluate(_case(reference="negative"), "  \n", ctx)
    assert score.value == 0.0
    assert score.dimensions is None
    assert "empty response" in score.detail
