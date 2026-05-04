import logging
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from app.loaders.postgres_loader import PostgresLoader

logger = logging.getLogger(__name__)

default_args = {
    "owner": "data_engineer",
    "depends_on_past": True,
    "start_date": datetime(2024, 1, 1),
    "retries": 2,
}

dag = DAG(
    "load_to_dwh",
    default_args=default_args,
    description="Load processed data from staging to PostgreSQL DWH",
    schedule_interval="@daily",
    catchup=False,
)


def load_entity(staging_path: str, target_table: str, **context) -> dict:
    """Generic load task: read from staging and upsert to DWH."""
    loader = PostgresLoader()

    try:
        data = loader.read_from_staging(staging_path)
        if not data:
            logger.warning("No data in staging for %s", staging_path)
            return {"loaded": 0}

        loader.upsert(target_table, data)
        logger.info("Loaded %d records into %s", len(data), target_table)
        return {"loaded": len(data)}
    except Exception:
        logger.exception("Failed to load %s into %s", staging_path, target_table)
        raise


create_tables = PostgresOperator(
    task_id="create_tables",
    postgres_conn_id="postgres_dwh",
    sql="""
    CREATE SCHEMA IF NOT EXISTS analytics;

    CREATE TABLE IF NOT EXISTS analytics.user_stats (
        registration_year INT PRIMARY KEY,
        user_count BIGINT,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS analytics.daily_revenue (
        user_id INT,
        date DATE,
        daily_revenue DECIMAL(10,2),
        order_count INT,
        updated_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (user_id, date)
    );
    """,
    dag=dag,
)

load_users_task = PythonOperator(
    task_id="load_users",
    python_callable=load_entity,
    op_kwargs={
        "staging_path": "staging/users",
        "target_table": "analytics.user_stats",
    },
    dag=dag,
)

load_orders_task = PythonOperator(
    task_id="load_orders",
    python_callable=load_entity,
    op_kwargs={
        "staging_path": "staging/orders",
        "target_table": "analytics.daily_revenue",
    },
    dag=dag,
)

create_tables >> [load_users_task, load_orders_task]
