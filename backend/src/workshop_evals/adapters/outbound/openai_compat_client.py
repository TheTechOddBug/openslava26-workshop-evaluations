"""OpenAI-compatible chat completion adapter.

Works with any server that speaks POST /chat/completions — Ollama, llama.cpp,
MLX Server, LM Studio, OpenAI, and Azure OpenAI.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx

from workshop_evals.application.ports.llm_client import Message
from workshop_evals.domain.models import Completion, ModelSpec, RunParams, Usage


class OpenAICompatClient:
    """LLM client for any OpenAI-compatible /chat/completions endpoint."""

    def __init__(self, *, timeout: float = 180.0, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries

    async def chat(
        self,
        model: ModelSpec,
        messages: list[Message],
        params: RunParams,
    ) -> Completion:
        if not model.base_url:
            return Completion(text="", error="base_url not configured for this model")

        url = f"{model.base_url.rstrip('/')}/chat/completions"

        body: dict[str, Any] = {
            "model": model.model_id,
            "messages": messages,
            "temperature": params.temperature,
            "max_tokens": params.max_tokens,
        }
        if params.top_p is not None:
            body["top_p"] = params.top_p
        if params.seed is not None:
            body["seed"] = params.seed
        if params.stop is not None:
            body["stop"] = params.stop
        if params.presence_penalty is not None:
            body["presence_penalty"] = params.presence_penalty
        if params.frequency_penalty is not None:
            body["frequency_penalty"] = params.frequency_penalty
        if model.supports_reasoning and params.reasoning_effort:
            body["reasoning_effort"] = params.reasoning_effort

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if model.api_key_env and model.api_key_env in os.environ:
            headers["Authorization"] = f"Bearer {os.environ[model.api_key_env]}"

        last_error = ""
        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                await asyncio.sleep(1.5 * attempt)
            try:
                t0 = time.perf_counter()
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, json=body, headers=headers)
                latency_ms = int((time.perf_counter() - t0) * 1000)

                if resp.status_code >= 500:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:300]}"
                    continue  # transient — retry

                if not resp.is_success:
                    # 4xx errors are not transient; return immediately
                    return Completion(
                        text="",
                        error=f"HTTP {resp.status_code}: {resp.text[:300]}",
                    )

                data = resp.json()
                choice = (data.get("choices") or [{}])[0]
                text = (choice.get("message") or {}).get("content") or ""
                raw = data.get("usage") or {}
                prompt_tokens = raw.get("prompt_tokens", 0)
                completion_tokens = raw.get("completion_tokens", 0)
                total_tokens = raw.get("total_tokens", prompt_tokens + completion_tokens)
                usage = Usage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                )
                return Completion(text=text, usage=usage, model_id=model.model_id)

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            except Exception as exc:
                # Unexpected error — no point retrying
                return Completion(text="", error=f"{type(exc).__name__}: {exc}")

        return Completion(text="", error=last_error)
