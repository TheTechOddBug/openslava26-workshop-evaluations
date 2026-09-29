"""Unit tests for discover_models — GET /models mocked with respx."""

from __future__ import annotations

import pytest
import respx
from httpx import ConnectError, Response

from workshop_evals.adapters.outbound.model_discovery import discover_models


@respx.mock
async def test_discover_models_returns_id_list():
    respx.get("http://x/v1/models").mock(
        return_value=Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})
    )
    result = await discover_models("http://x/v1")
    assert result == ["a", "b"]


@respx.mock
async def test_discover_models_trailing_slash_stripped():
    respx.get("http://x/v1/models").mock(
        return_value=Response(200, json={"data": [{"id": "only"}]})
    )
    result = await discover_models("http://x/v1/")
    assert result == ["only"]


@respx.mock
async def test_discover_models_server_error_raises():
    respx.get("http://x/v1/models").mock(return_value=Response(500))
    import httpx

    with pytest.raises(httpx.HTTPStatusError):
        await discover_models("http://x/v1")


@respx.mock
async def test_discover_models_connection_error_raises():
    respx.get("http://x/v1/models").mock(side_effect=ConnectError("refused"))
    import httpx

    with pytest.raises(httpx.HTTPError):
        await discover_models("http://x/v1")
