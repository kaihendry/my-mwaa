import os
import subprocess
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime


def get_git_commit():
    try:
        process = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return process.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


GIT_COMMIT_HASH = get_git_commit()

with DAG(
    dag_id="my_dag_with_git_hash",
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["versioning"],
    default_args={"owner": "airflow", "git_commit": GIT_COMMIT_HASH},
) as dag:
    log_version_task = BashOperator(
        task_id="log_git_version",
        bash_command=f'echo "DAG Version (Git Commit): {GIT_COMMIT_HASH}"',
    )

