#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import base64
import logging
import os
from datetime import datetime  # noqa: TC003
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional, Set, Tuple

import dotenv
import httpx
import jwt
import requests
import urllib3
from pydantic import BaseModel
from sqllineage.exceptions import InvalidSyntaxException
from sqllineage.runner import LineageRunner


if TYPE_CHECKING:
    from psycopg2.extensions import cursor as PGCursor  # noqa: N812
    from trino.dbapi import Cursor as TrinoCursor

import sys
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

from general.conn import PostgresConnector, TrinoConnector
from general.read_creds import Config

# Logging configuration
urllib3.disable_warnings()
os.environ["TZ"] = "Europe/Moscow"
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.WARNING,
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Environment variables configuration
BASE_DIR: Path = Path(__file__).resolve().parent.parent
dotenv.load_dotenv(BASE_DIR / ".env.prod", override=True)
dotenv.load_dotenv(BASE_DIR / ".env.dev", override=True)

config = Config()

# Data schemas
class TrinoQuery(BaseModel):
    query_id: Optional[str]
    state: Optional[str]
    user: Optional[str]
    source: Optional[str]
    query: Optional[str]
    resource_group_id: Optional[List[str]]
    queued_time_ms: Optional[int]
    analysis_time_ms: Optional[int]
    planning_time_ms: Optional[int]
    created: Optional[datetime]
    started: Optional[datetime]
    last_heartbeat: Optional[datetime]
    end: Optional[datetime]
    error_type: Optional[str]
    error_code: Optional[str]


############ Main script
def create_tables_in_pg(cur: PGCursor) -> None:
    """Creates tables in PostgreSQL if they don't exist."""
    logger.warning(
        "Start creating tables (omd.trino_queries_history, omd.trino_query_objects, omd.trino_queries_and_query_objects_lnk) if not exists",
    )

    create_table_query = """
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
    """
    cur.execute(create_table_query)
    cur.connection.commit()
    logger.warning("Tables created or exists")


def get_count_rows_from_trino(cur: TrinoCursor) -> int:
    """Gets row count from trino.system.runtime.queries. Returns an integer (int)."""
    logger.warning("Getting trino.system.runtime.queries rowcount")
    cur.execute("SELECT count(1) FROM system.runtime.queries")
    count_rows = cur.fetchone()

    if not count_rows:
        msg = "Have not answer from system.runtime.queries while count rows"
        raise ValueError(msg)

    logger.warning("Counted %s rows", count_rows)
    return int(count_rows[0])


def get_batched_trino_data(cur: TrinoCursor, count_rows: int, batch_size: int) -> Generator[List[Any], Any, Any]:
    """
    Creates a generator for batch extraction of data from trino.system.runtime.queries with specified batch size.

    Generator returns data chunks, each containing up to batch_size rows.
    """
    logger.warning("Start getting batched data")
    for offset in range(0, count_rows, batch_size):
        logger.warning("")
        cur.execute("""
            SELECT * FROM (
                SELECT *, ROW_NUMBER() OVER (ORDER BY query_id) as row_num
                FROM system.runtime.queries
            ) AS subquery
            WHERE row_num > ? AND row_num <= ?
        """, (offset, offset + batch_size))
        result = cur.fetchall()

        logger.warning("Getted %s - %s rows from %s", offset, offset+len(result), count_rows)
        yield result
    logger.warning("Source row is end")


def get_source_table_names(query: str, dialect: str="postgres") -> List[str]:
    """
    Extracts source table names from SQL query. Uses 'postgres' dialect by default.

    If InvalidSyntaxException occurs, dialect switches to 'non-validating'.
    In case of other errors, returns a list with message ['LineageRunner could not parse sql'].
    """
    source_table_names = ["LineageRunner could not parse sql"]
    try:
        source_table_names = [str(table) for table in LineageRunner(query, dialect=dialect).source_tables]
    except InvalidSyntaxException:
        source_table_names = [str(table) for table in LineageRunner(query, dialect="non-validating").source_tables]
    except Exception:
        logging.warning("\nError of running: %s", query)
        logging.exception("")
    return source_table_names


def validate_source_trino_queries(trino_queries: List[Any]) -> List[Tuple[TrinoQuery, List[str]]]:
    """
    Validates list of trino_queries and extracts related source tables.

    Returns a list of tuples, where each tuple consists of:
    1) TrinoQuery object created from trino.system.runtime.queries data.
    2) List of source tables related to the corresponding query.
    """
    logger.warning("Validating trino queries and getting source tables from each query")

    return [
        (TrinoQuery(
            query_id=i[0], state=i[1], user=i[2],  source=i[3],  query=i[4],  resource_group_id=i[5],
            queued_time_ms=i[6], analysis_time_ms=i[7], planning_time_ms=i[8], created=i[9],
            started=i[10], last_heartbeat=i[11], end=i[12], error_type=i[13], error_code=i[14],
        ), get_source_table_names(query=i[4]))
        for i in trino_queries
    ]


def add_trino_queries_history_to_pg(cur: PGCursor, trino_queries: List[TrinoQuery]) -> None:
    """
    Adds list of TrinoQuery objects to omd.trino_queries_history table in PostgreSQL if corresponding query_id doesn't exist.

    If query_id already exists, updates state for this query.
    """
    logger.warning("Start adding %s rows to omd.trino_queries_history", len(trino_queries))
    cur.executemany(
        f"""
        INSERT INTO omd.trino_queries_history ("{'","'.join(TrinoQuery.model_fields.keys())}")
        VALUES ({', '.join(['%s'] * len(TrinoQuery.model_fields))})
        ON CONFLICT (query_id) DO UPDATE SET state = EXCLUDED.state
        """, # noqa: S608
        [tuple(i[0].model_dump().values()) for i in trino_queries],
    )
    cur.connection.commit()
    logger.warning("Added or updated state %s rows to omd.trino_queries_history", cur.rowcount)


def add_trino_query_objects_to_pg(cur: PGCursor, source_table_names: Set[str]) -> None:
    """Adds source table names to database if they don't exist yet."""
    logger.warning("Start adding %s rows to omd.trino_query_objects", len(source_table_names))
    cur.executemany(
        """
        INSERT INTO omd.trino_query_objects (name)
        VALUES (%s)
        ON CONFLICT (name) DO NOTHING
        """,
        [(i,) for i in source_table_names],
    )
    cur.connection.commit()
    logger.warning("Added %s rows to omd.trino_query_objects.", cur.rowcount)


def get_trino_query_object_ids_from_pg(cur: PGCursor, source_table_names: Set[str]) -> List[Any]:
    """Retrieves object IDs from omd.trino_query_objects whose names are present in source_table_names list."""
    logger.warning("Start getting ids of omd.trino_query_objects")
    cur.execute("""SELECT id, "name" FROM omd.trino_query_objects WHERE "name" in %s""", (tuple(source_table_names),))
    result = cur.fetchall()
    logger.warning("Getted %s source tables.", len(result))
    return result


def add_trino_queries_and_query_objects_lnk_to_pg(
    cur: PGCursor, source_table_names: Dict[str, int], trino_queries: List[TrinoQuery],
) -> None:
    """
    1) Forms a list of tuples containing object_id and query_id,
    2) Adds records to omd.trino_queries_and_query_objects_lnk table in pg if combination (object_id + query_id) doesn't exist.
    """
    logger.warning("Start creating queries_and_query_objects_lnk and add them to postgres")

    trino_queries_and_query_objects_lnk = [
        (source_table_names.get(source_table), query.query_id)
        for query, source_tables in trino_queries
        for source_table in source_tables
    ]

    cur.executemany(
        """
        INSERT INTO omd.trino_queries_and_query_objects_lnk (object_id, query_id)
        VALUES (%s, %s)
        ON CONFLICT (object_id, query_id) DO NOTHING
        """,
        trino_queries_and_query_objects_lnk,
    )
    cur.connection.commit()
    logger.warning("Added %s rows to omd.trino_queries_and_query_objects_lnk.", cur.rowcount)


def get_omd_token() -> str:
    """Retrieves token from environment variables or, if missing, creates new token via REST and saves to config.omd.token."""
    now_ts = int(datetime.now().timestamp()) + 10
    if config.omd.token and now_ts < config.omd.token_expire_timestamp:
        return config.omd.token

    response = requests.post(
        url=config.omd.url + "/api/v1/users/login",
        headers={"Content-Type": "application/json"},
        json={"email": config.omd.email , "password": (base64.b64encode(config.omd.password.encode())).decode()},
        verify=False,
    )
    response.raise_for_status()
    response = response.json()

    config.omd.token = response.get("accessToken", None)
    config.omd.token_expire_timestamp = int((jwt.decode(config.omd.token, options={"verify_signature": False})).get("exp"))
    return config.omd.token


def change_source_table_names_to_fullyQualifiedName(source_table_names: Set[str]) -> List[str]:
    """Converts table names to fully qualified names, adding database service and database itself if missing in table name."""
    fullyQualifiedNames = []
    for table_name in source_table_names:
        table_name_len = len(table_name.split("."))

        if table_name_len == 2:
            fullyQualifiedName = f"{config.omd.target_db_service}.{config.omd.target_db}.{table_name}"
        elif table_name_len == 3:
            fullyQualifiedName = f"{config.omd.target_db_service}.{table_name}"
        else:
            fullyQualifiedName = None

        if fullyQualifiedName:
            fullyQualifiedNames.append(fullyQualifiedName)
    return fullyQualifiedNames


async def send_request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> Dict[str, str]:
    """Asynchronously sends REST request and returns dictionary with result or error message."""
    try:
        logger.warning(f"Send request to {url}")
        response = await getattr(client, method)(url, **kwargs)
        response.raise_for_status()
        logger.warning(f"Get from {url} -> status_code={response.status_code}")
        return response.json()
    except Exception as e:
        logger.warning(f"Get from {url} -> {e!s}")
        return {"error": str(e)}


async def get_table_ids_from_omd(source_table_names: Set[str]) -> Dict[str, str]:
    """
    Asynchronously requests table information from OMD via API and
    returns dictionary containing fully qualified table name (fullyQualifiedName) and its ID (id).
    """
    logger.warning(f"Send GET to api/v1/tables/name/<TABLE_NAME> ({len(source_table_names)} tables) to omd to find table_ids ")

    exists_tables = {}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + get_omd_token()}

    async with httpx.AsyncClient(base_url=config.omd.url, verify=False, headers=headers) as client:
        source_table_names = change_source_table_names_to_fullyQualifiedName(source_table_names=source_table_names)
        tasks = [send_request(client, "get", f"/api/v1/tables/name/{table_name}") for table_name in source_table_names]
        responses = await asyncio.gather(*tasks)

    for response in responses:
        table_name = response.get("fullyQualifiedName", None)
        if table_name:
            exists_tables[table_name] = response.get("id")

    logger.warning(f"Get {len(exists_tables.keys())} ids from omd. Not found - {len(source_table_names) - len(exists_tables.keys())}: {set(source_table_names) - set(exists_tables.keys())}") # noqa: E501
    return exists_tables


async def send_queries_to_omd(queries: Tuple[TrinoQuery, List[str]], omd_tables_ids: Dict[str, str]) -> None:
    """
    Asynchronous POST requests to omd via API: for each query from queries list checks if source tables exist in omd,
    and sends POST request if they exist.

    P.S. PUT request to /api/v1/queries searches query by name field, but query field is always unique.
    Therefore, adding the same query with different name and other fields won't work.
     - If you send the same name but different query -> returns status_code 200, updates query field and increments version (+0.1)
     - If you send different name but different query -> returns status_code 201, saves new query with version 0.1
     - If you send different name but the same query -> returns status_code 409 and doesn't add anything to OMD
     - Other fields don't affect the logic
    """
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + get_omd_token()}

    async with httpx.AsyncClient(base_url=config.omd.url, verify=False, headers=headers) as client:
        tasks = []
        for query, source_table_names in queries:
            source_table_names = change_source_table_names_to_fullyQualifiedName(source_table_names=source_table_names)
            queryUsedIn = []

            for fullyQualifiedName in source_table_names:
                table_id = omd_tables_ids.get(fullyQualifiedName)
                if table_id:
                    queryUsedIn.append({"id": table_id, "type": "table"})

            if len(queryUsedIn) > 0:
                tasks.append(
                    send_request(
                        client, "put", "/api/v1/queries",
                        json={
                            "name": query.query_id,
                            "query": query.query,
                            "description": f"user=`{query.user}`, state={query.state}",
                            "service": config.omd.target_db_service,
                            "queryUsedIn": queryUsedIn,
                            "duration": int((query.end.timestamp() - query.started.timestamp())*1000) if query.end else 0,
                            "queryDate": int(query.started.timestamp()*1000),
                        },
                    ),
                )
        await asyncio.gather(*tasks)


async def main() -> None:
    """
    Main ETL process
    1) Gets data from source trino.system.runtime.queries.
    2) Saves full copy to PostgreSQL database in omd.trino_queries_history table.
    3) Extracts source tables from each query, forms a set and adds them to omd.trino_query_objects table if they don't exist.
    4) Establishes many-to-many relationship between query history and source tables in omd.trino_queries_and_query_objects_lnk table.
    5) Gets source table IDs from omd and creates queries in omd via API.

    """
    logger.warning("Create trino and postgres instances")

    trino = TrinoConnector(
        host=config.trino.host,
        port=config.trino.port,
        user=config.trino.user,
        password=config.trino.password
    )
    pg = PostgresConnector(**config.postgres.model_dump())

    logger.warning("Getting trino and postgres cursors")
    with trino.get_connector() as (trino_conn, trino_cur), pg.get_cursor() as pg_cur:
        try:
            create_tables_in_pg(cur=pg_cur)

            for source_trino_queries in get_batched_trino_data(
                cur=trino_cur, count_rows=get_count_rows_from_trino(cur=trino_cur), batch_size=config.batch_size,
            ):
                trino_queries = validate_source_trino_queries(trino_queries=source_trino_queries)

                add_trino_queries_history_to_pg(cur=pg_cur, trino_queries=trino_queries)

                common_source_table_names: set = {
                    table_name for _, source_table_names in trino_queries for table_name in source_table_names
                }

                if common_source_table_names:
                    omd_tables_ids = await get_table_ids_from_omd(source_table_names=common_source_table_names)

                    add_trino_query_objects_to_pg(cur=pg_cur, source_table_names=common_source_table_names)
                    trino_query_objects_from_pg = get_trino_query_object_ids_from_pg(
                        cur=pg_cur, source_table_names=common_source_table_names,
                    )

                    common_source_table_names = {table_name: table_id for table_id, table_name in trino_query_objects_from_pg}
                    add_trino_queries_and_query_objects_lnk_to_pg(
                        cur=pg_cur, source_table_names=common_source_table_names, trino_queries=trino_queries,
                    )

                    await send_queries_to_omd(queries=trino_queries, omd_tables_ids=omd_tables_ids)

        except Exception:
            logger.exception("Error querying table")
        finally:
            pg_cur.close()


if __name__ == "__main__":
    logger.warning("Start script")
    asyncio.run(main())
    logger.warning("Finish script")
