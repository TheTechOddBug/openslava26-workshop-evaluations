"""Unit tests for YamlModelCatalog — base + overlay merge, persistence."""

from __future__ import annotations

from pathlib import Path

import yaml

from workshop_evals.adapters.outbound.yaml_env_catalog import YamlModelCatalog
from workshop_evals.domain.models import ModelSpec, Provider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_base(path: Path, models: list[dict] | None = None) -> None:
    if models is None:
        models = [
            {
                "id": "base-model",
                "display_name": "Base Model",
                "provider": "openai_compat",
                "model_id": "base-v1",
                "enabled": True,
            }
        ]
    path.write_text(yaml.safe_dump({"models": models}), encoding="utf-8")


def _spec(model_id: str, *, display_name: str = "Some Model", enabled: bool = True) -> ModelSpec:
    return ModelSpec(
        id=model_id,
        display_name=display_name,
        provider=Provider.OPENAI_COMPAT,
        model_id=f"{model_id}-v1",
        enabled=enabled,
    )


# ---------------------------------------------------------------------------
# source field
# ---------------------------------------------------------------------------


def test_file_model_has_source_file(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    models = catalog.all_models()
    assert len(models) == 1
    assert models[0].source == "file"


# ---------------------------------------------------------------------------
# upsert_model
# ---------------------------------------------------------------------------


def test_upsert_writes_overlay_file(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    catalog.upsert_model(_spec("user-model"))

    assert overlay.exists()
    raw = yaml.safe_load(overlay.read_text(encoding="utf-8"))
    assert any(m["id"] == "user-model" for m in raw["models"])


def test_upsert_sets_source_user(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    result = catalog.upsert_model(_spec("user-model"))
    assert result.source == "user"


def test_upsert_model_shows_in_all_models_and_get_model(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    catalog.upsert_model(_spec("user-model"))

    all_ids = {m.id for m in catalog.all_models()}
    assert "user-model" in all_ids
    assert catalog.get_model("user-model") is not None
    assert catalog.get_model("user-model").source == "user"


def test_overlay_overrides_file_model_by_id(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    override = ModelSpec(
        id="base-model",
        display_name="Overridden",
        provider=Provider.OPENAI_COMPAT,
        model_id="base-v2",
    )
    catalog.upsert_model(override)

    merged = catalog.get_model("base-model")
    assert merged is not None
    assert merged.source == "user"
    assert merged.display_name == "Overridden"
    # not duplicated in the merged view
    assert [m.id for m in catalog.all_models()].count("base-model") == 1


# ---------------------------------------------------------------------------
# list_models / all_models — enabled filtering
# ---------------------------------------------------------------------------


def test_list_models_excludes_disabled_all_models_includes_it(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(
        base,
        models=[
            {"id": "on", "model_id": "on-v1", "provider": "openai_compat", "enabled": True},
            {"id": "off", "model_id": "off-v1", "provider": "openai_compat", "enabled": False},
        ],
    )
    catalog = YamlModelCatalog(base, overlay)

    enabled_ids = {m.id for m in catalog.list_models()}
    all_ids = {m.id for m in catalog.all_models()}

    assert "on" in enabled_ids
    assert "off" not in enabled_ids
    assert "off" in all_ids


# ---------------------------------------------------------------------------
# set_enabled
# ---------------------------------------------------------------------------


def test_set_enabled_false_hides_from_list_models(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    catalog.set_enabled("base-model", False)

    assert "base-model" not in {m.id for m in catalog.list_models()}
    assert "base-model" in {m.id for m in catalog.all_models()}


# ---------------------------------------------------------------------------
# remove_model
# ---------------------------------------------------------------------------


def test_remove_model_user_only_returns_true_and_removes(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    catalog.upsert_model(_spec("user-only"))
    assert catalog.get_model("user-only") is not None

    removed = catalog.remove_model("user-only")

    assert removed is True
    assert catalog.get_model("user-only") is None


def test_remove_model_base_returns_false_and_model_stays(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)
    catalog = YamlModelCatalog(base, overlay)

    removed = catalog.remove_model("base-model")

    assert removed is False
    assert catalog.get_model("base-model") is not None


# ---------------------------------------------------------------------------
# persistence — fresh catalog reads the same overlay
# ---------------------------------------------------------------------------


def test_fresh_catalog_reflects_persisted_changes(tmp_path):
    base, overlay = tmp_path / "m.yaml", tmp_path / "ov.yaml"
    _write_base(base)

    catalog1 = YamlModelCatalog(base, overlay)
    catalog1.upsert_model(_spec("persisted"))

    catalog2 = YamlModelCatalog(base, overlay)
    assert catalog2.get_model("persisted") is not None
    assert catalog2.get_model("persisted").source == "user"
