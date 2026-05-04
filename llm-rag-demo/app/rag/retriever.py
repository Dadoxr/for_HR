from app.rag.embeddings import EmbeddingService
from app.storage.repository import DocumentRepository


class Retriever:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        repository: DocumentRepository,
    ):
        self._embeddings = embedding_service
        self._repository = repository

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[dict]:
        query_embedding = await self._embeddings.embed_query(query)
        return await self._repository.similarity_search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_id=document_id,
        )
