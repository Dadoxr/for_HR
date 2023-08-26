from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from app.extractors.api_extractor import APIExtractor
from app.storage.s3_storage import S3Storage

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
    'extract_api_data',
    default_args=default_args,
    description='Extract data from external APIs',
    schedule_interval='@daily',
    catchup=False
)

def extract_users(**context):
    """Extract user data from API"""
    extractor = APIExtractor()
    storage = S3Storage()
    
    data = extractor.fetch('users')
    storage.save('raw/users', data)
    
    return {'records': len(data)}

def extract_orders(**context):
    """Extract order data from API"""
    extractor = APIExtractor()
    storage = S3Storage()
    
    data = extractor.fetch('orders')
    storage.save('raw/orders', data)
    
    return {'records': len(data)}

extract_users_task = PythonOperator(
    task_id='extract_users',
    python_callable=extract_users,
    dag=dag
)

extract_orders_task = PythonOperator(
    task_id='extract_orders',
    python_callable=extract_orders,
    dag=dag
)

extract_users_task >> extract_orders_task

