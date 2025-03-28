import datetime
import os
import sys
import platform
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator


def print_system_info():
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_name = Path(__file__).name
    env = os.getenv("AIRFLOW_ENV", "production")
    python_version = sys.version
    platform_info = platform.platform()

    print(
        f"""
System Information:
------------------
Current Time: {current_time}
File Name: {file_name}
Environment: {env}
Python Version: {python_version}
Platform: {platform_info}
Working Directory: {os.getcwd()}
    """
    )


with DAG(
    dag_id="my_dag_name",
    start_date=datetime.datetime(2021, 1, 1),
    schedule="@daily",
):
    print_info = PythonOperator(
        task_id="print_system_info", python_callable=print_system_info
    )
