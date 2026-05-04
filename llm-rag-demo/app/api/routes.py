import logging

from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    HealthResponse,
    IngestRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)
from app.core.config import settings
from app.llm.providers import AnthropicProvider, OpenAIProvider, OpenRouterProvider
from app.llm.router import LLMRouter
from app.rag.embeddings import EmbeddingService
from app.rag.pipeline import RAGPipeline
from app.storage.repository import DocumentRepository

logger = logging.getLogger(__name__)
router = APIRouter()

_PROVIDER_REGISTRY = {
    "openai": lambda key, model: OpenAIProvider(api_key=key, default_model=model),
    "anthropic": lambda key, model: AnthropicProvider(api_key=key, default_model=model),
    "openrouter": lambda key, model: OpenRouterProvider(api_key=key, default_model=model),
}

_DEFAULT_MODELS = {
    "openai": lambda: settings.openai_model,
    "anthropic": lambda: settings.anthropic_model,
    "openrouter": lambda: settings.openrouter_model,
}

_DEFAULT_KEYS = {
    "openai": lambda: settings.openai_api_key,
    "anthropic": lambda: settings.anthropic_api_key,
    "openrouter": lambda: settings.openrouter_api_key,
}


def _build_providers(
    api_key: str | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> list:
    """Build LLM providers. If api_key/provider passed per-request, use those."""
    if api_key and provider:
        factory = _PROVIDER_REGISTRY.get(provider)
        if factory:
            return [factory(api_key, model or _DEFAULT_MODELS[provider]())]

    providers = []
    for name in settings.llm_provider_order:
        factory = _PROVIDER_REGISTRY.get(name)
        if factory:
            key = _DEFAULT_KEYS[name]()
            default_model = _DEFAULT_MODELS[name]()
            providers.append(factory(key, default_model))
    return providers


def _get_pipeline(
    api_key: str | None = None,
    provider: str | None = None,
    model: str | None = None,
    embedding_api_key: str | None = None,
) -> RAGPipeline:
    providers = _build_providers(api_key=api_key, provider=provider, model=model)
    llm_router = LLMRouter(
        providers=providers,
        max_retries=settings.llm_max_retries,
        timeout=settings.llm_timeout,
    )
    embedding_service = EmbeddingService(
        api_key=embedding_api_key or settings.openai_api_key,
    )
    repository = DocumentRepository()
    return RAGPipeline(
        llm_router=llm_router,
        embedding_service=embedding_service,
        repository=repository,
    )


def _is_auth_error(exc: Exception) -> bool:
    """Check if exception is an authentication error from any provider SDK."""
    try:
        from openai import AuthenticationError as OpenAIAuthError

        if isinstance(exc, OpenAIAuthError):
            return True
    except ImportError:
        pass
    try:
        from anthropic import AuthenticationError as AnthropicAuthError

        if isinstance(exc, AnthropicAuthError):
            return True
    except ImportError:
        pass
    return False


@router.get("/health", response_model=HealthResponse)
async def health_check():
    configured = []
    if settings.openai_api_key:
        configured.append({"name": "openai", "status": "configured"})
    if settings.anthropic_api_key:
        configured.append({"name": "anthropic", "status": "configured"})
    if settings.openrouter_api_key:
        configured.append({"name": "openrouter", "status": "configured"})

    return HealthResponse(
        status="healthy",
        providers=configured
        or [{"name": "none", "status": "no API keys set — pass your own in /ingest and /query"}],
    )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(req: IngestRequest):
    pipeline = _get_pipeline(embedding_api_key=req.openai_api_key)
    try:
        doc_id = await pipeline.ingest(
            title=req.title,
            text=req.text,
            source=req.source,
        )
    except Exception as exc:
        if _is_auth_error(exc):
            raise HTTPException(status_code=401, detail="Invalid API key for embedding provider")
        raise HTTPException(status_code=503, detail=str(exc))
    chunk_count = len(pipeline.split_text(req.text))
    return IngestResponse(document_id=doc_id, chunks_count=chunk_count)


@router.post("/query", response_model=QueryResponse)
async def query_documents(req: QueryRequest):
    embedding_key = req.openai_api_key or (
        req.api_key if req.provider == "openai" else None
    )
    pipeline = _get_pipeline(
        api_key=req.api_key,
        provider=req.provider,
        model=req.model,
        embedding_api_key=embedding_key,
    )
    try:
        result = await pipeline.query(
            question=req.question,
            top_k=req.top_k,
            document_id=req.document_id,
        )
    except Exception as exc:
        if _is_auth_error(exc):
            raise HTTPException(status_code=401, detail="Invalid API key for LLM provider")
        if isinstance(exc, RuntimeError):
            raise HTTPException(status_code=503, detail=str(exc))
        raise HTTPException(status_code=502, detail=str(exc))

    return QueryResponse(
        answer=result.answer,
        sources=result.sources,
        confidence=result.confidence,
        provider_used=pipeline.provider_names[0] if pipeline.provider_names else None,
        model_used=req.model,
    )
