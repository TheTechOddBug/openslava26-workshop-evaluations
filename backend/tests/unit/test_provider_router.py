"""Tests for the provider router that dispatches by a model's provider."""

from __future__ import annotations

from workshop_evals.adapters.outbound.fake_llm_client import FakeLLMClient
from workshop_evals.adapters.outbound.provider_router import ProviderRouter
from workshop_evals.domain.models import ModelSpec, Provider, RunParams


def _model(provider: Provider) -> ModelSpec:
    return ModelSpec(id="m", display_name="m", provider=provider, model_id="x")


async def test_router_dispatches_to_matching_client():
    router = ProviderRouter(
        {
            Provider.OPENAI_COMPAT: FakeLLMClient(default="from-openai"),
            Provider.ANTHROPIC: FakeLLMClient(default="from-anthropic"),
        }
    )
    out = await router.chat(
        _model(Provider.ANTHROPIC), [{"role": "user", "content": "hi"}], RunParams()
    )
    assert out.text == "from-anthropic"


async def test_router_reports_missing_client():
    router = ProviderRouter({})
    out = await router.chat(_model(Provider.OPENAI_COMPAT), [], RunParams())
    assert out.text == ""
    assert out.error is not None
