from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime


def check_deps():
    import pkg_resources

    installed_packages = [
        f"{dist.key} {dist.version}" for dist in pkg_resources.working_set
    ]
    for pkg in installed_packages:
        print(pkg)


with DAG(
    "check_dependencies", start_date=datetime(2025, 4, 11), schedule_interval=None
) as dag:

    PythonOperator(task_id="list_packages", python_callable=check_deps)
