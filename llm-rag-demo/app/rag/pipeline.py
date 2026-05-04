import logging
import re

from pydantic import BaseModel

from app.core.config import settings
from app.llm.router import LLMRouter
from app.llm.structured import generate_structured
from app.rag.embeddings import EmbeddingService
from app.rag.retriever import Retriever
from app.storage.repository import DocumentRepository

logger = logging.getLogger(__name__)

RAG_SYSTEM_PROMPT = """You are a helpful assistant. Answer the user's question based ONLY on the provided context.
If the context does not contain enough information, say so clearly.
Always cite which context chunks you used."""


class RAGAnswer(BaseModel):
    answer: str
    sources: list[str]
    confidence: float


class RAGPipeline:
    def __init__(
        self,
        llm_router: LLMRouter,
        embedding_service: EmbeddingService,
        repository: DocumentRepository,
    ):
        self._router = llm_router
        self._retriever = Retriever(embedding_service, repository)
        self._repository = repository
        self._embeddings = embedding_service

    @property
    def provider_names(self) -> list[str]:
        """Public access to configured provider names."""
        return [p.name for p in self._router.providers]

    async def ingest(self, title: str, text: str, source: str = "") -> str:
        """Chunk text, embed, and store in pgvector. Returns document ID."""
        doc = await self._repository.create_document(title=title, source=source)

        chunks_text = self.split_text(text)
        embeddings = await self._embeddings.embed_texts(chunks_text)

        chunk_records = [
            {
                "content": text_chunk,
                "chunk_index": i,
                "embedding": emb,
                "metadata": {"title": title, "source": source},
            }
            for i, (text_chunk, emb) in enumerate(zip(chunks_text, embeddings))
        ]
        await self._repository.store_chunks(doc.id, chunk_records)

        logger.info("Ingested document %s (%d chunks)", doc.id, len(chunk_records))
        return doc.id

    async def query(
        self,
        question: str,
        top_k: int | None = None,
        document_id: str | None = None,
    ) -> RAGAnswer:
        """Full RAG: retrieve context, augment prompt, generate structured answer."""
        k = top_k or settings.top_k
        chunks = await self._retriever.retrieve(
            query=question,
            top_k=k,
            document_id=document_id,
        )

        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[{i+1}] {chunk['content']}")
        context_block = "\n\n".join(context_parts)

        user_prompt = f"""Context:
{context_block}

Question: {question}"""

        return await generate_structured(
            router=self._router,
            output_model=RAGAnswer,
            user_prompt=user_prompt,
            system_context=RAG_SYSTEM_PROMPT,
        )

    def split_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks, preferring sentence boundaries.

        Falls back to word boundaries for sentences exceeding chunk_size.
        """
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        # Split into sentences, then break long sentences into words
        sentences = re.split(r"(?<=[.!?])\s+", text)
        segments: list[str] = []
        for sentence in sentences:
            if len(sentence) <= chunk_size:
                segments.append(sentence)
            else:
                # Split long sentence on word boundaries
                words = sentence.split()
                current = ""
                for word in words:
                    candidate = f"{current} {word}".strip() if current else word
                    if len(candidate) > chunk_size and current:
                        segments.append(current)
                        current = word
                    else:
                        current = candidate
                if current:
                    segments.append(current)

        chunks: list[str] = []
        current_chunk: list[str] = []
        current_len = 0

        for segment in segments:
            seg_len = len(segment)
            if current_len + seg_len > chunk_size and current_chunk:
                chunks.append(" ".join(current_chunk))
                # Keep overlap by retaining trailing segments
                overlap_chunk: list[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) > overlap:
                        break
                    overlap_chunk.insert(0, s)
                    overlap_len += len(s)
                current_chunk = overlap_chunk
                current_len = overlap_len

            current_chunk.append(segment)
            current_len += seg_len

        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks or [text]
