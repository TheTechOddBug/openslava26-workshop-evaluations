"""Dataset repository with two layers.

`data/datasets/*.jsonl` is the read-only base (the shipped workshop cases, source="file"),
one file per category. Cases added or edited from the UI are written to a separate overlay
file (source="user") that overrides the base by id. The base files are never modified.
"""

from __future__ import annotations

import json
from pathlib import Path

from workshop_evals.domain.models import EvalCase, EvalMethod

# Source datasets label methods with their own vocabulary; map it to the domain enum.
_METHOD_ALIASES: dict[str, EvalMethod] = {
    "exact_match": EvalMethod.EXACT_MATCH,
    "numeric": EvalMethod.NUMERIC,
    "regex": EvalMethod.REGEX,
    "json_schema": EvalMethod.JSON_SCHEMA,
    "unit_test": EvalMethod.CODE_EXEC,
    "code_exec": EvalMethod.CODE_EXEC,
    "sql": EvalMethod.SQL_EXEC,
    "sql_exec": EvalMethod.SQL_EXEC,
    "judge": EvalMethod.LLM_JUDGE,
    "llm_judge": EvalMethod.LLM_JUDGE,
}


def _to_case(raw: dict, fallback_category: str) -> EvalCase:
    method_key = str(raw.get("eval_method", "llm_judge"))
    default_method = _METHOD_ALIASES.get(method_key, EvalMethod.LLM_JUDGE)
    reference = raw.get("reference")
    if reference is not None and not isinstance(reference, str):
        reference = str(reference)  # numeric references (e.g. reasoning answers) arrive as numbers
    return EvalCase(
        id=raw["id"],
        category=raw.get("category") or fallback_category,
        prompt=raw["prompt"],
        default_method=default_method,
        reference=reference,
        tests=raw.get("tests"),
        sql_schema=raw.get("schema") or raw.get("sql_schema"),
        json_schema=raw.get("json_schema"),
        rubric=raw.get("rubric"),
        subcategory=raw.get("subcategory"),
        lang=raw.get("lang"),
        max_tokens=raw.get("max_tokens"),
        enabled=bool(raw.get("enabled", True)),
        source="file",
    )


class JsonlDatasetRepository:
    def __init__(self, datasets_dir: Path, overlay_path: Path | None = None) -> None:
        self._datasets_dir = Path(datasets_dir)
        self._overlay_path = Path(overlay_path) if overlay_path else None
        self._base: dict[str, EvalCase] = {}
        self._load_base(self._datasets_dir)
        self._overlay: dict[str, EvalCase] = self._load_overlay()

    def _load_base(self, datasets_dir: Path) -> None:
        for path in sorted(datasets_dir.glob("*.jsonl")):
            category = path.stem
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    case = _to_case(json.loads(line), category)
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    raise ValueError(f"{path.name}:{lineno}: {exc}") from exc
                self._base[case.id] = case

    def _load_overlay(self) -> dict[str, EvalCase]:
        if self._overlay_path is None or not self._overlay_path.exists():
            return {}
        data = json.loads(self._overlay_path.read_text(encoding="utf-8")) or {}
        overlay: dict[str, EvalCase] = {}
        for raw in data.get("cases", []):
            case = EvalCase.model_validate({**raw, "source": "user"})
            overlay[case.id] = case
        return overlay

    def _merged(self) -> dict[str, EvalCase]:
        merged = dict(self._base)
        merged.update(self._overlay)  # overlay overrides / extends the base by id
        return merged

    # --- reads -------------------------------------------------------------
    def list_categories(self) -> list[str]:
        """Categories with at least one enabled case -- what the selectors offer."""
        return sorted({c.category for c in self._merged().values() if c.enabled})

    def get_cases(self, category: str) -> list[EvalCase]:
        """Enabled cases in a category, base order first."""
        return [c for c in self._merged().values() if c.enabled and c.category == category]

    def get_case(self, case_id: str) -> EvalCase | None:
        return self._merged().get(case_id)

    def all_cases(self) -> list[EvalCase]:
        """Every case including disabled ones -- for the management view."""
        return list(self._merged().values())

    # --- writes (persisted to the overlay) --------------------------------
    def upsert_case(self, case: EvalCase) -> EvalCase:
        stored = case.model_copy(update={"source": "user"})
        self._overlay[stored.id] = stored
        self._persist()
        return stored

    def remove_case(self, case_id: str) -> bool:
        """Delete a user-added case. Base (file) cases cannot be deleted -- disable them."""
        if case_id in self._overlay and case_id not in self._base:
            del self._overlay[case_id]
            self._persist()
            return True
        return False

    def set_enabled(self, case_id: str, enabled: bool) -> EvalCase | None:
        case = self._merged().get(case_id)
        if case is None:
            return None
        return self.upsert_case(case.model_copy(update={"enabled": enabled}))

    def _persist(self) -> None:
        if self._overlay_path is None:
            return
        self._overlay_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cases": [c.model_dump(mode="json", exclude={"source"}) for c in self._overlay.values()]
        }
        self._overlay_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
