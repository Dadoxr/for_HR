# FastAPI Demo

Async API with multiple architecture patterns: CQRS/Event Sourcing, DAL-Services-REST, and GraphQL. SQLAlchemy async with SQLite (default) or PostgreSQL support.

## Quick Start

### Using Makefile

```bash
make install    # Install dependencies
make test       # Run tests
make run        # Start application
make dev        # Start in development mode (auto-reload)
```

SQLite database is created automatically in `data/fastapi.db`. For PostgreSQL, set `DB_TYPE=postgres` in `.env.dev`.

### Using Docker

```bash
docker-compose up -d
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# GraphQL: http://localhost:8000/graphql
```

База данных SQLite сохраняется в `./data/fastapi.db` через volume.

## Architecture Patterns

### CQRS + Event Sourcing
- `/api/v1/orders` - Commands (write operations)
- `/api/v1/orders` - Queries (read operations)
- Event store with saga pattern for distributed transactions

Examples: [CQRS_EXAMPLES.md](./CQRS_EXAMPLES.md)

### DAL-Services-REST
- `/rest/orders` - REST API with DAL (Data Access Layer) pattern
- SQLAlchemy async with SQLite (default) or PostgreSQL
- Service layer for business logic

### GraphQL
- `/graphql` - GraphQL API with Strawberry
- GraphiQL playground available at `/graphql`
- Query and Mutation support
- Same DAL-Services layer as REST

Examples: [GRAPHQL_EXAMPLES.md](./GRAPHQL_EXAMPLES.md)

## Features

- Async/await with dependency injection
- Event-driven architecture (CQRS)
- DAL-Services-REST pattern
- GraphQL API (Strawberry)
- SQLAlchemy async ORM
- Distributed transaction handling (Saga)
- Kubernetes-ready with health checks

## Testing

```bash
make test       # Run all tests
make test-cov   # Run tests with coverage report
```

