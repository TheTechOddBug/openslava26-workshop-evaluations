"""Unit tests for OpenAICompatClient — httpx calls mocked with respx."""

from __future__ import annotations

import json

import pytest
import respx
from httpx import Response

from workshop_evals.adapters.outbound.openai_compat_client import OpenAICompatClient
from workshop_evals.domain.models import ModelSpec, Provider, RunParams


def _model(
    base_url: str = "http://localhost:11434/v1", *, api_key_env: str | None = None
) -> ModelSpec:
    return ModelSpec(
        id="ollama-llama3",
        display_name="Llama 3 (Ollama)",
        provider=Provider.OPENAI_COMPAT,
        model_id="llama3",
        base_url=base_url,
        api_key_env=api_key_env,
    )


def _params(**kw) -> RunParams:
    return RunParams(**kw)


def _chat_response(content: str = "hello", prompt: int = 10, compl: int = 5) -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {
            "prompt_tokens": prompt,
            "completion_tokens": compl,
            "total_tokens": prompt + compl,
        },
    }


@respx.mock
async def test_successful_chat_returns_text_and_usage() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response("world", prompt=10, compl=5))
    )

    client = OpenAICompatClient()
    result = await client.chat(_model(), [{"role": "user", "content": "hi"}], _params())

    assert result.text == "world"
    assert result.error is None
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5
    assert result.usage.total_tokens == 15
    assert result.usage.latency_ms >= 0


@respx.mock
async def test_model_id_propagated() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response())
    )
    result = await OpenAICompatClient().chat(
        _model(), [{"role": "user", "content": "test"}], _params()
    )
    assert result.model_id == "llama3"


@respx.mock
async def test_optional_params_included_when_set() -> None:
    route = respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response())
    )

    await OpenAICompatClient().chat(
        _model(),
        [{"role": "user", "content": "test"}],
        _params(top_p=0.9, seed=42, stop=["END"], presence_penalty=0.1, frequency_penalty=0.2),
    )

    body = json.loads(route.calls[0].request.content)
    assert body["top_p"] == pytest.approx(0.9)
    assert body["seed"] == 42
    assert body["stop"] == ["END"]
    assert body["presence_penalty"] == pytest.approx(0.1)
    assert body["frequency_penalty"] == pytest.approx(0.2)


@respx.mock
async def test_optional_params_omitted_when_none() -> None:
    route = respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(200, json=_chat_response())
    )

    await OpenAICompatClient().chat(
        _model(),
        [{"role": "user", "content": "test"}],
        _params(),  # all optional fields default to None
    )

    body = json.loads(route.calls[0].request.content)
    for optional in ("top_p", "seed", "stop", "presence_penalty", "frequency_penalty"):
        assert optional not in body, f"unexpected key {optional!r} in request body"


@respx.mock
async def test_4xx_error_returned_immediately() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(400, text="bad request")
    )

    result = await OpenAICompatClient(max_retries=2).chat(
        _model(), [{"role": "user", "content": "x"}], _params()
    )

    assert result.text == ""
    assert result.error is not None
    assert "400" in result.error


@respx.mock
async def test_5xx_returns_error() -> None:
    respx.post("http://localhost:11434/v1/chat/completions").mock(
        return_value=Response(503, text="service unavailable")
    )

    # max_retries=0 means a single attempt — no sleep, test stays instant.
    result = await OpenAICompatClient(max_retries=0).chat(
        _model(), [{"role": "user", "content": "x"}], _params()
    )

    assert result.text == ""
    assert result.error is not None
    assert "503" in result.error


async def test_missing_base_url_returns_error_without_network() -> None:
    no_url_model = ModelSpec(
        id="no-url",
        display_name="No URL",
        provider=Provider.OPENAI_COMPAT,
        model_id="test",
        base_url=None,
    )
    result = await OpenAICompatClient().chat(
        no_url_model, [{"role": "user", "content": "hi"}], _params()
    )
    assert result.text == ""
    assert result.error is not None
