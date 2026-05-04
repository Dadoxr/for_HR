import logging
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from app.extractors.api_extractor import APIExtractor
from app.storage.s3_storage import LocalStorage

logger = logging.getLogger(__name__)

default_args = {
    "owner": "data_engineer",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "extract_api_data",
    default_args=default_args,
    description="Extract users and orders data from external APIs to local staging",
    schedule_interval="@daily",
    catchup=False,
)


def extract_entity(endpoint: str, staging_path: str, **context) -> dict:
    """Generic extraction task: fetch from API and save to staging."""
    extractor = APIExtractor()
    storage = LocalStorage()

    try:
        data = extractor.fetch(endpoint)
        storage.save(staging_path, data)
        logger.info("Extracted %d records for %s", len(data), endpoint)
        return {"records": len(data)}
    except Exception:
        logger.exception("Failed to extract %s", endpoint)
        raise


extract_users_task = PythonOperator(
    task_id="extract_users",
    python_callable=extract_entity,
    op_kwargs={"endpoint": "users", "staging_path": "raw/users"},
    dag=dag,
)

extract_orders_task = PythonOperator(
    task_id="extract_orders",
    python_callable=extract_entity,
    op_kwargs={"endpoint": "orders", "staging_path": "raw/orders"},
    dag=dag,
)

extract_users_task >> extract_orders_task
