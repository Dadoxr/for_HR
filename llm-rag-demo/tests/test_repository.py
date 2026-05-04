"""Tests for DocumentRepository with mocked SQLAlchemy sessions."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.storage.repository import DocumentRepository


def _mock_session_context(session_mock):
    """Create an async context manager that yields the session mock."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session_mock)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


@pytest.mark.asyncio
async def test_create_document():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()

    async def fake_refresh(obj):
        if obj.id is None:
            import uuid
            obj.id = str(uuid.uuid4())

    session.refresh = AsyncMock(side_effect=fake_refresh)

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        doc = await repo.create_document(title="Test Doc", source="unit-test")

    assert doc.title == "Test Doc"
    assert doc.source == "unit-test"
    assert doc.id is not None
    session.add.assert_called_once()
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_store_chunks():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    chunks_data = [
        {
            "content": "chunk 1 text",
            "chunk_index": 0,
            "embedding": [0.1] * 1536,
            "metadata": {"title": "Doc"},
        },
        {
            "content": "chunk 2 text",
            "chunk_index": 1,
            "embedding": [0.2] * 1536,
        },
    ]

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        records = await repo.store_chunks("doc-123", chunks_data)

    assert len(records) == 2
    assert session.add.call_count == 2
    session.commit.assert_called_once()

    stored = session.add.call_args_list
    first_chunk = stored[0][0][0]
    assert first_chunk.document_id == "doc-123"
    assert first_chunk.content == "chunk 1 text"
    assert first_chunk.chunk_index == 0
    assert json.loads(first_chunk.metadata_json) == {"title": "Doc"}

    second_chunk = stored[1][0][0]
    assert json.loads(second_chunk.metadata_json) == {}


@pytest.mark.asyncio
async def test_similarity_search():
    mock_row = MagicMock()
    mock_row.id = "chunk-1"
    mock_row.document_id = "doc-1"
    mock_row.content = "Python is great"
    mock_row.chunk_index = 0
    mock_row.metadata_json = '{"title": "Doc"}'
    mock_row.distance = 0.15

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        results = await repo.similarity_search(
            query_embedding=[0.1] * 1536,
            top_k=5,
        )

    assert len(results) == 1
    assert results[0]["content"] == "Python is great"
    assert results[0]["score"] == pytest.approx(0.85)
    assert results[0]["metadata"] == {"title": "Doc"}
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_similarity_search_with_document_filter():
    mock_result = MagicMock()
    mock_result.all.return_value = []

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        results = await repo.similarity_search(
            query_embedding=[0.1] * 1536,
            top_k=3,
            document_id="specific-doc",
        )

    assert results == []
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_document_found():
    mock_doc = MagicMock()
    mock_doc.id = "doc-1"
    mock_doc.title = "Found Doc"

    session = AsyncMock()
    session.get = AsyncMock(return_value=mock_doc)

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        doc = await repo.get_document("doc-1")

    assert doc.title == "Found Doc"
    session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_document_not_found():
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        doc = await repo.get_document("nonexistent")

    assert doc is None


@pytest.mark.asyncio
async def test_list_documents():
    mock_doc1 = MagicMock(id="doc-1", title="First")
    mock_doc2 = MagicMock(id="doc-2", title="Second")

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [mock_doc1, mock_doc2]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    with patch("app.storage.repository.async_session", return_value=_mock_session_context(session)):
        repo = DocumentRepository()
        docs = await repo.list_documents()

    assert len(docs) == 2
    assert docs[0].title == "First"
    assert docs[1].title == "Second"
