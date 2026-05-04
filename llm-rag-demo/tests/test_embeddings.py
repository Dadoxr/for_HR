"""Tests for EmbeddingService with mocked OpenAI SDK calls."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.embeddings import EmbeddingService


@pytest.mark.asyncio
async def test_embed_texts():
    mock_item_1 = MagicMock()
    mock_item_1.embedding = [0.1, 0.2, 0.3]
    mock_item_2 = MagicMock()
    mock_item_2.embedding = [0.4, 0.5, 0.6]

    mock_response = MagicMock()
    mock_response.data = [mock_item_1, mock_item_2]

    with patch("app.rag.embeddings.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.embeddings.create = AsyncMock(return_value=mock_response)

        service = EmbeddingService(api_key="sk-test", model="text-embedding-3-small")
        result = await service.embed_texts(["hello", "world"])

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    instance.embeddings.create.assert_called_once_with(
        input=["hello", "world"],
        model="text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_embed_query():
    mock_item = MagicMock()
    mock_item.embedding = [0.7, 0.8, 0.9]

    mock_response = MagicMock()
    mock_response.data = [mock_item]

    with patch("app.rag.embeddings.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.embeddings.create = AsyncMock(return_value=mock_response)

        service = EmbeddingService(api_key="sk-test")
        result = await service.embed_query("test query")

    assert result == [0.7, 0.8, 0.9]


@pytest.mark.asyncio
async def test_embed_texts_api_error():
    with patch("app.rag.embeddings.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.embeddings.create = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )

        service = EmbeddingService(api_key="bad-key")
        with pytest.raises(Exception, match="401"):
            await service.embed_texts(["test"])
