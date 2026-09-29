"""Fake LLM client for tests — no network, deterministic."""

from __future__ import annotations

import json
from collections.abc import Callable

from workshop_evals.application.ports.llm_client import Message
from workshop_evals.domain.models import Completion, ModelSpec, RunParams, Usage


class FakeLLMClient:
    """Drop-in replacement for any real LLM client in unit tests.

    Resolution order per ``chat`` call:
      1. ``handler(model, messages, params)`` — full control over the reply.
      2. ``responses`` dict — first key that is a substring of the last user
         message wins.
      3. ``default`` — returned verbatim when nothing else matched.
    """

    def __init__(
        self,
        *,
        responses: dict[str, str] | None = None,
        handler: Callable[[ModelSpec, list[Message], RunParams], str] | None = None,
        default: str = "",
    ) -> None:
        self._responses = responses or {}
        self._handler = handler
        self._default = default

    async def chat(
        self,
        model: ModelSpec,
        messages: list[Message],
        params: RunParams,
    ) -> Completion:
        if self._handler is not None:
            reply = self._handler(model, messages, params)
        else:
            last_user = next(
                (m["content"] for m in reversed(messages) if m.get("role") == "user"),
                "",
            )
            reply = self._default
            for key, value in self._responses.items():
                if key in last_user:
                    reply = value
                    break

        usage = Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        return Completion(text=reply, usage=usage, model_id=model.model_id)

    @classmethod
    def judge(cls, scores: dict[str, float], justification: str = "ok") -> FakeLLMClient:
        """Return a FakeLLMClient whose default reply is a valid judge JSON string.

        The JSON contains every key from *scores* plus a ``justification`` field,
        so any LLM-judge scorer that expects that shape can parse it without
        making a real API call.

        Example::

            client = FakeLLMClient.judge(
                {"relevance": 0.8, "accuracy": 0.9, "clarity": 0.7,
                 "completeness": 0.8, "helpfulness": 0.75},
                justification="All five criteria met.",
            )
        """
        payload = {**scores, "justification": justification}
        return cls(default=json.dumps(payload))
