import json

import pytest

from app.llm.router import LLMRouter
from app.llm.structured import generate_structured
from app.rag.pipeline import RAGAnswer, RAGPipeline
from app.rag.retriever import Retriever
from tests.conftest import MockDocumentRepository, MockEmbeddingService, MockProvider


# --- Structured output parsing ---


@pytest.mark.asyncio
async def test_structured_output_parsing():
    response_json = json.dumps({
        "answer": "Paris is the capital of France.",
        "sources": ["[1]"],
        "confidence": 0.95,
    })
    provider = MockProvider(response=response_json)
    router = LLMRouter(providers=[provider])

    result = await generate_structured(
        router=router,
        output_model=RAGAnswer,
        user_prompt="What is the capital of France?",
    )

    assert result.answer == "Paris is the capital of France."
    assert result.confidence == 0.95
    assert "[1]" in result.sources


@pytest.mark.asyncio
async def test_structured_output_strips_markdown():
    raw = '```json\n{"answer": "test", "sources": [], "confidence": 0.5}\n```'
    provider = MockProvider(response=raw)
    router = LLMRouter(providers=[provider])

    result = await generate_structured(
        router=router,
        output_model=RAGAnswer,
        user_prompt="test",
    )

    assert result.answer == "test"


@pytest.mark.asyncio
async def test_structured_output_retries_on_invalid_json():
    """First call returns garbage, second call returns valid JSON."""
    call_count = 0
    valid_response = json.dumps({
        "answer": "fixed",
        "sources": [],
        "confidence": 0.8,
    })

    class FlakyProvider(MockProvider):
        async def complete(self, messages, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                from app.llm.providers import LLMResponse
                return LLMResponse(
                    content="not valid json {{{",
                    provider="flaky",
                    model="test",
                )
            return await super().complete(messages, **kwargs)

    provider = FlakyProvider(name="flaky", response=valid_response)
    router = LLMRouter(providers=[provider])

    result = await generate_structured(
        router=router,
        output_model=RAGAnswer,
        user_prompt="test",
        max_retries=3,
    )

    assert result.answer == "fixed"
    assert call_count == 2


@pytest.mark.asyncio
async def test_structured_output_fails_on_persistent_garbage():
    """LLM keeps returning garbage like 'UUID UUID! UUID' - should raise ValueError."""
    garbage_provider = MockProvider(name="garbage", response="UUID UUID! UUID 1234 nonsense")
    router = LLMRouter(providers=[garbage_provider])

    with pytest.raises(ValueError, match="Failed to get valid structured output"):
        await generate_structured(
            router=router,
            output_model=RAGAnswer,
            user_prompt="test",
            max_retries=2,
        )

    assert garbage_provider.call_count == 2


@pytest.mark.asyncio
async def test_structured_output_with_extra_fields_ignored():
    """LLM returns valid JSON but with extra fields - Pydantic should ignore them."""
    response_json = json.dumps({
        "answer": "Test answer",
        "sources": ["[1]"],
        "confidence": 0.9,
        "random_extra_field": "UUID UUID!",
        "another": 42,
    })
    provider = MockProvider(response=response_json)
    router = LLMRouter(providers=[provider])

    result = await generate_structured(
        router=router,
        output_model=RAGAnswer,
        user_prompt="test",
    )

    assert result.answer == "Test answer"
    assert not hasattr(result, "random_extra_field")


# --- Text splitting ---


@pytest.mark.asyncio
async def test_text_splitting():
    pipeline = RAGPipeline.__new__(RAGPipeline)
    from app.core.config import settings
    original_chunk_size = settings.chunk_size
    original_overlap = settings.chunk_overlap

    settings.chunk_size = 10
    settings.chunk_overlap = 3

    try:
        chunks = pipeline.split_text("Hello world, this is a test of text splitting.")
        assert len(chunks) > 1
        assert all(len(c) <= 10 for c in chunks)
    finally:
        settings.chunk_size = original_chunk_size
        settings.chunk_overlap = original_overlap


@pytest.mark.asyncio
async def test_text_splitting_short_text():
    """Text shorter than chunk_size should return single chunk."""
    pipeline = RAGPipeline.__new__(RAGPipeline)
    chunks = pipeline.split_text("Short.")
    assert len(chunks) == 1
    assert chunks[0] == "Short."


@pytest.mark.asyncio
async def test_text_splitting_empty_returns_original():
    """Empty text should return the original text."""
    pipeline = RAGPipeline.__new__(RAGPipeline)
    chunks = pipeline.split_text("")
    assert chunks == [""]


# --- Pipeline ingest ---


@pytest.mark.asyncio
async def test_ingest_creates_document_and_chunks(mock_embedding_service, mock_repository):
    provider = MockProvider()
    router = LLMRouter(providers=[provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    doc_id = await pipeline.ingest(
        title="Test Doc",
        text="Python is great. FastAPI is built on Python.",
        source="unit-test",
    )

    assert doc_id is not None
    assert doc_id in mock_repository.documents
    assert mock_repository.documents[doc_id]["title"] == "Test Doc"
    assert len(mock_repository.chunks) > 0
    assert mock_embedding_service.call_count > 0


@pytest.mark.asyncio
async def test_ingest_chunks_have_embeddings(mock_embedding_service, mock_repository):
    provider = MockProvider()
    router = LLMRouter(providers=[provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    await pipeline.ingest(title="Doc", text="Some content here for testing embeddings.")

    for chunk in mock_repository.chunks:
        assert "embedding" in chunk
        assert isinstance(chunk["embedding"], list)
        assert len(chunk["embedding"]) == 1536


@pytest.mark.asyncio
async def test_ingest_preserves_metadata(mock_embedding_service, mock_repository):
    provider = MockProvider()
    router = LLMRouter(providers=[provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    await pipeline.ingest(title="My Title", text="Content.", source="my-source")

    for chunk in mock_repository.chunks:
        assert chunk["metadata"]["title"] == "My Title"
        assert chunk["metadata"]["source"] == "my-source"


# --- Pipeline query ---


@pytest.mark.asyncio
async def test_query_retrieves_and_generates(mock_embedding_service, mock_repository):
    """Full pipeline: ingest doc, then query it. LLM returns structured answer."""
    answer_json = json.dumps({
        "answer": "FastAPI is a Python web framework.",
        "sources": ["[1]"],
        "confidence": 0.92,
    })
    provider = MockProvider(response=answer_json)
    router = LLMRouter(providers=[provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    await pipeline.ingest(title="Doc", text="FastAPI is a modern Python web framework for building APIs.")
    result = await pipeline.query("What is FastAPI?")

    assert result.answer == "FastAPI is a Python web framework."
    assert result.confidence == 0.92
    assert provider.call_count == 1  # LLM called once for query


@pytest.mark.asyncio
async def test_query_passes_context_to_llm(mock_embedding_service, mock_repository):
    """Verify that retrieved chunks appear in the prompt sent to LLM."""
    answer_json = json.dumps({"answer": "ok", "sources": [], "confidence": 0.5})
    provider = MockProvider(response=answer_json)
    router = LLMRouter(providers=[provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    await pipeline.ingest(title="Doc", text="PostgreSQL supports vector search via pgvector extension.")
    await pipeline.query("How does PostgreSQL handle vectors?")

    messages = provider.last_messages
    assert messages is not None
    user_msg = next(m for m in messages if m["role"] == "user")
    assert "Context:" in user_msg["content"]
    assert "Question:" in user_msg["content"]


@pytest.mark.asyncio
async def test_query_with_document_filter(mock_embedding_service, mock_repository):
    """Querying with document_id should only search within that document."""
    answer_json = json.dumps({"answer": "Filtered", "sources": ["[1]"], "confidence": 0.8})
    provider = MockProvider(response=answer_json)
    router = LLMRouter(providers=[provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    doc1_id = await pipeline.ingest(title="Python", text="Python is a programming language.")
    doc2_id = await pipeline.ingest(title="Rust", text="Rust is a systems language.")

    result = await pipeline.query("What is this about?", document_id=doc1_id)
    assert result.answer == "Filtered"


@pytest.mark.asyncio
async def test_query_llm_returns_garbage_falls_back_to_error(mock_embedding_service, mock_repository):
    """LLM returns 'UUID UUID! UUID' garbage - pipeline should raise ValueError."""
    garbage_provider = MockProvider(name="garbage", response="UUID UUID! UUID asdfjkl")
    router = LLMRouter(providers=[garbage_provider])
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    await pipeline.ingest(title="Doc", text="Some content for testing.")

    with pytest.raises(ValueError, match="Failed to get valid structured output"):
        await pipeline.query("What is this?")


@pytest.mark.asyncio
async def test_query_llm_all_providers_down(mock_embedding_service, mock_repository):
    """All LLM providers fail - should raise RuntimeError."""
    p1 = MockProvider(name="a", should_fail=True)
    p2 = MockProvider(name="b", should_fail=True)
    router = LLMRouter(providers=[p1, p2], max_retries=1)
    pipeline = RAGPipeline(
        llm_router=router,
        embedding_service=mock_embedding_service,
        repository=mock_repository,
    )

    await pipeline.ingest(title="Doc", text="Content.")

    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        await pipeline.query("test")


# --- Retriever ---


@pytest.mark.asyncio
async def test_retriever_returns_relevant_chunks(mock_embedding_service, mock_repository):
    """Retriever should return chunks sorted by similarity score."""
    retriever = Retriever(mock_embedding_service, mock_repository)

    mock_repository.chunks = []
    embeddings = await mock_embedding_service.embed_texts(["python programming", "cooking recipes", "python web framework"])
    for i, (text, emb) in enumerate([
        ("python programming", embeddings[0]),
        ("cooking recipes", embeddings[1]),
        ("python web framework", embeddings[2]),
    ]):
        mock_repository.chunks.append({
            "id": str(i),
            "document_id": "doc1",
            "content": text,
            "chunk_index": i,
            "embedding": emb,
            "metadata": {},
        })

    results = await retriever.retrieve("python", top_k=2)

    assert len(results) == 2
    assert all(r["score"] > 0 for r in results)
    # First result should have highest score
    assert results[0]["score"] >= results[1]["score"]
