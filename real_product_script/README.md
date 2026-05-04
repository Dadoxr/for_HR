# Query Lineage Tracker

Production ETL pipeline tracking Trino query lineage and synchronizing metadata with OMD system. Running in production for years.

**Note:** Requires production infrastructure access (Trino, OMD API, production databases). Cannot be run locally.

## Overview

Extracts query execution data from Trino, analyzes SQL lineage, and synchronizes metadata with operational metadata management system. Uses batch processing, async API calls, and database operations.

## Features

- **Query Extraction**: Batch extraction from `trino.system.runtime.queries`
- **SQL Lineage Analysis**: Extracts source tables from SQL queries using SQLLineage
- **Metadata Synchronization**: Syncs query metadata with OMD via REST API
- **Async Processing**: Efficient async HTTP requests for API calls
- **PostgreSQL Storage**: Stores query history and lineage relationships

## Architecture

```
Trino (system.runtime.queries)
    ↓ (batch extraction)
PostgreSQL (query history + lineage)
    ↓ (lineage analysis)
OMD API (metadata sync)
```

## Key Components

1. **Trino Connector**: Extracts query execution data
2. **PostgreSQL Storage**: 
   - `omd.trino_queries_history` - Query execution history
   - `omd.trino_query_objects` - Source table catalog
   - `omd.trino_queries_and_query_objects_lnk` - Many-to-many relationships
3. **Lineage Analyzer**: SQL parsing to extract source tables
4. **OMD Client**: Async REST API client for metadata synchronization

## Requirements

- Python 3.10+
- PostgreSQL
- Trino access
- OMD API access

## Dependencies

- `pydantic` - Data validation
- `httpx` - Async HTTP client
- `sqllineage` - SQL lineage extraction
- `psycopg2` - PostgreSQL adapter
- `trino` - Trino client

## Usage

```bash
python main.py
```

Configure via environment variables (`.env.prod` or `.env.dev`):
- Trino connection settings
- PostgreSQL connection settings
- OMD API credentials
- Batch size configuration

## Data Flow

1. **Extract**: Gets query data from Trino in batches
2. **Transform**: Validates queries and extracts source tables via SQL lineage
3. **Load**: 
   - Stores query history in PostgreSQL
   - Creates source table catalog
   - Establishes query-to-table relationships
4. **Sync**: Sends query metadata to OMD API asynchronously

## Notes

- Uses batch processing for large datasets
- Handles SQL parsing errors gracefully
- Implements async patterns for API efficiency
- Production-ready error handling and logging

