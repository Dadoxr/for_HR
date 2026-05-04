# LLM RAG Demo

RAG pipeline with multi-provider LLM fallback, PostgreSQL embeddings (pgvector), and structured outputs.

## Architecture

```
POST /ingest                          POST /query
     │                                     │
     ▼                                     ▼
 Chunking                            Embed query
     │                                     │
     ▼                                     ▼
 Embed chunks ──► pgvector         pgvector similarity search
                                           │
                                           ▼
                                   Augment prompt with context
                                           │
                                           ▼
                                   LLM Router (fallback chain)
                                   ┌─────────────────────┐
                                   │ OpenAI → Anthropic → │
                                   │     OpenRouter       │
                                   └─────────────────────┘
                                           │
                                           ▼
                                   Structured output (Pydantic)
```

## Key Components

**LLM Provider Abstraction** (`app/llm/providers.py`)
Abstract `LLMProvider` with three implementations: OpenAI, Anthropic, OpenRouter. Each wraps the respective SDK with async support.

**Fallback Router** (`app/llm/router.py`)
Tries providers in order. On failure (rate limit, timeout, API error), falls back to the next healthy provider. Tracks health per provider with exponential cooldown.

**Structured Outputs** (`app/llm/structured.py`)
Sends Pydantic model JSON schema as part of the prompt. Parses and validates LLM response. Retries with error feedback on validation failure.

**RAG Pipeline** (`app/rag/pipeline.py`)
Full flow: chunk text → embed → store in pgvector → retrieve by similarity → augment prompt → generate structured answer.

**PostgreSQL + pgvector** (`app/storage/`)
Embeddings stored in PostgreSQL via pgvector extension. Cosine similarity search with IVFFlat index.

## Quick Start

```bash
# Copy and set API keys (at least one LLM provider)
cp .env.example .env

# Start with Docker
docker-compose up -d

# Or locally
make install && make dev
```

## API

```bash
# Health check (works without API keys)
curl http://localhost:8001/health

# Ingest a document
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{"title": "My Doc", "text": "Your text content here..."}'

# Query with RAG
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What does the document say about X?"}'
```

## Testing

```bash
# Unit tests (no API keys needed - uses mock providers)
make test

# Integration test against running instance
python test_api.py
```

## Tech Stack

- **FastAPI** - async API
- **PostgreSQL + pgvector** - vector storage and similarity search
- **OpenAI / Anthropic / OpenRouter** - LLM providers with fallback
- **Pydantic** - structured output validation
- **SQLAlchemy 2.0** - async ORM
- **Docker Compose** - one-command setup
