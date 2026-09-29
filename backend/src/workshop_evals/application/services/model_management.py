"""Manage the model catalogue from the UI: discover, add, edit, enable, remove.

Credentials are never persisted here. A user may set a key for the running session, which
lands in the process environment (never on disk) and is read by the provider adapters
through the model's `api_key_env`.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable

from workshop_evals.application.ports.model_catalog import ModelCatalogPort
from workshop_evals.domain.models import ModelSpec

Discoverer = Callable[[str], Awaitable[list[str]]]


def sanitize_id(model_id: str) -> str:
    """Turn a provider model id (e.g. 'qwen3:4b') into a catalogue id ('qwen3-4b')."""
    out = "".join(c if c.isalnum() else "-" for c in model_id.lower())
    return "-".join(part for part in out.split("-") if part) or "model"


class ModelManagementService:
    def __init__(self, catalog: ModelCatalogPort, discover: Discoverer) -> None:
        self._catalog = catalog
        self._discover = discover

    def list_all(self) -> list[dict]:
        return [self._with_key_status(m) for m in self._catalog.all_models()]

    def upsert(self, spec: ModelSpec) -> dict:
        return self._with_key_status(self._catalog.upsert_model(spec))

    def remove(self, model_id: str) -> bool:
        return self._catalog.remove_model(model_id)

    def set_enabled(self, model_id: str, enabled: bool) -> dict | None:
        updated = self._catalog.set_enabled(model_id, enabled)
        return self._with_key_status(updated) if updated else None

    async def discover(self, base_url: str) -> dict:
        found = await self._discover(base_url)
        known = {m.model_id for m in self._catalog.all_models()}
        return {"models": found, "already_added": sorted(known.intersection(found))}

    def set_credential(self, env_name: str, value: str) -> None:
        if not self._is_allowed_env(env_name):
            raise ValueError(
                f"'{env_name}' is not an accepted key variable "
                "(must end in _API_KEY or be referenced by a model)"
            )
        os.environ[env_name] = value  # session only; never written to disk

    def credential_status(self, env_name: str) -> bool:
        return bool(os.environ.get(env_name))

    def _is_allowed_env(self, name: str) -> bool:
        referenced = {m.api_key_env for m in self._catalog.all_models() if m.api_key_env}
        return name.endswith("_API_KEY") or name in referenced

    def _with_key_status(self, model: ModelSpec) -> dict:
        data = model.model_dump(mode="json")
        data["key_detected"] = (
            True if not model.api_key_env else bool(os.environ.get(model.api_key_env))
        )
        return data
