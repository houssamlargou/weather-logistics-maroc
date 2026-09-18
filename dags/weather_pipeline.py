from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator


def hello_world():
    print("Airflow is working.")


default_args = {
    "owner": "ycode",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="weather_pipeline",
    description="Daily weather ETL for Moroccan cities",
    start_date=datetime(2026, 9, 1),
    schedule="@daily",
    catchup=False,
    default_args=default_args,
    tags=["weather", "etl"],
) as dag:

    task_hello = PythonOperator(
        task_id="hello_world",
        python_callable=hello_world,
    )