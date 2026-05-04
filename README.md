# Roman Uglov - Production Code Samples

- uglovrv@gmail.com (Prefer)
- linkedin.com/in/romanuglov

**Stack:** Python | FastAPI | LLM/RAG | OpenAI & Anthropic APIs | pgvector | PostgreSQL | Airflow | PySpark | Kubernetes | Docker | Redis

## Projects

### AI / LLM Engineering

**[LLM RAG Demo](llm-rag-demo)**
RAG pipeline with multi-provider LLM fallback (OpenAI, Anthropic, OpenRouter).
Embeddings in PostgreSQL (pgvector), structured outputs, provider health tracking.

### Backend & Infrastructure

**[FastAPI Demo](fastapi-demo)**
Async API with CQRS and GraphQL, event sourcing, distributed transactions.
Kubernetes-ready with CI/CD pipeline and health checks.

### Data Engineering

**[Data ETL Demo](data-etl-demo)**
Airflow pipeline: extract → transform → load patterns.
PostgreSQL data warehouse integration.

### Production Code

**[Query Lineage Tracker](real_product_script)**
Production ETL pipeline for Trino query lineage tracking and metadata sync.
Batch processing, SQL lineage analysis, async API integration.

### System Design

**[Architecture Docs](system-design-demo)**
- LLM orchestration with RAG and multi-provider fallback
- High-load API (2000+ RPS)
- Terabyte ETL pipeline

## Quick Start

```bash
./test_all.sh            # Check status
./test_all.sh --start    # Start all demos
./test_all.sh --clean    # Clean up
./test_all.sh --restart  # Restart everything
```
