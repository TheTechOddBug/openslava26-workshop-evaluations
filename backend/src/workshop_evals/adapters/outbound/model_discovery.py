"""Discover the models installed on an OpenAI-compatible server (e.g. Ollama).

Purely mechanical: a GET to the server's /models endpoint. No AI involved.
"""

from __future__ import annotations

import httpx


async def discover_models(base_url: str, timeout: float = 8.0) -> list[str]:
    """Return the model ids installed on the server at base_url.

    Raises httpx.HTTPError if the server is unreachable or returns an error.
    """
    url = base_url.rstrip("/") + "/models"
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
    return [entry["id"] for entry in data.get("data", []) if entry.get("id")]
