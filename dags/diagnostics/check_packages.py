import datetime
import subprocess
import sys

from airflow import DAG
from airflow.operators.python import PythonOperator


def check_installed_packages(**context):
    """Check installed Python packages and environment details."""
    print("=" * 80)
    print("MWAA Python Environment Diagnostics")
    print("=" * 80)
    print()

    # Get DAG run context information
    dag_run = context.get("dag_run")
    if dag_run:
        print("DAG Run Information:")
        print(f"  Run ID:       {dag_run.run_id}")
        print(f"  Run Type:     {dag_run.run_type}")

        conf = dag_run.conf or {}
        if conf:
            triggered_by = conf.get("triggered_by", "N/A")
            trigger_source = conf.get("trigger_source", "N/A")
            print(f"  Triggered By: {triggered_by}")
            print(f"  Trigger Source: {trigger_source}")
        else:
            if dag_run.run_type == "manual":
                print("  Triggered By: Manual trigger from Airflow UI")
        print()

    # Python version
    print("Python Environment:")
    print(f"  Python Version: {sys.version}")
    print(f"  Python Path:    {sys.executable}")
    print()

    # Check specific packages we care about
    print("Key Packages:")
    print("─" * 80)

    key_packages = [
        "apache-airflow",
        "boto3",
        "snowflake-connector-python",
        "cryptography",
        "pyopenssl",
        "structlog",
    ]

    for package_name in key_packages:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                # Extract version from pip show output
                lines = result.stdout.split('\n')
                for line in lines:
                    if line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                        print(f"  ✓ {package_name:30s} {version}")
                        break
            else:
                print(f"  ✗ {package_name:30s} NOT INSTALLED")
        except Exception as e:
            print(f"  ✗ {package_name:30s} ERROR: {e}")

    print()

    # List ALL installed packages
    print("All Installed Packages (pip freeze):")
    print("─" * 80)

    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "freeze"],
            capture_output=True,
            text=True,
            check=True,
        )

        packages = result.stdout.strip().split('\n')
        print(f"Total packages: {len(packages)}")
        print()

        # Show all packages
        for package in sorted(packages):
            print(f"  {package}")

    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to list packages: {e}")
        print(f"  STDERR: {e.stderr}")

    print()
    print("=" * 80)
    print("End of Diagnostics")
    print("=" * 80)


with DAG(
    dag_id="check_packages",
    start_date=datetime.datetime.now(),
    schedule=None,
    catchup=False,
    tags=["diagnostics", "debug", "packages"],
    description="Check installed Python packages in MWAA environment",
):
    check_packages = PythonOperator(
        task_id="check_installed_packages",
        python_callable=check_installed_packages,
    )
