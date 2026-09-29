"""Unit tests for JsonlDatasetRepository — base + overlay merge, persistence."""

from __future__ import annotations

import json
from pathlib import Path

from workshop_evals.adapters.outbound.jsonl_dataset_repo import JsonlDatasetRepository
from workshop_evals.domain.models import EvalCase, EvalMethod

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_base(datasets_dir: Path) -> None:
    """Write two small JSONL dataset files into *datasets_dir*."""
    # cat_a: 2 cases — one with a numeric reference (coercion check), one plain
    a01 = {"id": "a-01", "prompt": "What is 6 * 7?", "eval_method": "exact_match", "reference": 42}
    a02 = {"id": "a-02", "prompt": "Summarise the plot.", "eval_method": "llm_judge"}
    (datasets_dir / "cat_a.jsonl").write_text(
        "\n".join([json.dumps(a01), json.dumps(a02)]),
        encoding="utf-8",
    )
    # cat_b: 1 case
    b01 = {"id": "b-01", "prompt": "Classify.", "eval_method": "judge", "reference": "positive"}
    (datasets_dir / "cat_b.jsonl").write_text(json.dumps(b01), encoding="utf-8")


def _case(
    case_id: str,
    *,
    category: str = "cat_a",
    prompt: str = "A prompt",
    method: EvalMethod = EvalMethod.LLM_JUDGE,
    reference: str | None = None,
    enabled: bool = True,
) -> EvalCase:
    return EvalCase(
        id=case_id,
        category=category,
        prompt=prompt,
        default_method=method,
        reference=reference,
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# source field — base vs overlay
# ---------------------------------------------------------------------------


def test_base_cases_have_source_file(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir)

    cases = repo.all_cases()
    assert len(cases) == 3
    assert all(c.source == "file" for c in cases)


# ---------------------------------------------------------------------------
# list_categories / get_cases — basic reads
# ---------------------------------------------------------------------------


def test_list_categories_returns_all_categories_with_enabled_cases(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir)

    cats = repo.list_categories()
    assert sorted(cats) == ["cat_a", "cat_b"]


def test_get_cases_returns_enabled_cases_in_that_category(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir)

    cases = repo.get_cases("cat_a")
    assert len(cases) == 2
    assert all(c.category == "cat_a" for c in cases)
    assert all(c.enabled for c in cases)


def test_get_cases_other_category_not_included(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir)

    ids = {c.id for c in repo.get_cases("cat_b")}
    assert ids == {"b-01"}
    assert "a-01" not in ids


# ---------------------------------------------------------------------------
# numeric reference coercion
# ---------------------------------------------------------------------------


def test_numeric_reference_coerced_to_str(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir)

    case = repo.get_case("a-01")
    assert case is not None
    assert isinstance(case.reference, str)
    assert case.reference == "42"


# ---------------------------------------------------------------------------
# upsert_case — overlay writes
# ---------------------------------------------------------------------------


def test_upsert_case_creates_overlay_file(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    overlay = tmp_path / "overlay.json"
    repo = JsonlDatasetRepository(datasets_dir, overlay)

    repo.upsert_case(_case("u-01"))

    assert overlay.exists()
    data = json.loads(overlay.read_text(encoding="utf-8"))
    assert any(c["id"] == "u-01" for c in data["cases"])


def test_upsert_case_sets_source_user(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    result = repo.upsert_case(_case("u-01"))
    assert result.source == "user"


def test_upsert_case_appears_in_all_cases_and_get_case(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    repo.upsert_case(_case("u-01"))

    all_ids = {c.id for c in repo.all_cases()}
    assert "u-01" in all_ids
    assert repo.get_case("u-01") is not None
    assert repo.get_case("u-01").source == "user"


# ---------------------------------------------------------------------------
# overlay overrides base by id
# ---------------------------------------------------------------------------


def test_overlay_overrides_base_case_by_id(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    override = _case("a-01", prompt="Overridden prompt", method=EvalMethod.EXACT_MATCH)
    repo.upsert_case(override)

    merged = repo.get_case("a-01")
    assert merged is not None
    assert merged.source == "user"
    assert merged.prompt == "Overridden prompt"
    # should not be duplicated
    assert [c.id for c in repo.all_cases()].count("a-01") == 1


# ---------------------------------------------------------------------------
# set_enabled — disabled cases
# ---------------------------------------------------------------------------


def test_set_enabled_false_hides_from_get_cases_and_list_categories(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    repo.set_enabled("b-01", False)

    assert "cat_b" not in repo.list_categories()
    assert repo.get_cases("cat_b") == []


def test_disabled_case_still_appears_in_all_cases_and_get_case(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    repo.set_enabled("b-01", False)

    all_ids = {c.id for c in repo.all_cases()}
    assert "b-01" in all_ids

    case = repo.get_case("b-01")
    assert case is not None
    assert case.enabled is False


def test_category_disappears_from_list_when_only_case_disabled(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    # cat_b has only b-01
    repo.set_enabled("b-01", False)

    assert "cat_b" not in repo.list_categories()


def test_set_enabled_returns_none_for_unknown_id(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    assert repo.set_enabled("nonexistent", False) is None


# ---------------------------------------------------------------------------
# remove_case
# ---------------------------------------------------------------------------


def test_remove_user_case_returns_true_and_removes(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    repo.upsert_case(_case("u-del"))
    assert repo.get_case("u-del") is not None

    removed = repo.remove_case("u-del")

    assert removed is True
    assert repo.get_case("u-del") is None


def test_remove_base_case_returns_false_and_case_stays(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    repo = JsonlDatasetRepository(datasets_dir, tmp_path / "ov.json")

    removed = repo.remove_case("a-01")

    assert removed is False
    assert repo.get_case("a-01") is not None


# ---------------------------------------------------------------------------
# persistence — fresh repository reads the same overlay
# ---------------------------------------------------------------------------


def test_fresh_repo_reflects_persisted_changes(tmp_path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    _write_base(datasets_dir)
    overlay = tmp_path / "ov.json"

    repo1 = JsonlDatasetRepository(datasets_dir, overlay)
    repo1.upsert_case(_case("persisted-01"))

    repo2 = JsonlDatasetRepository(datasets_dir, overlay)
    assert repo2.get_case("persisted-01") is not None
    assert repo2.get_case("persisted-01").source == "user"
