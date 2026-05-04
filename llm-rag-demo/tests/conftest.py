import json
import math
import uuid

import pytest

from app.llm.providers import LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    """Controllable mock for testing the LLM router and pipeline."""

    def __init__(self, name: str = "mock", response: str = '{"answer":"test"}', should_fail: bool = False):
        self.name = name
        self._response = response
        self._should_fail = should_fail
        self.call_count = 0
        self.last_messages: list[dict] | None = None

    async def complete(self, messages, model=None, temperature=0.0, max_tokens=2048):
        self.call_count += 1
        self.last_messages = messages
        if self._should_fail:
            raise RuntimeError(f"Mock provider {self.name} failure")
        return LLMResponse(
            content=self._response,
            provider=self.name,
            model=model or "mock-model",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            latency_ms=1.0,
        )


class MockEmbeddingService:
    """Returns deterministic embeddings for testing."""

    def __init__(self, dimensions: int = 1536):
        self._dimensions = dimensions
        self.call_count = 0

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        return [self._fake_embedding(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        self.call_count += 1
        return self._fake_embedding(query)

    def _fake_embedding(self, text: str) -> list[float]:
        seed = sum(ord(c) for c in text) % 100
        base = [seed / 100.0] * self._dimensions
        for i in range(min(len(text), self._dimensions)):
            base[i] = ord(text[i]) / 256.0
        return base


class MockDocumentRepository:
    """In-memory repository for testing without pgvector."""

    def __init__(self):
        self.documents: dict[str, dict] = {}
        self.chunks: list[dict] = []

    async def create_document(self, title: str, source: str = ""):
        doc_id = str(uuid.uuid4())
        doc = type("Document", (), {"id": doc_id, "title": title, "source": source})()
        self.documents[doc_id] = {"id": doc_id, "title": title, "source": source}
        return doc

    async def store_chunks(self, document_id: str, chunks: list[dict]):
        records = []
        for c in chunks:
            chunk_id = str(uuid.uuid4())
            record = {
                "id": chunk_id,
                "document_id": document_id,
                "content": c["content"],
                "chunk_index": c["chunk_index"],
                "embedding": c["embedding"],
                "metadata": c.get("metadata", {}),
            }
            self.chunks.append(record)
            records.append(record)
        return records

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[dict]:
        candidates = self.chunks
        if document_id:
            candidates = [c for c in candidates if c["document_id"] == document_id]

        scored = []
        for c in candidates:
            score = self._cosine_similarity(query_embedding, c["embedding"])
            scored.append({
                "id": c["id"],
                "document_id": c["document_id"],
                "content": c["content"],
                "chunk_index": c["chunk_index"],
                "metadata": c["metadata"],
                "score": score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    async def get_document(self, document_id: str):
        doc = self.documents.get(document_id)
        if not doc:
            return None
        return type("Document", (), doc)()

    async def list_documents(self):
        return [type("Document", (), d)() for d in self.documents.values()]

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


@pytest.fixture
def mock_provider():
    return MockProvider(name="primary")


@pytest.fixture
def failing_provider():
    return MockProvider(name="failing", should_fail=True)


@pytest.fixture
def mock_embedding_service():
    return MockEmbeddingService()


@pytest.fixture
def mock_repository():
    repo = MockDocumentRepository()
    repo.chunks = []
    return repo
