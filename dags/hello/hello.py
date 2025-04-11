# Version: 0.0.0
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
    # get all env vars
    env = os.environ
    python_version = sys.version
    platform_info = platform.platform()

    # print all env vars
    print("Environment Variables:")
    for key, value in env.items():
        print(f"{key}: {value}")

    # print sys info
    print("System Information:")
    print(f"Current Time: {current_time}")
    print(f"File Name: {file_name}")
    print(f"Python Version: {python_version}")
    print(f"Platform Info: {platform_info}")


with DAG(
    dag_id="my_dag_name",
    start_date=datetime.datetime.now(),
    catchup=False,
):
    print_info = PythonOperator(
        task_id="print_system_info", python_callable=print_system_info
    )
