"""Tests for the Anthropic adapter with the SDK client replaced by a fake."""

from __future__ import annotations

import workshop_evals.adapters.outbound.anthropic_client as mod
from workshop_evals.domain.models import ModelSpec, Provider, RunParams


class _Block:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _Usage:
    input_tokens = 3
    output_tokens = 5


class _Resp:
    def __init__(self, text: str) -> None:
        self.content = [_Block(text)]
        self.usage = _Usage()


class _Messages:
    def __init__(self, capture: dict, raise_exc: bool) -> None:
        self._capture = capture
        self._raise = raise_exc

    async def create(self, **kwargs):
        self._capture.clear()
        self._capture.update(kwargs)
        if self._raise:
            raise RuntimeError("boom")
        return _Resp("hello from claude")


def _fake_anthropic(capture: dict, raise_exc: bool = False):
    class _Fake:
        def __init__(self, api_key=None):
            self.messages = _Messages(capture, raise_exc)

    return _Fake


def _model(**kw) -> ModelSpec:
    base = {
        "id": "a",
        "display_name": "Claude",
        "provider": Provider.ANTHROPIC,
        "model_id": "claude-x",
        "api_key_env": "ANTHROPIC_API_KEY",
    }
    base.update(kw)
    return ModelSpec(**base)


async def test_anthropic_success(monkeypatch):
    capture: dict = {}
    monkeypatch.setattr(mod, "AsyncAnthropic", _fake_anthropic(capture))
    client = mod.AnthropicClient()
    messages = [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
    out = await client.chat(_model(), messages, RunParams(max_tokens=100))
    assert out.text == "hello from claude"
    assert out.error is None
    assert out.usage.total_tokens == 8
    assert capture["system"] == "sys"  # system turn pulled out separately
    assert all(m["role"] != "system" for m in capture["messages"])


async def test_anthropic_error_is_captured(monkeypatch):
    monkeypatch.setattr(mod, "AsyncAnthropic", _fake_anthropic({}, raise_exc=True))
    out = await mod.AnthropicClient().chat(
        _model(), [{"role": "user", "content": "hi"}], RunParams()
    )
    assert out.text == ""
    assert "boom" in out.error


async def test_anthropic_enables_thinking(monkeypatch):
    capture: dict = {}
    monkeypatch.setattr(mod, "AsyncAnthropic", _fake_anthropic(capture))
    model = _model(supports_reasoning=True)
    await mod.AnthropicClient().chat(
        model, [{"role": "user", "content": "hi"}], RunParams(reasoning_effort="high")
    )
    assert capture["thinking"]["type"] == "enabled"
    assert "temperature" not in capture  # dropped when thinking is on
