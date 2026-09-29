"""Anthropic Messages API adapter.

Replaces the legacy `claude -p` subprocess approach with a real SDK call
against AsyncAnthropic. Supports extended thinking when the model declares
supports_reasoning and a reasoning_effort is requested.
"""

from __future__ import annotations

import os
from typing import Any

from anthropic import AsyncAnthropic

from workshop_evals.application.ports.llm_client import Message
from workshop_evals.domain.models import Completion, ModelSpec, RunParams, Usage

# Map reasoning_effort labels to approximate thinking-token budgets.
_THINKING_BUDGET: dict[str, int] = {
    "low": 1024,
    "medium": 8000,
    "high": 20000,
}


class AnthropicClient:
    """LLM client using the Anthropic Messages API."""

    def __init__(self) -> None:
        pass

    async def chat(
        self,
        model: ModelSpec,
        messages: list[Message],
        params: RunParams,
    ) -> Completion:
        api_key: str | None = None
        if model.api_key_env:
            api_key = os.environ.get(model.api_key_env)

        # Extract any leading system turn(s); Anthropic takes these separately.
        system_parts: list[str] = []
        remaining: list[Message] = []
        for msg in messages:
            if msg["role"] == "system" and not remaining:
                system_parts.append(msg["content"])
            else:
                remaining.append(msg)
        system_text = "\n\n".join(system_parts) if system_parts else None

        kwargs: dict[str, Any] = {
            "model": model.model_id,
            "max_tokens": params.max_tokens,
            "temperature": params.temperature,
            "messages": remaining,
        }
        if system_text:
            kwargs["system"] = system_text
        if params.top_p is not None:
            kwargs["top_p"] = params.top_p
        if params.stop is not None:
            kwargs["stop_sequences"] = params.stop

        # Best-effort extended thinking — degraded gracefully if the model or
        # SDK version doesn't support it.
        if (
            model.supports_reasoning
            and params.reasoning_effort
            and params.reasoning_effort != "none"
        ):
            budget = _THINKING_BUDGET.get(params.reasoning_effort, 8000)
            try:
                kwargs["thinking"] = {"type": "enabled", "budget_tokens": budget}
                # Anthropic requires temperature=1 when thinking is enabled.
                kwargs.pop("temperature", None)
            except Exception:
                pass

        client = AsyncAnthropic(api_key=api_key)
        try:
            resp = await client.messages.create(**kwargs)
        except Exception as exc:
            return Completion(text="", error=f"{type(exc).__name__}: {exc}")

        # Collect text blocks; thinking blocks carry reasoning traces, not the answer.
        text_parts: list[str] = []
        for block in resp.content:
            if getattr(block, "type", None) == "text":
                text_parts.append(block.text)
        text = "".join(text_parts)

        usage = Usage(
            prompt_tokens=resp.usage.input_tokens,
            completion_tokens=resp.usage.output_tokens,
            total_tokens=resp.usage.input_tokens + resp.usage.output_tokens,
        )
        return Completion(text=text, usage=usage, model_id=model.model_id)
