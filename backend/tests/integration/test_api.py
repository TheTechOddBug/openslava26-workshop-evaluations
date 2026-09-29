"""End-to-end API tests through the FastAPI app with a fake model client."""

from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient
from httpx import Response

from workshop_evals.adapters.inbound.http.app import build_container, create_app
from workshop_evals.adapters.outbound.fake_llm_client import FakeLLMClient
from workshop_evals.config.settings import get_settings


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_list_models(client):
    r = client.get("/api/catalog/models")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()}
    assert "qwen3-4b" in ids
    assert len(ids) == 7


def test_list_evaluators(client):
    r = client.get("/api/catalog/evaluators")
    methods = {e["method"] for e in r.json()}
    assert {"exact_match", "llm_judge", "code_exec", "sql_exec", "bleu"} <= methods
    judge = next(e for e in r.json() if e["method"] == "llm_judge")
    assert judge["needs_judge"] is True
    assert judge["tier"] == "llm_judge"


def test_list_datasets(client):
    r = client.get("/api/catalog/datasets")
    cats = {d["category"] for d in r.json()}
    assert "sentiment_classification" in cats
    assert len(cats) == 14


def test_list_cases_in_category(client):
    r = client.get("/api/catalog/datasets/sentiment_classification/cases")
    assert r.status_code == 200
    assert len(r.json()) == 15


def test_applicable_methods_show_divergence(client):
    # A sentiment case carries both a reference and a rubric, so a deterministic
    # check and an LLM judge both apply -- the core teaching point.
    r = client.get("/api/catalog/cases/sent-01/methods")
    methods = set(r.json())
    assert "exact_match" in methods
    assert "llm_judge" in methods


def test_applicable_methods_unknown_case(client):
    assert client.get("/api/catalog/cases/does-not-exist/methods").status_code == 404


def test_evaluate_exact_match_inline(client):
    body = {
        "model_id": "qwen3-4b",
        "methods": ["exact_match"],
        "prompt": "Classify the sentiment: I love this product.",
        "reference": "positive",
    }
    r = client.post("/api/evaluate", json=body)
    assert r.status_code == 200
    score = r.json()["scores"][0]
    assert score["method"] == "exact_match"
    assert score["value"] == 1.0
    assert score["passed"] is True


def test_evaluate_llm_judge_inline(client):
    body = {
        "model_id": "qwen3-4b",
        "methods": ["llm_judge"],
        "prompt": "Explain recursion to a beginner.",
        "rubric": ["clear", "correct"],
        "judge_model_id": "gpt-4o",
    }
    r = client.post("/api/evaluate", json=body)
    score = r.json()["scores"][0]
    assert score["method"] == "llm_judge"
    assert score["dimensions"] is not None
    assert 0.0 <= score["value"] <= 1.0
    assert score["judge_model"] == "gpt-4o"


def test_evaluate_same_prompt_two_mechanisms(client):
    body = {
        "model_id": "qwen3-4b",
        "methods": ["exact_match", "llm_judge"],
        "prompt": "Classify the sentiment: I love this product.",
        "reference": "positive",
        "rubric": ["accurate label"],
        "judge_model_id": "gpt-4o",
    }
    r = client.post("/api/evaluate", json=body)
    methods = {s["method"] for s in r.json()["scores"]}
    assert methods == {"exact_match", "llm_judge"}


def test_evaluate_self_evaluation_is_flagged(client):
    body = {
        "model_id": "gpt-4o",
        "methods": ["llm_judge"],
        "prompt": "Anything",
        "rubric": ["x"],
        "judge_model_id": "gpt-4o",
    }
    r = client.post("/api/evaluate", json=body)
    assert "self-evaluation" in r.json()["scores"][0]["detail"]


def test_evaluate_code_execution():
    fake = FakeLLMClient(default="```python\ndef add(a, b):\n    return a + b\n```")
    local = TestClient(create_app(build_container(llm_client=fake)))
    body = {
        "model_id": "qwen3-4b",
        "methods": ["code_exec"],
        "prompt": "Write add(a, b).",
        "tests": "assert add(1, 2) == 3",
    }
    r = local.post("/api/evaluate", json=body)
    score = r.json()["scores"][0]
    assert score["method"] == "code_exec"
    assert score["value"] == 1.0


def test_evaluate_requires_case_or_prompt(client):
    body = {"model_id": "qwen3-4b", "methods": ["exact_match"]}
    assert client.post("/api/evaluate", json=body).status_code == 422


def test_evaluate_unknown_case(client):
    body = {"model_id": "qwen3-4b", "methods": ["exact_match"], "case_id": "nope"}
    assert client.post("/api/evaluate", json=body).status_code == 404


def test_evaluate_unknown_model_reports_error(client):
    body = {"model_id": "ghost", "methods": ["exact_match"], "prompt": "x", "reference": "x"}
    r = client.post("/api/evaluate", json=body)
    assert r.status_code == 200
    assert r.json()["error"] is not None


def test_run_matrix(client):
    body = {
        "case_ids": ["sent-01", "sent-02"],
        "candidates": [{"model_id": "qwen3-4b"}, {"model_id": "llama3-2-3b"}],
        "methods": ["exact_match"],
    }
    r = client.post("/api/runs", json=body)
    assert r.status_code == 202  # accepted; runs in the background
    run = r.json()
    assert run["total_cells"] == 4

    fetched = client.get(f"/api/runs/{run['id']}").json()
    assert fetched["status"] == "completed"
    assert fetched["completed_cells"] == 4
    assert len(fetched["results"]) == 4


def test_run_matrix_skips_unknown_case(client):
    body = {
        "case_ids": ["sent-01", "ghost-case"],
        "candidates": [{"model_id": "qwen3-4b"}],
        "methods": ["exact_match"],
    }
    posted = client.post("/api/runs", json=body)
    assert posted.status_code == 202
    run = client.get(f"/api/runs/{posted.json()['id']}").json()
    assert run["status"] == "completed"
    assert run["completed_cells"] == 2
    assert len(run["results"]) == 1  # the unknown case produced no cell


def test_get_unknown_run(client):
    assert client.get("/api/runs/nope").status_code == 404


def test_judge_agreement_flow(client):
    posted = client.post(
        "/api/runs",
        json={
            "case_ids": ["sent-01", "sent-02"],
            "candidates": [{"model_id": "qwen3-4b"}],
            "methods": ["llm_judge"],
            "judge_model_id": "gpt-4o",
        },
    )
    assert posted.status_code == 202
    run_id = posted.json()["id"]
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "completed"

    r = client.post(
        "/api/judge-agreement",
        json={
            "run_id": run_id,
            "reference_judge_model_id": "claude-sonnet-4-5",
            "sample_size": 10,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["sample_size"] == 2
    assert data["verdict"] in {"reliable", "questionable", "unreliable"}
    assert set(data["mae_by_dimension"]) <= {
        "correctness",
        "completeness",
        "robustness",
        "clarity",
        "efficiency",
    }


def test_judge_agreement_unknown_run(client):
    r = client.post(
        "/api/judge-agreement",
        json={"run_id": "nope", "reference_judge_model_id": "gpt-4o"},
    )
    assert r.status_code == 404


def test_judge_agreement_requires_judge_scores(client):
    run_id = client.post(
        "/api/runs",
        json={
            "case_ids": ["sent-01"],
            "candidates": [{"model_id": "qwen3-4b"}],
            "methods": ["exact_match"],
        },
    ).json()["id"]
    r = client.post(
        "/api/judge-agreement",
        json={"run_id": run_id, "reference_judge_model_id": "gpt-4o"},
    )
    assert r.status_code == 422


def test_compare_pairwise_detects_position_bias(client):
    body = {
        "case_id": "sent-01",
        "model_a": "qwen3-4b",
        "model_b": "llama3-2-3b",
        "judge_model_id": "gpt-4o",
        "swap": True,
    }
    r = client.post("/api/compare", json=body)
    assert r.status_code == 200
    data = r.json()
    # the fake judge always prefers position A, so the winner flips when positions swap
    assert data["verdict"] == "a"
    assert data["swapped_verdict"] == "b"
    assert data["position_bias"] is True
    assert data["response_a"] and data["response_b"]


def test_compare_without_swap_has_no_bias_flag(client):
    body = {
        "prompt": "Say hello.",
        "model_a": "qwen3-4b",
        "model_b": "llama3-2-3b",
        "judge_model_id": "gpt-4o",
        "swap": False,
    }
    r = client.post("/api/compare", json=body)
    assert r.status_code == 200
    assert r.json()["position_bias"] is None


def test_compare_unknown_model_reports_error(client):
    body = {"prompt": "x", "model_a": "ghost", "model_b": "llama3-2-3b", "judge_model_id": "gpt-4o"}
    r = client.post("/api/compare", json=body)
    assert r.status_code == 200
    assert r.json()["error"] is not None


def test_compare_requires_case_or_prompt(client):
    body = {"model_a": "qwen3-4b", "model_b": "llama3-2-3b", "judge_model_id": "gpt-4o"}
    assert client.post("/api/compare", json=body).status_code == 422


def test_ensemble_judge_averages_multiple_judges(client):
    body = {
        "case_id": "sent-01",
        "model_id": "qwen3-4b",
        "judge_model_ids": ["gpt-4o", "claude-sonnet-4-5"],
    }
    r = client.post("/api/ensemble-judge", json=body)
    assert r.status_code == 200
    data = r.json()
    assert len(data["per_judge"]) == 2
    assert data["spread"] == 0.0  # both fake judges agree exactly
    assert 0.0 <= data["ensemble_score"] <= 1.0
    assert set(data["ensemble_dimensions"]) == {
        "correctness",
        "completeness",
        "robustness",
        "clarity",
        "efficiency",
    }


def test_ensemble_requires_at_least_one_judge(client):
    body = {"case_id": "sent-01", "model_id": "qwen3-4b", "judge_model_ids": []}
    assert client.post("/api/ensemble-judge", json=body).status_code == 422


def test_ensemble_unknown_model_reports_error(client):
    body = {"prompt": "x", "model_id": "ghost", "judge_model_ids": ["gpt-4o"]}
    r = client.post("/api/ensemble-judge", json=body)
    assert r.status_code == 200
    assert r.json()["error"] is not None


# ---------------------------------------------------------------------------
# Model-management integration tests
# These use a separate fixture so they never touch the real overlay file.
# ---------------------------------------------------------------------------

_NEW_MODEL = {
    "id": "mgmt-test-model",
    "display_name": "Mgmt Test Model",
    "provider": "openai_compat",
    "model_id": "mgmt-test-v1",
}

_BASE_MODEL_ID = "qwen3-4b"  # must exist in data/models.yaml


@pytest.fixture
def mgmt_client(tmp_path) -> TestClient:
    """TestClient backed by an isolated tmp overlay — does not touch the real runtime file."""
    settings = get_settings().model_copy(update={"models_overlay": tmp_path / "ov.yaml"})
    container = build_container(settings=settings, llm_client=FakeLLMClient(default="positive"))
    return TestClient(create_app(container))


def test_manage_endpoint_returns_source_and_key_detected(mgmt_client):
    r = mgmt_client.get("/api/catalog/manage")
    assert r.status_code == 200
    models = r.json()
    assert len(models) > 0
    first = models[0]
    assert "source" in first
    assert "key_detected" in first


def test_upsert_model_then_appears_in_enabled_list(mgmt_client):
    r = mgmt_client.post("/api/catalog/models", json=_NEW_MODEL)
    assert r.status_code == 200
    assert r.json()["source"] == "user"

    enabled = mgmt_client.get("/api/catalog/models").json()
    assert any(m["id"] == "mgmt-test-model" for m in enabled)


def test_delete_user_model_returns_removed_true(mgmt_client):
    mgmt_client.post("/api/catalog/models", json=_NEW_MODEL)
    r = mgmt_client.delete(f"/api/catalog/models/{_NEW_MODEL['id']}")
    assert r.status_code == 200
    assert r.json() == {"removed": True}


def test_delete_base_model_returns_400(mgmt_client):
    r = mgmt_client.delete(f"/api/catalog/models/{_BASE_MODEL_ID}")
    assert r.status_code == 400


def test_set_enabled_false_hides_from_list_but_keeps_in_manage(mgmt_client):
    mgmt_client.post("/api/catalog/models", json=_NEW_MODEL)

    r = mgmt_client.post(
        f"/api/catalog/models/{_NEW_MODEL['id']}/enabled", json={"enabled": False}
    )
    assert r.status_code == 200

    enabled_ids = {m["id"] for m in mgmt_client.get("/api/catalog/models").json()}
    assert "mgmt-test-model" not in enabled_ids

    manage_ids = {m["id"] for m in mgmt_client.get("/api/catalog/manage").json()}
    assert "mgmt-test-model" in manage_ids


def test_set_credential_valid_api_key(mgmt_client):
    import os

    r = mgmt_client.post(
        "/api/catalog/credentials", json={"env_name": "OPENAI_API_KEY", "value": "sk-x"}
    )
    assert r.status_code == 200
    assert r.json()["detected"] is True
    # cleanup: remove the injected key so it doesn't leak into other tests
    os.environ.pop("OPENAI_API_KEY", None)


def test_set_credential_system_var_returns_422(mgmt_client):
    r = mgmt_client.post(
        "/api/catalog/credentials", json={"env_name": "HOME", "value": "evil"}
    )
    assert r.status_code == 422


@respx.mock
def test_discover_via_api(mgmt_client):
    base_url = "http://localhost:11434/v1"
    respx.get(f"{base_url}/models").mock(
        return_value=Response(200, json={"data": [{"id": "model-a"}, {"id": "model-b"}]})
    )
    r = mgmt_client.post("/api/catalog/discover", json={"base_url": base_url})
    assert r.status_code == 200
    data = r.json()
    assert "models" in data
    assert "already_added" in data
    assert set(data["models"]) == {"model-a", "model-b"}


# ---------------------------------------------------------------------------
# Dataset-management integration tests
# These use a separate fixture so they never touch the real overlay file.
# ---------------------------------------------------------------------------

_NEW_CASE = {
    "id": "ds-mgmt-test-case",
    "category": "ds_mgmt_test_cat",
    "prompt": "A test prompt for dataset management.",
    "default_method": "llm_judge",
    "reference": "expected answer",
}

_BASE_CASE_CATEGORY = "sentiment_classification"


@pytest.fixture
def ds_mgmt_client(tmp_path) -> TestClient:
    """TestClient with an isolated tmp datasets overlay — never touches the real runtime file."""
    settings = get_settings().model_copy(
        update={
            "models_overlay": tmp_path / "ov.yaml",
            "datasets_overlay": tmp_path / "ds.json",
        }
    )
    container = build_container(settings=settings, llm_client=FakeLLMClient(default="positive"))
    return TestClient(create_app(container))


def test_manage_datasets_endpoint_returns_source_and_enabled(ds_mgmt_client):
    r = ds_mgmt_client.get("/api/catalog/datasets/manage")
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) > 0
    first = cases[0]
    assert "source" in first
    assert "enabled" in first


def test_upsert_case_then_appears_in_category_and_catalog(ds_mgmt_client):
    r = ds_mgmt_client.post("/api/catalog/cases", json=_NEW_CASE)
    assert r.status_code == 200
    assert r.json()["source"] == "user"

    cases = ds_mgmt_client.get(f"/api/catalog/datasets/{_NEW_CASE['category']}/cases").json()
    assert any(c["id"] == _NEW_CASE["id"] for c in cases)

    cats = {d["category"] for d in ds_mgmt_client.get("/api/catalog/datasets").json()}
    assert _NEW_CASE["category"] in cats


def test_delete_user_case_returns_removed_true(ds_mgmt_client):
    ds_mgmt_client.post("/api/catalog/cases", json=_NEW_CASE)
    r = ds_mgmt_client.delete(f"/api/catalog/cases/{_NEW_CASE['id']}")
    assert r.status_code == 200
    assert r.json() == {"removed": True}


def test_delete_base_case_returns_400(ds_mgmt_client):
    # Grab an id from a known base category
    cases = ds_mgmt_client.get(f"/api/catalog/datasets/{_BASE_CASE_CATEGORY}/cases").json()
    assert len(cases) > 0
    base_case_id = cases[0]["id"]

    r = ds_mgmt_client.delete(f"/api/catalog/cases/{base_case_id}")
    assert r.status_code == 400


def test_set_case_enabled_false_hides_from_cases_but_shows_in_manage(ds_mgmt_client):
    ds_mgmt_client.post("/api/catalog/cases", json=_NEW_CASE)

    r = ds_mgmt_client.post(
        f"/api/catalog/cases/{_NEW_CASE['id']}/enabled", json={"enabled": False}
    )
    assert r.status_code == 200

    cat = _NEW_CASE["category"]
    case_ids = {c["id"] for c in ds_mgmt_client.get(f"/api/catalog/datasets/{cat}/cases").json()}
    assert _NEW_CASE["id"] not in case_ids

    manage_ids = {c["id"] for c in ds_mgmt_client.get("/api/catalog/datasets/manage").json()}
    assert _NEW_CASE["id"] in manage_ids


def test_set_case_enabled_unknown_id_returns_404(ds_mgmt_client):
    r = ds_mgmt_client.post("/api/catalog/cases/no-such-case/enabled", json={"enabled": False})
    assert r.status_code == 404
