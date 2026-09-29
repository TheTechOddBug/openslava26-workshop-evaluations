"""Unit tests for DatasetManagementService."""

from __future__ import annotations

import json
from pathlib import Path

from workshop_evals.adapters.outbound.jsonl_dataset_repo import JsonlDatasetRepository
from workshop_evals.application.services.dataset_management import DatasetManagementService
from workshop_evals.domain.models import EvalCase, EvalMethod

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _write_base(datasets_dir: Path) -> None:
    """Write a minimal JSONL base with cases in two categories."""
    l01 = {"id": "l-01", "prompt": "Letter after A?", "eval_method": "exact_match", "reference": "B"}  # noqa: E501
    l02 = {"id": "l-02", "prompt": "Spell cat.", "eval_method": "exact_match", "reference": "cat"}
    (datasets_dir / "letters.jsonl").write_text(
        "\n".join([json.dumps(l01), json.dumps(l02)]),
        encoding="utf-8",
    )
    m01 = {"id": "m-01", "prompt": "2 + 2?", "eval_method": "exact_match", "reference": "4"}
    (datasets_dir / "math.jsonl").write_text(json.dumps(m01), encoding="utf-8")


def _make_repo(tmp_path: Path) -> JsonlDatasetRepository:
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    overlay = tmp_path / "ds_overlay.json"
    return JsonlDatasetRepository(datasets_dir, overlay)


def _make_service(repo: JsonlDatasetRepository) -> DatasetManagementService:
    return DatasetManagementService(repo)


def _new_case(case_id: str = "u-new", *, category: str = "letters") -> EvalCase:
    return EvalCase(
        id=case_id,
        category=category,
        prompt="A user-added prompt",
        default_method=EvalMethod.LLM_JUDGE,
    )


# ---------------------------------------------------------------------------
# list_all
# ---------------------------------------------------------------------------


def test_list_all_returns_all_cases_including_disabled(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    result = svc.list_all()
    # 3 base cases, all enabled
    assert len(result) == 3


def test_list_all_includes_source_and_enabled_fields(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    result = svc.list_all()
    for item in result:
        assert "source" in item
        assert "enabled" in item


def test_list_all_base_cases_have_source_file(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    result = svc.list_all()
    assert all(item["source"] == "file" for item in result)


def test_list_all_includes_freshly_upserted_user_case(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    svc.upsert(_new_case("u-fresh"))

    ids = {r["id"] for r in svc.list_all()}
    assert "u-fresh" in ids


def test_list_all_user_case_has_source_user(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    svc.upsert(_new_case("u-src"))

    user_cases = [r for r in svc.list_all() if r["id"] == "u-src"]
    assert len(user_cases) == 1
    assert user_cases[0]["source"] == "user"


# ---------------------------------------------------------------------------
# upsert
# ---------------------------------------------------------------------------


def test_upsert_returns_dict_with_source_user(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    result = svc.upsert(_new_case("u-upsert"))

    assert isinstance(result, dict)
    assert result["source"] == "user"
    assert result["id"] == "u-upsert"


def test_upsert_case_appears_in_list_all(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    svc.upsert(_new_case("u-appear"))

    ids = {r["id"] for r in svc.list_all()}
    assert "u-appear" in ids


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


def test_remove_user_case_returns_true(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    svc.upsert(_new_case("u-rm"))
    removed = svc.remove("u-rm")

    assert removed is True


def test_remove_base_case_returns_false(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    removed = svc.remove("l-01")

    assert removed is False


# ---------------------------------------------------------------------------
# set_enabled
# ---------------------------------------------------------------------------


def test_set_enabled_false_returns_dict_with_enabled_false(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    result = svc.set_enabled("l-01", False)

    assert isinstance(result, dict)
    assert result["enabled"] is False


def test_set_enabled_true_re_enables(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    svc.set_enabled("l-01", False)
    result = svc.set_enabled("l-01", True)

    assert result is not None
    assert result["enabled"] is True


def test_set_enabled_unknown_id_returns_none(tmp_path):
    repo = _make_repo(tmp_path)
    svc = _make_service(repo)

    result = svc.set_enabled("ghost-id", False)

    assert result is None
