"""Application settings, read from the environment (prefix WORKSHOP_EVALS_) or defaults."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WORKSHOP_EVALS_", env_file=".env", extra="ignore")

    datasets_dir: Path = _BACKEND_ROOT / "data" / "datasets"
    models_yaml: Path = _BACKEND_ROOT / "data" / "models.yaml"
    # Where UI-managed models persist. Fixed and independent of models_yaml, so switching
    # the base catalogue does not strand the overlay. Gitignored.
    models_overlay: Path = _BACKEND_ROOT / "data" / "models.runtime.yaml"
    # Where UI-managed dataset cases persist. Gitignored overlay over the read-only JSONL base.
    datasets_overlay: Path = _BACKEND_ROOT / "data" / "datasets.runtime.json"

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Offline demo mode: answer with a canned client instead of calling real models.
    # Handy for a run-through without local models or API keys, and for deterministic tests.
    fake_llm: bool = False

    # Guard rails
    code_exec_timeout: float = 10.0
    judge_budget_cap_usd: float = 5.0

    # Optional default judge model id (must exist in the catalogue)
    default_judge_model_id: str | None = None


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
