# Production LLM Orchestration with RAG

Architecture for a production LLM system serving enterprise B2B clients with near-99% SLA.

## System Overview

```
┌──────────────┐     ┌──────────────────┐     ┌─────────────────────────┐
│   Clients    │────▶│   API Gateway    │────▶│   LLM Orchestration     │
│  (B2B API)   │     │  (Rate Limit,    │     │   Service (FastAPI)     │
│              │     │   Auth, Quota)   │     │                         │
└──────────────┘     └──────────────────┘     └────────┬────────────────┘
                                                       │
                            ┌──────────────────────────┼──────────────────┐
                            ▼                          ▼                  ▼
                    ┌──────────────┐         ┌──────────────┐   ┌──────────────┐
                    │  RAG Pipeline │         │  LLM Router  │   │   Cache      │
                    │              │         │  (Fallback)  │   │  (Redis)     │
                    └──────┬───────┘         └──────┬───────┘   └──────────────┘
                           │                        │
                    ┌──────┴───────┐        ┌───────┴────────────────────┐
                    │  PostgreSQL   │        │                           │
                    │  + pgvector   │        ▼           ▼              ▼
                    │  (Embeddings) │    ┌────────┐ ┌──────────┐ ┌────────────┐
                    └──────────────┘    │ OpenAI │ │ Anthropic│ │ OpenRouter │
                                       └────────┘ └──────────┘ └────────────┘
```

## RAG Pipeline

### Document Ingestion

```
Raw Document → Chunking (512 tokens, 64 overlap)
                    │
                    ▼
            Embedding (OpenAI text-embedding-3-small)
                    │
                    ▼
            PostgreSQL + pgvector (IVFFlat index)
```

- **Chunking strategy:** Fixed-size with overlap to preserve context at boundaries. Chunk size tuned for embedding model's optimal input length.
- **Embedding storage:** PostgreSQL with pgvector extension instead of a dedicated vector DB. Reduces infrastructure complexity - one database for both relational and vector data.
- **Indexing:** IVFFlat for approximate nearest neighbor search. 100 lists for datasets up to ~1M chunks. Switch to HNSW at larger scale.

### Query Flow

```
User Query → Embed Query → pgvector Cosine Similarity (top-k)
                                      │
                                      ▼
                              Context Assembly
                              (top-k chunks + metadata)
                                      │
                                      ▼
                              Augmented Prompt
                              (system + context + query)
                                      │
                                      ▼
                              LLM Generation → Structured Output (Pydantic)
```

- **Retrieval:** Cosine similarity via pgvector `<=>` operator. Supports metadata filtering (by document, brand, audience).
- **Context window management:** Token counting before prompt assembly. If context exceeds model limits, trim lowest-relevance chunks.
- **Structured outputs:** Pydantic model schema sent as part of system prompt. Parse + validate response. Retry with error feedback on parse failure (up to 2 retries).

## Multi-Provider LLM Fallback

### Provider Chain

```
Request → Provider 1 (OpenAI) ──fail──▶ Provider 2 (Anthropic) ──fail──▶ Provider 3 (OpenRouter)
              │                              │                                │
              ▼                              ▼                                ▼
          Response                       Response                         Response
```

### Health Tracking

Each provider maintains a health state:

| State | Condition | Behavior |
|-------|-----------|----------|
| Healthy | 0 consecutive failures | Try first |
| Degraded | 1-2 failures, cooldown expired | Try with lower priority |
| Unhealthy | 3+ failures, in cooldown | Skip until cooldown expires |

**Cooldown:** Exponential backoff - 60s → 120s → 240s → 300s (max). Resets on first successful call.

### Retry Logic

- **Per-provider retries:** Up to 2 attempts with 0.5s × attempt backoff.
- **Cross-provider fallback:** If a provider exhausts retries, mark unhealthy and try the next.
- **Total budget:** If all providers fail, return 503 with error details.

### Why Not a Single Provider?

- **Rate limits:** OpenAI rate limits hit during peak hours. Fallback to Anthropic maintains SLA.
- **Outages:** Every provider has had multi-hour outages in 2024. A 3-provider chain survived all of them.
- **Cost optimization:** Route simple queries to cheaper models, complex queries to stronger models (future enhancement).

## Caching Strategy

```
┌─────────────────────────────────────────┐
│             Redis Cache Layers          │
├─────────────────────────────────────────┤
│ L1: Embedding Cache                     │
│     Key: hash(text) → embedding vector  │
│     TTL: 24h                            │
│     Hit rate: ~40% (repeated queries)   │
├─────────────────────────────────────────┤
│ L2: Response Cache                      │
│     Key: hash(query + context) → answer │
│     TTL: 1h                             │
│     Hit rate: ~15% (exact matches)      │
└─────────────────────────────────────────┘
```

- Embedding cache saves ~$0.02/1M tokens and ~200ms per cached query.
- Response cache saves the full LLM call (~$0.01-0.10 per query and 1-5s latency).

## Observability

### Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `llm_request_duration_seconds` | Histogram | provider, model, status |
| `llm_tokens_total` | Counter | provider, direction (prompt/completion) |
| `llm_provider_errors_total` | Counter | provider, error_type |
| `llm_fallback_total` | Counter | from_provider, to_provider |
| `rag_retrieval_duration_seconds` | Histogram | top_k |
| `rag_chunk_relevance_score` | Histogram | - |
| `cache_hits_total` | Counter | layer (embedding/response) |

### Grafana Dashboard

Key panels:
- **P95 latency by provider** - detect degradation before SLA breach
- **Fallback rate** - high rate signals provider instability
- **Token cost per hour** - budget tracking, anomaly detection
- **Cache hit rate** - efficiency monitoring

### Alerting

| Alert | Condition | Severity |
|-------|-----------|----------|
| All providers unhealthy | 0 healthy providers for >1min | Critical |
| SLA latency breach | P95 > 5s for 5min | Warning |
| High fallback rate | >30% requests fall back for 10min | Warning |
| Token budget exceeded | Daily cost > threshold | Warning |

## Scaling

### Horizontal Scaling

```
                    ┌─────────────────┐
                    │  Load Balancer  │
                    └────────┬────────┘
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │  Pod 1   │  │  Pod 2   │  │  Pod 3   │
        │ FastAPI  │  │ FastAPI  │  │ FastAPI  │
        └──────────┘  └──────────┘  └──────────┘
              │              │              │
              └──────────────┼──────────────┘
                             ▼
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │   (pgvector)     │
                    │  + Read Replica  │
                    └──────────────────┘
```

- **API pods:** Kubernetes HPA, 3-10 pods based on CPU and request rate.
- **Database:** Read replica for similarity search queries. Primary for writes.
- **Connection pooling:** PgBouncer in front of PostgreSQL. Each pod gets a limited pool.
- **Async throughout:** FastAPI + asyncpg + httpx - no thread blocking on I/O.

### Bottlenecks and Mitigations

| Bottleneck | Mitigation |
|-----------|------------|
| LLM API latency (1-5s) | Async requests, response caching, streaming |
| Embedding generation | Batch embedding, embedding cache |
| pgvector search at scale | IVFFlat → HNSW, read replicas, pre-filtering |
| Token costs | Cache, model routing by complexity, budget alerts |

## Cost Management

### Per-Request Cost Breakdown

| Component | Cost (approximate) |
|-----------|-------------------|
| Embedding (query) | ~$0.00002 |
| Embedding (ingest, per chunk) | ~$0.00002 |
| LLM generation (GPT-4o-mini) | ~$0.001-0.01 |
| LLM generation (Claude Sonnet) | ~$0.005-0.05 |
| pgvector query | negligible |

### Budget Controls

- **Token counting** before each LLM call. Reject if estimated cost exceeds per-request budget.
- **Per-tenant quotas** tracked in Redis. Daily/monthly limits with soft and hard caps.
- **Model routing:** Simple factual queries → GPT-4o-mini ($). Complex reasoning → Claude Sonnet ($$). Use query classifier to route.

## Performance Targets

| Metric | Target |
|--------|--------|
| P95 end-to-end latency | < 5s (including LLM) |
| P95 retrieval latency | < 100ms |
| Availability | 99.9% |
| Error rate | < 0.1% |
| Cache hit rate (embedding) | > 30% |
