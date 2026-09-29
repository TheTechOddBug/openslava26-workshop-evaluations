"""Opt-in tests against a live local model via Ollama.

These are skipped unless Ollama is reachable with the expected model pulled, so the default
suite stays offline and free. Run them explicitly with ``pytest -m real_llm``.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from workshop_evals.adapters.inbound.http.app import build_container, create_app
from workshop_evals.adapters.outbound.openai_compat_client import OpenAICompatClient
from workshop_evals.domain.models import ModelSpec, Provider, RunParams

pytestmark = pytest.mark.real_llm

_OLLAMA_BASE = "http://localhost:11434/v1"
_TINY_MODEL = "qwen2.5:0.5b"
_CATALOG_MODEL = "qwen3-4b"  # id in data/models.yaml -> model_id qwen3:4b


def _available(model_id: str) -> bool:
    try:
        r = httpx.get("http://localhost:11434/api/tags", timeout=3, trust_env=False)
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return any(model_id in name for name in names)
    except Exception:
        return False


@pytest.mark.skipif(not _available(_TINY_MODEL), reason=f"{_TINY_MODEL} not pulled in Ollama")
async def test_openai_compat_client_against_live_model():
    client = OpenAICompatClient()
    model = ModelSpec(
        id="local",
        display_name="local",
        provider=Provider.OPENAI_COMPAT,
        model_id=_TINY_MODEL,
        base_url=_OLLAMA_BASE,
    )
    completion = await client.chat(
        model,
        [{"role": "user", "content": "Reply with a single word."}],
        RunParams(max_tokens=32, temperature=0.0),
    )
    assert completion.error is None
    assert completion.text.strip() != ""
    assert completion.usage.total_tokens > 0


@pytest.mark.skipif(not _available("qwen3:4b"), reason="qwen3:4b not pulled in Ollama")
def test_api_evaluate_against_live_model():
    client = TestClient(create_app(build_container()))
    body = {
        "model_id": _CATALOG_MODEL,
        "methods": ["exact_match", "fuzzy"],
        "prompt": "Classify the sentiment as one word (positive, negative or neutral): "
        "'This is the best purchase I have made all year.'",
        "reference": "positive",
    }
    r = client.post("/api/evaluate", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["error"] is None
    assert data["response"].strip() != ""
    assert len(data["scores"]) == 2
    for score in data["scores"]:
        assert 0.0 <= score["value"] <= 1.0
