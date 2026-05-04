import json

from sqlalchemy import select, text

from app.storage.models import Document, DocumentChunk, async_session


class DocumentRepository:
    async def create_document(self, title: str, source: str = "") -> Document:
        async with async_session() as session:
            doc = Document(title=title, source=source)
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            return doc

    async def store_chunks(
        self,
        document_id: str,
        chunks: list[dict],
    ) -> list[DocumentChunk]:
        """Store text chunks with their embeddings.

        Each item in `chunks` must have: content, chunk_index, embedding, metadata (optional).
        """
        async with async_session() as session:
            records = []
            for c in chunks:
                chunk = DocumentChunk(
                    document_id=document_id,
                    content=c["content"],
                    chunk_index=c["chunk_index"],
                    embedding=c["embedding"],
                    metadata_json=json.dumps(c.get("metadata", {})),
                )
                session.add(chunk)
                records.append(chunk)
            await session.commit()
            for r in records:
                await session.refresh(r)
            return records

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        document_id: str | None = None,
    ) -> list[dict]:
        """Find the most similar chunks using pgvector cosine distance."""
        async with async_session() as session:
            distance = DocumentChunk.embedding.cosine_distance(query_embedding)
            stmt = (
                select(
                    DocumentChunk.id,
                    DocumentChunk.document_id,
                    DocumentChunk.content,
                    DocumentChunk.chunk_index,
                    DocumentChunk.metadata_json,
                    distance.label("distance"),
                )
                .order_by(distance)
                .limit(top_k)
            )

            if document_id:
                stmt = stmt.where(DocumentChunk.document_id == document_id)

            result = await session.execute(stmt)
            rows = result.all()
            return [
                {
                    "id": row.id,
                    "document_id": row.document_id,
                    "content": row.content,
                    "chunk_index": row.chunk_index,
                    "metadata": json.loads(row.metadata_json),
                    "score": 1.0 - row.distance,
                }
                for row in rows
            ]

    async def get_document(self, document_id: str) -> Document | None:
        async with async_session() as session:
            return await session.get(Document, document_id)

    async def list_documents(self) -> list[Document]:
        async with async_session() as session:
            result = await session.execute(
                select(Document).order_by(Document.created_at.desc())
            )
            return list(result.scalars().all())
