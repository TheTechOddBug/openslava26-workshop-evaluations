"""Fixtures for API-level tests. A fake LLM client keeps them fast, free and offline."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from workshop_evals.adapters.inbound.http.app import build_container, create_app
from workshop_evals.adapters.outbound.fake_llm_client import FakeLLMClient
from workshop_evals.domain.scoring.judge_rubric import JUDGE_SYSTEM, PAIRWISE_SYSTEM

_JUDGE_JSON = json.dumps(
    {
        "correctness": 8,
        "completeness": 8,
        "robustness": 7,
        "clarity": 9,
        "efficiency": 7,
        "justification": "meets the criteria",
    }
)
_PAIRWISE_JSON = json.dumps({"winner": "A", "justification": "Answer A is clearer."})


def _handler(model, messages, params) -> str:
    """Return judge JSON for judge calls, a fixed sentiment label otherwise."""
    system = messages[0]["content"] if messages and messages[0].get("role") == "system" else ""
    if system == PAIRWISE_SYSTEM:
        return _PAIRWISE_JSON
    if system == JUDGE_SYSTEM:
        return _JUDGE_JSON
    return "positive"


@pytest.fixture
def fake() -> FakeLLMClient:
    return FakeLLMClient(handler=_handler)


@pytest.fixture
def client(fake) -> TestClient:
    return TestClient(create_app(build_container(llm_client=fake)))
