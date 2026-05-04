import logging
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from app.storage.s3_storage import LocalStorage

logger = logging.getLogger(__name__)


class PostgresLoader:
    """Loads data to PostgreSQL data warehouse."""

    def __init__(self, connection_string: str | None = None) -> None:
        self.conn_string = connection_string or "postgresql://user:pass@localhost/dwh"
        self._storage = LocalStorage()

    def read_from_staging(self, path: str) -> list[dict[str, Any]]:
        """Read data from local staging area."""
        return self._storage.load(path)

    def upsert(self, table: str, data: list[dict[str, Any]]) -> None:
        """Upsert data to table using safe SQL identifier quoting."""
        if not data:
            logger.info("No data to upsert into %s", table)
            return

        columns = list(data[0].keys())

        # Build safe SQL with quoted identifiers
        table_parts = table.split(".")
        table_id = sql.SQL(".").join(sql.Identifier(part) for part in table_parts)
        columns_id = sql.SQL(",").join(sql.Identifier(col) for col in columns)
        query = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(table_id, columns_id)

        values = [[row[col] for col in columns] for row in data]

        conn = psycopg2.connect(self.conn_string)
        try:
            with conn.cursor() as cur:
                execute_values(cur, query, values)
                conn.commit()
                logger.info("Upserted %d rows into %s", len(data), table)
        except Exception:
            conn.rollback()
            logger.exception("Failed to upsert into %s", table)
            raise
        finally:
            conn.close()
