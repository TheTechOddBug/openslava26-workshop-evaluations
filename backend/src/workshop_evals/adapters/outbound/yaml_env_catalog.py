"""Model catalogue with two layers.

`models.yaml` is the read-only base (shipped example, source="file"). Changes made from the
UI are written to a separate overlay file (source="user") that overrides the base by id.
The base file is never modified. Credentials are never stored here -- only `api_key_env`,
the *name* of the environment variable that holds a key.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from workshop_evals.domain.models import ModelRole, ModelSpec, Provider


def _to_spec(entry: dict, source: str) -> ModelSpec:
    return ModelSpec(
        id=entry["id"],
        display_name=entry.get("display_name", entry["id"]),
        provider=Provider(entry.get("provider", "openai_compat")),
        model_id=entry["model_id"],
        base_url=entry.get("base_url"),
        api_key_env=entry.get("api_key_env"),
        role=ModelRole(entry.get("role", "both")),
        supports_reasoning=bool(entry.get("supports_reasoning", False)),
        enabled=bool(entry.get("enabled", True)),
        source=source,
    )


def _read(path: Path, source: str) -> dict[str, ModelSpec]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {e["id"]: _to_spec(e, source) for e in data.get("models", [])}


class YamlModelCatalog:
    def __init__(self, yaml_path: Path, overlay_path: Path | None = None) -> None:
        self._yaml_path = Path(yaml_path)
        self._overlay_path = Path(overlay_path) if overlay_path else None
        self._file: dict[str, ModelSpec] = _read(self._yaml_path, "file")
        self._overlay: dict[str, ModelSpec] = (
            _read(self._overlay_path, "user") if self._overlay_path else {}
        )

    def _merged(self) -> dict[str, ModelSpec]:
        merged = dict(self._file)
        merged.update(self._overlay)  # overlay overrides / extends the base by id
        return merged

    # --- reads -------------------------------------------------------------
    def list_models(self) -> list[ModelSpec]:
        """Enabled models only -- what the candidate/judge selectors offer."""
        return [m for m in self._merged().values() if m.enabled]

    def all_models(self) -> list[ModelSpec]:
        """Every model including disabled ones -- for the management view."""
        return list(self._merged().values())

    def get_model(self, model_id: str) -> ModelSpec | None:
        return self._merged().get(model_id)

    # --- writes (persisted to the overlay) --------------------------------
    def upsert_model(self, spec: ModelSpec) -> ModelSpec:
        stored = spec.model_copy(update={"source": "user"})
        self._overlay[stored.id] = stored
        self._persist()
        return stored

    def remove_model(self, model_id: str) -> bool:
        """Delete a user-added model. Base (file) models cannot be deleted -- disable them."""
        if model_id in self._overlay and model_id not in self._file:
            del self._overlay[model_id]
            self._persist()
            return True
        return False

    def set_enabled(self, model_id: str, enabled: bool) -> ModelSpec | None:
        spec = self._merged().get(model_id)
        if spec is None:
            return None
        return self.upsert_model(spec.model_copy(update={"enabled": enabled}))

    def _persist(self) -> None:
        if self._overlay_path is None:
            return
        self._overlay_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "models": [
                m.model_dump(mode="json", exclude={"source"}) for m in self._overlay.values()
            ]
        }
        self._overlay_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
