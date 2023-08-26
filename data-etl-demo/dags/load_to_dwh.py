from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from datetime import datetime, timedelta
from app.loaders.postgres_loader import PostgresLoader

default_args = {
    'owner': 'data_engineer',
    'depends_on_past': True,
    'start_date': datetime(2024, 1, 1),
    'retries': 2
}

dag = DAG(
    'load_to_dwh',
    default_args=default_args,
    description='Load processed data to PostgreSQL DWH',
    schedule_interval='@daily',
    catchup=False
)

def load_users(**context):
    """Load user aggregates to DWH"""
    loader = PostgresLoader()
    
    data = loader.read_from_staging('staging/users')
    loader.upsert('analytics.user_stats', data)
    
    return {'loaded': len(data)}

def load_orders(**context):
    """Load order metrics to DWH"""
    loader = PostgresLoader()
    
    data = loader.read_from_staging('staging/orders')
    loader.upsert('analytics.daily_revenue', data)
    
    return {'loaded': len(data)}

create_tables = PostgresOperator(
    task_id='create_tables',
    postgres_conn_id='postgres_dwh',
    sql='''
    CREATE TABLE IF NOT EXISTS analytics.user_stats (
        registration_year INT,
        user_count BIGINT,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS analytics.daily_revenue (
        user_id INT,
        date DATE,
        daily_revenue DECIMAL(10,2),
        order_count INT,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    ''',
    dag=dag
)

load_users_task = PythonOperator(
    task_id='load_users',
    python_callable=load_users,
    dag=dag
)

load_orders_task = PythonOperator(
    task_id='load_orders',
    python_callable=load_orders,
    dag=dag
)

create_tables >> [load_users_task, load_orders_task]

