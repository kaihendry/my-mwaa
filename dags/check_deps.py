from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import structlog


def check_deps():
    import pkg_resources

    logger = structlog.get_logger()

    installed_packages = [
        f"{dist.key} {dist.version}" for dist in pkg_resources.working_set
    ]

    logger.info("Checking installed packages", package_count=len(installed_packages))

    for pkg in installed_packages:
        logger.info("Package installed", package=pkg)


with DAG(
    "check_dependencies", start_date=datetime(2025, 4, 11), schedule_interval=None
) as dag:

    PythonOperator(task_id="list_packages", python_callable=check_deps)
