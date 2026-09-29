"""Driven port for talking to a language model.

Every provider (local OpenAI-compatible servers, OpenAI, Azure, Anthropic, or a fake used
in tests) is reached through this single interface, so the rest of the code never depends
on a concrete SDK.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from workshop_evals.domain.models import Completion, ModelSpec, RunParams

Message = dict[str, str]  # {"role": "system" | "user" | "assistant", "content": "..."}


@runtime_checkable
class LLMClientPort(Protocol):
    async def chat(
        self,
        model: ModelSpec,
        messages: list[Message],
        params: RunParams,
    ) -> Completion:
        """Send a chat completion request and return the model's reply."""
        ...
