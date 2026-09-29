"""Driven port for the catalogue of configured models."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from workshop_evals.domain.models import ModelSpec


@runtime_checkable
class ModelCatalogPort(Protocol):
    def list_models(self) -> list[ModelSpec]:
        """Return enabled models (candidates and judges) for the selectors."""
        ...

    def all_models(self) -> list[ModelSpec]:
        """Return every model, including disabled ones, for management."""
        ...

    def get_model(self, model_id: str) -> ModelSpec | None:
        """Return a model by id, or None if unknown."""
        ...

    def upsert_model(self, spec: ModelSpec) -> ModelSpec:
        """Add or replace a user-managed model; persisted to the overlay."""
        ...

    def remove_model(self, model_id: str) -> bool:
        """Delete a user-added model. Returns False for base (file) models."""
        ...

    def set_enabled(self, model_id: str, enabled: bool) -> ModelSpec | None:
        """Enable or disable a model, or None if unknown."""
        ...
