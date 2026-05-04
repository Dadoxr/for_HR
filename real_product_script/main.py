#!/usr/bin/env python3
"""Trino query lineage tracker.

ETL pipeline that:
1. Extracts query data from Trino system.runtime.queries
2. Stores query history in PostgreSQL
3. Parses SQL to extract source table lineage
4. Syncs metadata with OMD via REST API
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import dotenv
import httpx
import jwt
import urllib3
from pydantic import BaseModel
from sqllineage.exceptions import InvalidSyntaxException
from sqllineage.runner import LineageRunner

if TYPE_CHECKING:
    from psycopg2.extensions import cursor as PGCursor  # noqa: N812
    from trino.dbapi import Cursor as TrinoCursor

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(PROJECT_ROOT)

from general.conn import PostgresConnector, TrinoConnector
from general.read_creds import Config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
urllib3.disable_warnings()
os.environ["TZ"] = "Europe/Moscow"
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR: Path = Path(__file__).resolve().parent.parent
_env = os.getenv("ENV", "dev")
dotenv.load_dotenv(BASE_DIR / f".env.{_env}", override=True)

config = Config()

# Token refresh lock for async safety
_token_lock = asyncio.Lock()

# Column names for SQL — derived from model at module level, immutable
_TRINO_QUERY_COLUMNS = list(TrinoQuery.model_fields.keys()) if False else None  # noqa: deferred


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
class TrinoQuery(BaseModel):
    query_id: str | None = None
    state: str | None = None
    user: str | None = None
    source: str | None = None
    query: str | None = None
    resource_group_id: list[str] | None = None
    queued_time_ms: int | None = None
    analysis_time_ms: int | None = None
    planning_time_ms: int | None = None
    created: datetime | None = None
    started: datetime | None = None
    last_heartbeat: datetime | None = None
    end: datetime | None = None
    error_type: str | None = None
    error_code: str | None = None


# Computed after class definition
TRINO_QUERY_COLUMNS: list[str] = list(TrinoQuery.model_fields.keys())
TRINO_QUERY_PLACEHOLDERS: str = ", ".join(["%s"] * len(TRINO_QUERY_COLUMNS))
TRINO_QUERY_COLUMN_SQL: str = '","'.join(TRINO_QUERY_COLUMNS)


# ---------------------------------------------------------------------------
# PostgreSQL operations
# ---------------------------------------------------------------------------
def create_tables_in_pg(cur: PGCursor) -> None:
    """Create schema and tables in PostgreSQL if they don't exist."""
    logger.info("Creating tables if not exists")

    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS omd;

        CREATE TABLE IF NOT EXISTS omd.trino_queries_history (
            query_id VARCHAR PRIMARY KEY,
            state VARCHAR,
            "user" VARCHAR,
            "source" VARCHAR,
            query VARCHAR,
            resource_group_id VARCHAR[],
            queued_time_ms BIGINT,
            analysis_time_ms BIGINT,
            planning_time_ms BIGINT,
            created TIMESTAMP(3) WITH TIME ZONE,
            started TIMESTAMP(3) WITH TIME ZONE,
            last_heartbeat TIMESTAMP(3) WITH TIME ZONE,
            "end" TIMESTAMP(3) WITH TIME ZONE,
            error_type VARCHAR,
            error_code VARCHAR
        );
        CREATE TABLE IF NOT EXISTS omd.trino_query_objects (
            id SERIAL PRIMARY KEY,
            "name" VARCHAR NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS omd.trino_queries_and_query_objects_lnk (
            object_id INT REFERENCES omd.trino_query_objects(id),
            query_id VARCHAR REFERENCES omd.trino_queries_history(query_id),
            PRIMARY KEY (object_id, query_id)
        );
    """)
    cur.connection.commit()
    logger.info("Tables created or already exist")


def add_trino_queries_history_to_pg(
    cur: PGCursor,
    trino_queries: list[tuple[TrinoQuery, list[str]]],
) -> None:
    """Upsert TrinoQuery records into omd.trino_queries_history."""
    logger.info("Upserting %d rows to omd.trino_queries_history", len(trino_queries))
    cur.executemany(
        f"""
        INSERT INTO omd.trino_queries_history ("{TRINO_QUERY_COLUMN_SQL}")
        VALUES ({TRINO_QUERY_PLACEHOLDERS})
        ON CONFLICT (query_id) DO UPDATE SET state = EXCLUDED.state
        """,  # noqa: S608 — columns are from Pydantic model, not user input
        [tuple(q.model_dump().values()) for q, _ in trino_queries],
    )
    cur.connection.commit()
    logger.info("Upserted %d rows to omd.trino_queries_history", cur.rowcount)


def add_trino_query_objects_to_pg(cur: PGCursor, source_table_names: set[str]) -> None:
    """Insert source table names that don't exist yet."""
    logger.info("Inserting %d table names to omd.trino_query_objects", len(source_table_names))
    cur.executemany(
        """
        INSERT INTO omd.trino_query_objects (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING
        """,
        [(name,) for name in source_table_names],
    )
    cur.connection.commit()
    logger.info("Inserted %d rows to omd.trino_query_objects", cur.rowcount)


def get_trino_query_object_ids_from_pg(
    cur: PGCursor, source_table_names: set[str]
) -> list[tuple[int, str]]:
    """Get (id, name) for table names present in the database."""
    logger.info("Fetching object IDs from omd.trino_query_objects")
    cur.execute(
        """SELECT id, "name" FROM omd.trino_query_objects WHERE "name" in %s""",
        (tuple(source_table_names),),
    )
    result = cur.fetchall()
    logger.info("Got %d source table IDs", len(result))
    return result


def add_trino_queries_and_query_objects_lnk_to_pg(
    cur: PGCursor,
    source_table_ids: dict[str, int],
    trino_queries: list[tuple[TrinoQuery, list[str]]],
) -> None:
    """Insert query-to-table relationships (M2M)."""
    logger.info("Inserting query-object links to omd.trino_queries_and_query_objects_lnk")

    links = [
        (source_table_ids.get(table_name), query.query_id)
        for query, source_tables in trino_queries
        for table_name in source_tables
        if source_table_ids.get(table_name) is not None
    ]

    cur.executemany(
        """
        INSERT INTO omd.trino_queries_and_query_objects_lnk (object_id, query_id)
        VALUES (%s, %s)
        ON CONFLICT (object_id, query_id) DO NOTHING
        """,
        links,
    )
    cur.connection.commit()
    logger.info("Inserted %d link rows", cur.rowcount)


# ---------------------------------------------------------------------------
# Trino extraction
# ---------------------------------------------------------------------------
def get_count_rows_from_trino(cur: TrinoCursor) -> int:
    """Get row count from trino.system.runtime.queries."""
    logger.info("Counting rows in system.runtime.queries")
    cur.execute("SELECT count(1) FROM system.runtime.queries")
    count_rows = cur.fetchone()

    if not count_rows:
        raise ValueError("No response from system.runtime.queries for row count")

    logger.info("Counted %d rows", count_rows[0])
    return int(count_rows[0])


def get_batched_trino_data(
    cur: TrinoCursor, count_rows: int, batch_size: int
) -> Generator[list[Any], None, None]:
    """Yield batches of rows from trino.system.runtime.queries."""
    logger.info("Starting batched extraction (%d total rows, batch size %d)", count_rows, batch_size)
    for offset in range(0, count_rows, batch_size):
        cur.execute(
            """
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (ORDER BY query_id) as row_num
                FROM system.runtime.queries
            ) AS subquery
            WHERE row_num > ? AND row_num <= ?
            """,
            (offset, offset + batch_size),
        )
        result = cur.fetchall()
        logger.info("Got rows %d-%d of %d", offset, offset + len(result), count_rows)
        yield result
    logger.info("Batch extraction complete")


# ---------------------------------------------------------------------------
# SQL lineage analysis
# ---------------------------------------------------------------------------
def get_source_table_names(query: str, dialect: str = "postgres") -> list[str]:
    """Extract source table names from SQL using sqllineage.

    Falls back to 'non-validating' dialect on syntax errors.
    Returns error marker if parsing fails entirely.
    """
    try:
        return [str(t) for t in LineageRunner(query, dialect=dialect).source_tables]
    except InvalidSyntaxException:
        return [str(t) for t in LineageRunner(query, dialect="non-validating").source_tables]
    except Exception:
        logger.warning("Failed to parse SQL: %.200s", query)
        return ["LineageRunner could not parse sql"]


def validate_source_trino_queries(
    trino_queries: list[Any],
) -> list[tuple[TrinoQuery, list[str]]]:
    """Validate raw Trino rows and extract source tables for each query."""
    logger.info("Validating %d trino queries", len(trino_queries))
    return [
        (
            TrinoQuery(
                query_id=row[0],
                state=row[1],
                user=row[2],
                source=row[3],
                query=row[4],
                resource_group_id=row[5],
                queued_time_ms=row[6],
                analysis_time_ms=row[7],
                planning_time_ms=row[8],
                created=row[9],
                started=row[10],
                last_heartbeat=row[11],
                end=row[12],
                error_type=row[13],
                error_code=row[14],
            ),
            get_source_table_names(query=row[4]),
        )
        for row in trino_queries
    ]


# ---------------------------------------------------------------------------
# OMD API integration
# ---------------------------------------------------------------------------
async def get_omd_token() -> str:
    """Get or refresh OMD API token (async-safe with lock)."""
    async with _token_lock:
        TOKEN_EXPIRY_BUFFER = 10
        now_ts = int(datetime.now().timestamp()) + TOKEN_EXPIRY_BUFFER
        if config.omd.token and now_ts < config.omd.token_expire_timestamp:
            return config.omd.token

        logger.info("Refreshing OMD token")
        async with httpx.AsyncClient(verify=config.omd.ssl_verify if hasattr(config.omd, "ssl_verify") else False) as client:
            response = await client.post(
                url=config.omd.url + "/api/v1/users/login",
                headers={"Content-Type": "application/json"},
                json={"email": config.omd.email, "password": config.omd.password},
            )
            response.raise_for_status()
            data = response.json()

        config.omd.token = data.get("accessToken")
        config.omd.token_expire_timestamp = int(
            jwt.decode(config.omd.token, options={"verify_signature": False}).get("exp")
        )
        return config.omd.token


def to_fully_qualified_name(table_name: str) -> str | None:
    """Convert a table name to fully qualified OMD format.

    - schema.table (2 parts) -> service.db.schema.table
    - catalog.schema.table (3 parts) -> service.catalog.schema.table
    - Other formats are skipped
    """
    parts = table_name.split(".")
    if len(parts) == 2:
        return f"{config.omd.target_db_service}.{config.omd.target_db}.{table_name}"
    if len(parts) == 3:
        return f"{config.omd.target_db_service}.{table_name}"
    return None


def to_fully_qualified_names(source_table_names: set[str]) -> list[str]:
    """Convert a set of table names to fully qualified OMD names, skipping invalid ones."""
    return [fqn for name in source_table_names if (fqn := to_fully_qualified_name(name))]


async def send_request(
    client: httpx.AsyncClient, method: str, url: str, **kwargs
) -> dict[str, Any]:
    """Send an async HTTP request, returning response JSON or error dict."""
    try:
        response = await getattr(client, method)(url, **kwargs)
        response.raise_for_status()
        logger.debug("Request %s %s -> %d", method.upper(), url, response.status_code)
        return response.json()
    except Exception as exc:
        logger.warning("Request %s %s failed: %s", method.upper(), url, exc)
        return {"error": str(exc)}


async def get_table_ids_from_omd(source_table_names: set[str]) -> dict[str, str]:
    """Fetch OMD table IDs for given source table names."""
    fqn_list = to_fully_qualified_names(source_table_names)
    logger.info("Looking up %d table IDs in OMD", len(fqn_list))

    token = await get_omd_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    existing_tables: dict[str, str] = {}
    async with httpx.AsyncClient(
        base_url=config.omd.url,
        verify=config.omd.ssl_verify if hasattr(config.omd, "ssl_verify") else False,
        headers=headers,
    ) as client:
        tasks = [
            send_request(client, "get", f"/api/v1/tables/name/{name}")
            for name in fqn_list
        ]
        responses = await asyncio.gather(*tasks)

    for resp in responses:
        fqn = resp.get("fullyQualifiedName")
        if fqn:
            existing_tables[fqn] = resp.get("id")

    not_found = set(fqn_list) - set(existing_tables)
    logger.info("Found %d table IDs, %d not found: %s", len(existing_tables), len(not_found), not_found)
    return existing_tables


async def send_queries_to_omd(
    queries: list[tuple[TrinoQuery, list[str]]],
    omd_table_ids: dict[str, str],
) -> None:
    """Sync query metadata to OMD for queries with known source tables.

    PUT /api/v1/queries behaviour:
    - Same name, different query -> 200, updates query, increments version
    - Different name, different query -> 201, new query v0.1
    - Different name, same query -> 409, no change
    """
    token = await get_omd_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(
        base_url=config.omd.url,
        verify=config.omd.ssl_verify if hasattr(config.omd, "ssl_verify") else False,
        headers=headers,
    ) as client:
        tasks = []
        for query, source_tables in queries:
            fqn_list = to_fully_qualified_names(set(source_tables))
            query_used_in = [
                {"id": omd_table_ids[fqn], "type": "table"}
                for fqn in fqn_list
                if fqn in omd_table_ids
            ]

            if query_used_in:
                duration = (
                    int((query.end.timestamp() - query.started.timestamp()) * 1000)
                    if query.end and query.started
                    else 0
                )
                tasks.append(
                    send_request(
                        client,
                        "put",
                        "/api/v1/queries",
                        json={
                            "name": query.query_id,
                            "query": query.query,
                            "description": f"user=`{query.user}`, state={query.state}",
                            "service": config.omd.target_db_service,
                            "queryUsedIn": query_used_in,
                            "duration": duration,
                            "queryDate": int(query.started.timestamp() * 1000) if query.started else 0,
                        },
                    ),
                )

        if tasks:
            await asyncio.gather(*tasks)
            logger.info("Sent %d queries to OMD", len(tasks))


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------
def process_batch_pg(
    pg_cur: PGCursor,
    trino_queries: list[tuple[TrinoQuery, list[str]]],
) -> set[str]:
    """Store batch data in PostgreSQL. Returns set of all source table names."""
    add_trino_queries_history_to_pg(cur=pg_cur, trino_queries=trino_queries)

    all_source_tables: set[str] = {
        table_name
        for _, source_tables in trino_queries
        for table_name in source_tables
    }

    if all_source_tables:
        add_trino_query_objects_to_pg(cur=pg_cur, source_table_names=all_source_tables)
        pg_objects = get_trino_query_object_ids_from_pg(
            cur=pg_cur, source_table_names=all_source_tables
        )
        source_table_ids = {name: obj_id for obj_id, name in pg_objects}
        add_trino_queries_and_query_objects_lnk_to_pg(
            cur=pg_cur,
            source_table_ids=source_table_ids,
            trino_queries=trino_queries,
        )

    return all_source_tables


async def main() -> None:
    """Main ETL process.

    1. Extract queries from Trino in batches
    2. Validate and parse SQL lineage
    3. Store in PostgreSQL (history, objects, links)
    4. Sync metadata with OMD API
    """
    logger.info("Initializing connectors")

    trino = TrinoConnector(
        host=config.trino.host,
        port=config.trino.port,
        user=config.trino.user,
        password=config.trino.password,
    )
    pg = PostgresConnector(**config.postgres.model_dump())

    logger.info("Opening database connections")
    with trino.get_connector() as (trino_conn, trino_cur), pg.get_cursor() as pg_cur:
        try:
            create_tables_in_pg(cur=pg_cur)
            count_rows = get_count_rows_from_trino(cur=trino_cur)

            for raw_batch in get_batched_trino_data(
                cur=trino_cur, count_rows=count_rows, batch_size=config.batch_size
            ):
                trino_queries = validate_source_trino_queries(trino_queries=raw_batch)

                all_source_tables = process_batch_pg(pg_cur, trino_queries)

                if all_source_tables:
                    omd_table_ids = await get_table_ids_from_omd(
                        source_table_names=all_source_tables
                    )
                    await send_queries_to_omd(
                        queries=trino_queries, omd_table_ids=omd_table_ids
                    )

        except Exception:
            logger.exception("ETL pipeline failed")
            raise


if __name__ == "__main__":
    logger.info("Starting Trino lineage tracker")
    asyncio.run(main())
    logger.info("Trino lineage tracker finished")
