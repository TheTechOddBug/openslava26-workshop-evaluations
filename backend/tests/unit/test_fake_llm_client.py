"""Unit tests for FakeLLMClient."""

from __future__ import annotations

import json

import pytest

from workshop_evals.adapters.outbound.fake_llm_client import FakeLLMClient
from workshop_evals.domain.models import ModelSpec, Provider, RunParams


def _model(model_id: str = "fake") -> ModelSpec:
    return ModelSpec(
        id=model_id,
        display_name="Fake",
        provider=Provider.FAKE,
        model_id=model_id,
    )


def _params() -> RunParams:
    return RunParams()


def _user(content: str) -> dict:
    return {"role": "user", "content": content}


async def test_responses_dict_routes_by_substring() -> None:
    client = FakeLLMClient(
        responses={
            "capital of France": "Paris",
            "capital of Germany": "Berlin",
        }
    )
    model = _model()

    paris = await client.chat(model, [_user("What is the capital of France?")], _params())
    assert paris.text == "Paris"

    berlin = await client.chat(model, [_user("capital of Germany please")], _params())
    assert berlin.text == "Berlin"


async def test_default_returned_when_no_key_matches() -> None:
    client = FakeLLMClient(responses={"xyz": "nope"}, default="fallback answer")
    result = await client.chat(_model(), [_user("something completely different")], _params())
    assert result.text == "fallback answer"


async def test_empty_responses_and_no_default_gives_empty_string() -> None:
    client = FakeLLMClient()
    result = await client.chat(_model(), [_user("hello")], _params())
    assert result.text == ""


async def test_handler_overrides_responses_dict() -> None:
    def handler(model, messages, params):
        return f"handled:{model.model_id}"

    client = FakeLLMClient(
        responses={"anything": "from responses"},
        handler=handler,
        default="unused",
    )
    result = await client.chat(_model("mymodel"), [_user("anything")], _params())
    assert result.text == "handled:mymodel"


async def test_model_id_propagated_to_completion() -> None:
    client = FakeLLMClient(default="ok")
    result = await client.chat(_model("gpt-test"), [_user("hi")], _params())
    assert result.model_id == "gpt-test"


async def test_usage_fields_are_minimal_placeholders() -> None:
    client = FakeLLMClient(default="reply")
    result = await client.chat(_model(), [_user("hello")], _params())
    assert result.usage.prompt_tokens == 1
    assert result.usage.completion_tokens == 1
    assert result.usage.total_tokens == 2


async def test_judge_json_is_parseable() -> None:
    scores = {
        "relevance": 0.8,
        "accuracy": 0.9,
        "clarity": 0.7,
        "completeness": 0.8,
        "helpfulness": 0.75,
    }
    client = FakeLLMClient.judge(scores, justification="All five criteria look good.")

    result = await client.chat(_model(), [_user("evaluate this response")], _params())
    parsed = json.loads(result.text)

    for dim, val in scores.items():
        assert parsed[dim] == pytest.approx(val)
    assert parsed["justification"] == "All five criteria look good."


async def test_judge_default_justification_is_ok() -> None:
    client = FakeLLMClient.judge({"quality": 1.0})
    result = await client.chat(_model(), [_user("any prompt")], _params())
    parsed = json.loads(result.text)
    assert parsed["justification"] == "ok"


async def test_judge_json_contains_all_score_keys() -> None:
    scores = {"a": 0.5, "b": 0.6, "c": 0.7, "d": 0.8, "e": 0.9}
    client = FakeLLMClient.judge(scores)
    result = await client.chat(_model(), [_user("judge me")], _params())
    parsed = json.loads(result.text)
    for key in scores:
        assert key in parsed
