# Data ETL Demo

Airflow pipeline: extract from APIs, load to PostgreSQL data warehouse.

## Architecture

- **Extract**: Fetch data from external APIs
- **Load**: Store results in PostgreSQL data warehouse

## Quick Start

```bash
# Standard method
docker-compose up -d

# Alternative (macOS without file sharing)
docker-compose -f docker-compose-simple.yml up -d --build

# Airflow UI: http://localhost:8080 (admin/admin)
```

## DAGs

- `extract_api_data`: Fetches data from public APIs
- `load_to_dwh`: Loads processed data to PostgreSQL

