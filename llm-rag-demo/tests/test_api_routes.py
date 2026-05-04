"""Tests for API routes with mocked pipeline - covers error handling paths."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


def _mock_pipeline(ingest_return="doc-123", query_return=None, ingest_error=None, query_error=None):
    pipeline = AsyncMock()

    if ingest_error:
        pipeline.ingest = AsyncMock(side_effect=ingest_error)
    else:
        pipeline.ingest = AsyncMock(return_value=ingest_return)

    if query_error:
        pipeline.query = AsyncMock(side_effect=query_error)
    elif query_return:
        pipeline.query = AsyncMock(return_value=query_return)

    pipeline.split_text = lambda text: ["chunk1", "chunk2"]
    pipeline.provider_names = ["mock"]
    return pipeline


@pytest.mark.asyncio
async def test_ingest_success():
    pipeline = _mock_pipeline(ingest_return="doc-abc-123")

    with patch("app.api.routes._get_pipeline", return_value=pipeline):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/ingest", json={
                "title": "Test",
                "text": "Some content here.",
                "source": "test",
            })

    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == "doc-abc-123"
    assert data["chunks_count"] == 2
    pipeline.ingest.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_auth_error():
    from openai import AuthenticationError
    error = AuthenticationError(
        message="Invalid API key",
        response=AsyncMock(status_code=401),
        body={"error": {"message": "Invalid API key"}},
    )
    pipeline = _mock_pipeline(ingest_error=error)

    with patch("app.api.routes._get_pipeline", return_value=pipeline):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/ingest", json={
                "title": "Test",
                "text": "Content",
            })

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ingest_service_unavailable():
    pipeline = _mock_pipeline(ingest_error=ConnectionError("DB down"))

    with patch("app.api.routes._get_pipeline", return_value=pipeline):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/ingest", json={
                "title": "Test",
                "text": "Content",
            })

    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_query_success():
    from app.rag.pipeline import RAGAnswer
    answer = RAGAnswer(answer="FastAPI is a framework", sources=["[1]"], confidence=0.9)
    pipeline = _mock_pipeline(query_return=answer)

    with patch("app.api.routes._get_pipeline", return_value=pipeline):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/query", json={"question": "What is FastAPI?"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "FastAPI is a framework"
    assert data["confidence"] == 0.9


@pytest.mark.asyncio
async def test_query_all_providers_down():
    pipeline = _mock_pipeline(query_error=RuntimeError("All LLM providers failed"))

    with patch("app.api.routes._get_pipeline", return_value=pipeline):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/query", json={"question": "test"})

    assert resp.status_code == 503
    assert "All LLM providers failed" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_query_structured_output_failure():
    pipeline = _mock_pipeline(query_error=ValueError("Failed to get valid structured output"))

    with patch("app.api.routes._get_pipeline", return_value=pipeline):
        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/query", json={"question": "test"})

    assert resp.status_code == 502
