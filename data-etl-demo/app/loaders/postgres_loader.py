from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
from psycopg2.extensions import connection, cursor

class PostgresLoader:
    """Loads data to PostgreSQL data warehouse."""
    
    def __init__(self, connection_string: Optional[str] = None) -> None:
        self.conn_string: str = connection_string or "postgresql://user:pass@localhost/dwh"
    
    def read_from_staging(self, path: str) -> List[Dict[str, Any]]:
        """Read data from staging area."""
        return []
    
    def upsert(self, table: str, data: List[Dict[str, Any]]) -> None:
        """Upsert data to table."""
        if not data:
            return
        
        conn: connection = psycopg2.connect(self.conn_string)
        cur: cursor = conn.cursor()
        
        columns: List[str] = list(data[0].keys())
        query: str = f"INSERT INTO {table} ({','.join(columns)}) VALUES %s"
        
        values: List[List[Any]] = [[row[col] for col in columns] for row in data]
        execute_values(cur, query, values)
        
        conn.commit()
        cur.close()
        conn.close()

