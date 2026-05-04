import asyncio
import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BASE_DELAY = 1.0


class EmbeddingService:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ):
        self._client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            timeout=30.0,
        )
        self._model = model or settings.openai_embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts with retry and exponential backoff."""
        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.embeddings.create(
                    input=texts,
                    model=self._model,
                )
                return [item.embedding for item in response.data]
            except Exception as exc:
                if attempt == MAX_RETRIES - 1:
                    raise
                delay = BASE_DELAY * (2**attempt)
                logger.warning(
                    "Embedding attempt %d failed: %s. Retrying in %.1fs",
                    attempt + 1,
                    exc,
                    delay,
                )
                await asyncio.sleep(delay)

    async def embed_query(self, query: str) -> list[float]:
        result = await self.embed_texts([query])
        return result[0]
