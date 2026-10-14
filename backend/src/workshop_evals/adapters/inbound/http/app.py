"""Composition root: wire the ports and adapters together and expose the FastAPI app.

The LLM client can be overridden (tests inject a fake), so the whole API can be exercised
without any network access or model cost.
"""

from __future__ import annotations

from dataclasses import dataclass

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from workshop_evals.adapters.inbound.http.routes import router
from workshop_evals.adapters.outbound.anthropic_client import AnthropicClient
from workshop_evals.adapters.outbound.demo_client import make_demo_client
from workshop_evals.adapters.outbound.inmemory_run_repo import InMemoryRunRepository
from workshop_evals.adapters.outbound.jsonl_dataset_repo import JsonlDatasetRepository
from workshop_evals.adapters.outbound.model_discovery import discover_models
from workshop_evals.adapters.outbound.openai_compat_client import OpenAICompatClient
from workshop_evals.adapters.outbound.provider_router import ProviderRouter
from workshop_evals.adapters.outbound.yaml_env_catalog import YamlModelCatalog
from workshop_evals.application.ports.llm_client import LLMClientPort
from workshop_evals.application.services.catalog import CatalogService
from workshop_evals.application.services.compare import ComparePairwiseService
from workshop_evals.application.services.dataset_management import DatasetManagementService
from workshop_evals.application.services.ensemble import EnsembleJudgeService
from workshop_evals.application.services.evaluators import default_registry
from workshop_evals.application.services.judge_agreement import JudgeAgreementService
from workshop_evals.application.services.model_management import ModelManagementService
from workshop_evals.application.services.run_evaluation import RunEvaluationService
from workshop_evals.config.settings import Settings, get_settings
from workshop_evals.domain.models import Provider


@dataclass
class Container:
    settings: Settings
    datasets: JsonlDatasetRepository
    catalog: CatalogService
    runs: RunEvaluationService
    judge_agreement: JudgeAgreementService
    compare: ComparePairwiseService
    ensemble: EnsembleJudgeService
    models_mgmt: ModelManagementService
    datasets_mgmt: DatasetManagementService
    run_repo: InMemoryRunRepository


def default_llm_client() -> LLMClientPort:
    return ProviderRouter(
        {
            Provider.OPENAI_COMPAT: OpenAICompatClient(),
            Provider.ANTHROPIC: AnthropicClient(),
        }
    )


def build_container(
    settings: Settings | None = None, llm_client: LLMClientPort | None = None
) -> Container:
    settings = settings or get_settings()
    datasets = JsonlDatasetRepository(settings.datasets_dir, settings.datasets_overlay)
    models = YamlModelCatalog(settings.models_yaml, settings.models_overlay)
    run_repo = InMemoryRunRepository()
    registry = default_registry()
    if llm_client is not None:
        client = llm_client
    elif settings.fake_llm:
        client = make_demo_client()
    else:
        client = default_llm_client()
    runs = RunEvaluationService(client, models, datasets, registry, run_repo)
    judge_agreement = JudgeAgreementService(client, models, datasets, run_repo)
    compare = ComparePairwiseService(client, models, datasets)
    ensemble = EnsembleJudgeService(client, models, datasets)
    models_mgmt = ModelManagementService(models, discover_models)
    datasets_mgmt = DatasetManagementService(datasets)
    catalog = CatalogService(models, datasets, registry)
    return Container(
        settings=settings,
        datasets=datasets,
        catalog=catalog,
        runs=runs,
        judge_agreement=judge_agreement,
        compare=compare,
        ensemble=ensemble,
        models_mgmt=models_mgmt,
        datasets_mgmt=datasets_mgmt,
        run_repo=run_repo,
    )


def create_app(container: Container | None = None) -> FastAPI:
    container = container or build_container()
    app = FastAPI(title="Workshop Evals API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.container = container
    app.include_router(router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    uvicorn.run(app, host="127.0.0.1", port=get_settings().port)
