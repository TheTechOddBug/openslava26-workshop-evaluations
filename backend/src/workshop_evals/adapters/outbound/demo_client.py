"""A canned LLM client for offline demo mode and deterministic tests.

It answers candidate prompts with a short fixed reply and judge prompts with a valid
rubric JSON, so the whole application works with no local model and no API key.
"""

from __future__ import annotations

import json

from workshop_evals.adapters.outbound.fake_llm_client import FakeLLMClient
from workshop_evals.application.ports.llm_client import Message
from workshop_evals.domain.models import ModelSpec, RunParams
from workshop_evals.domain.scoring.judge_rubric import JUDGE_SYSTEM, PAIRWISE_SYSTEM

_JUDGE_REPLY = json.dumps(
    {
        "correctness": 8,
        "completeness": 7,
        "robustness": 7,
        "clarity": 8,
        "efficiency": 7,
        "justification": "A reasonable answer that covers the main points.",
    }
)


_PAIRWISE_REPLY = json.dumps({"winner": "A", "justification": "Answer A reads more clearly."})


def _handler(model: ModelSpec, messages: list[Message], params: RunParams) -> str:
    system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
    if system == PAIRWISE_SYSTEM:
        # Always prefers the answer in position A -- a deliberately position-biased demo.
        return _PAIRWISE_REPLY
    if system == JUDGE_SYSTEM:
        return _JUDGE_REPLY
    return "positive"


def make_demo_client() -> FakeLLMClient:
    return FakeLLMClient(handler=_handler)
