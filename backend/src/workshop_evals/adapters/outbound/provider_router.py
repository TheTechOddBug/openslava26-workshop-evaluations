"""Routes each chat call to the client that handles the model's provider.

This is itself an LLMClientPort, so the application layer depends on one client regardless
of how many providers are wired in behind it.
"""

from __future__ import annotations

from workshop_evals.application.ports.llm_client import LLMClientPort, Message
from workshop_evals.domain.models import Completion, ModelSpec, Provider, RunParams


class ProviderRouter:
    def __init__(self, clients: dict[Provider, LLMClientPort]) -> None:
        self._clients = clients

    async def chat(
        self, model: ModelSpec, messages: list[Message], params: RunParams
    ) -> Completion:
        client = self._clients.get(model.provider)
        if client is None:
            return Completion(
                text="", error=f"no client configured for provider '{model.provider.value}'"
            )
        return await client.chat(model, messages, params)
