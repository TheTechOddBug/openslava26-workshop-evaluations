"""Unit tests for ModelManagementService and sanitize_id."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from workshop_evals.adapters.outbound.yaml_env_catalog import YamlModelCatalog
from workshop_evals.application.services.model_management import ModelManagementService, sanitize_id

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


_TEST_ENV_VARS = ("SOME_PROVIDER_API_KEY", "CUSTOM_KEY_NAME", "RETURN_TEST_API_KEY")


@pytest.fixture(autouse=True)
def _clean_test_env_vars():
    """Ensure test-specific env vars are absent before and after each test."""
    for var in _TEST_ENV_VARS:
        os.environ.pop(var, None)
    yield
    for var in _TEST_ENV_VARS:
        os.environ.pop(var, None)


def _write_base(path: Path, *, api_key_env: str | None = None) -> None:
    entry: dict = {
        "id": "local-model",
        "display_name": "Local Model",
        "provider": "openai_compat",
        "model_id": "local-v1",
        "enabled": True,
    }
    if api_key_env:
        entry["api_key_env"] = api_key_env
    path.write_text(yaml.safe_dump({"models": [entry]}), encoding="utf-8")


def _make_catalog(tmp_path: Path, *, api_key_env: str | None = None) -> YamlModelCatalog:
    base = tmp_path / "models.yaml"
    overlay = tmp_path / "overlay.yaml"
    _write_base(base, api_key_env=api_key_env)
    return YamlModelCatalog(base, overlay)


def _make_service(
    catalog: YamlModelCatalog, discoverer=None
) -> ModelManagementService:
    async def _noop(url: str) -> list[str]:
        return []

    return ModelManagementService(catalog, discoverer or _noop)


# ---------------------------------------------------------------------------
# key_detected
# ---------------------------------------------------------------------------


def test_list_all_local_model_key_detected_true(tmp_path):
    """A model with no api_key_env needs no key; key_detected is always True."""
    svc = _make_service(_make_catalog(tmp_path))

    result = svc.list_all()
    assert len(result) == 1
    assert result[0]["key_detected"] is True


def test_list_all_key_detected_false_when_env_unset(tmp_path):
    svc = _make_service(_make_catalog(tmp_path, api_key_env="SOME_PROVIDER_API_KEY"))

    result = svc.list_all()
    assert result[0]["key_detected"] is False


def test_list_all_key_detected_true_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("SOME_PROVIDER_API_KEY", "sk-test")
    svc = _make_service(_make_catalog(tmp_path, api_key_env="SOME_PROVIDER_API_KEY"))

    result = svc.list_all()
    assert result[0]["key_detected"] is True


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------


async def test_discover_returns_models_and_already_added(tmp_path):
    """already_added is the intersection of discovered ids with catalog model_ids."""
    catalog = _make_catalog(tmp_path)  # has model_id="local-v1"

    async def _fake(url: str) -> list[str]:
        return ["local-v1", "brand-new"]

    svc = ModelManagementService(catalog, _fake)
    result = await svc.discover("http://localhost:11434/v1")

    assert set(result["models"]) == {"local-v1", "brand-new"}
    assert result["already_added"] == ["local-v1"]


async def test_discover_empty_when_no_overlap(tmp_path):
    async def _fake(url: str) -> list[str]:
        return ["totally-unknown-model"]

    svc = ModelManagementService(_make_catalog(tmp_path), _fake)
    result = await svc.discover("http://localhost:11434/v1")

    assert result["already_added"] == []
    assert "totally-unknown-model" in result["models"]


# ---------------------------------------------------------------------------
# set_credential
# ---------------------------------------------------------------------------


def test_set_credential_accepts_api_key_suffix(tmp_path):
    svc = _make_service(_make_catalog(tmp_path))
    svc.set_credential("SOME_PROVIDER_API_KEY", "sk-abc")
    assert os.environ.get("SOME_PROVIDER_API_KEY") == "sk-abc"


def test_set_credential_accepts_name_referenced_by_model(tmp_path):
    svc = _make_service(_make_catalog(tmp_path, api_key_env="CUSTOM_KEY_NAME"))
    svc.set_credential("CUSTOM_KEY_NAME", "secret")
    assert os.environ.get("CUSTOM_KEY_NAME") == "secret"


def test_set_credential_returns_none(tmp_path):
    svc = _make_service(_make_catalog(tmp_path))
    result = svc.set_credential("RETURN_TEST_API_KEY", "hidden")
    assert result is None


def test_set_credential_raises_for_system_env(tmp_path):
    svc = _make_service(_make_catalog(tmp_path))
    with pytest.raises(ValueError):
        svc.set_credential("HOME", "injected")


def test_set_credential_raises_for_unreferenced_non_api_key(tmp_path):
    """A name that neither ends in _API_KEY nor is referenced by any model is rejected."""
    svc = _make_service(_make_catalog(tmp_path))
    with pytest.raises(ValueError):
        svc.set_credential("RANDOM_VAR", "value")


# ---------------------------------------------------------------------------
# sanitize_id
# ---------------------------------------------------------------------------


def test_sanitize_id_colon_separator():
    assert sanitize_id("qwen3:4b") == "qwen3-4b"


def test_sanitize_id_multiple_colons():
    assert sanitize_id("my::model") == "my-model"


def test_sanitize_id_trailing_separator():
    assert sanitize_id("model:") == "model"


def test_sanitize_id_mixed_separators():
    assert sanitize_id("my::model--v2") == "my-model-v2"


def test_sanitize_id_uppercase_lowercased():
    assert sanitize_id("GPT-4O") == "gpt-4o"


def test_sanitize_id_all_separators_fallback():
    # Degenerate input of only non-alnum chars falls back to "model"
    assert sanitize_id("::--") == "model"
