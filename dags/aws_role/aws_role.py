import datetime
import json
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator


def print_aws_role(**context):
    """Print AWS role information from the Airflow runtime environment.

    This function detects how the DAG was triggered:
    - Via Makefile/script: Uses dag_run.conf with 'triggered_by' (from $USER env var)
    - Via Airflow UI: Detected as run_type='manual' with no conf
    - Via Scheduler: Detected as run_type='scheduled'
    """
    print("=" * 80)
    print("AWS Role Information")
    print("=" * 80)
    print()

    # Get DAG run context information
    dag_run = context.get("dag_run")
    if dag_run:
        print("DAG Run Trigger Information:")
        print(f"  Run ID:       {dag_run.run_id}")
        print(f"  Run Type:     {dag_run.run_type}")
        print(f"  Logical Date: {dag_run.logical_date}")

        # Check if triggered with configuration (from script or API)
        conf = dag_run.conf or {}
        if conf:
            triggered_by = conf.get("triggered_by", "N/A")
            trigger_source = conf.get("trigger_source", "N/A")
            timestamp = conf.get("timestamp", "N/A")

            print(f"  Triggered By: {triggered_by}")
            print(f"  Trigger Source: {trigger_source}")
            print(f"  Trigger Time: {timestamp}")
        else:
            # Manual trigger from UI or scheduled
            if dag_run.run_type == "manual":
                print("  Triggered By: Manual trigger from Airflow UI")
            elif dag_run.run_type == "scheduled":
                print("  Triggered By: Airflow Scheduler")
            else:
                print(f"  Triggered By: {dag_run.run_type}")
        print()

    try:
        # Get caller identity using AWS CLI
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=True,
        )

        identity = json.loads(result.stdout)

        print("AWS STS Caller Identity:")
        print(f"  User ID:  {identity.get('UserId', 'N/A')}")
        print(f"  Account:  {identity.get('Account', 'N/A')}")
        print(f"  ARN:      {identity.get('Arn', 'N/A')}")
        print()

        # Extract role name from ARN if it's a role
        arn = identity.get("Arn", "")
        if "assumed-role" in arn:
            role_name = arn.split("/")[-2] if "/" in arn else "Unknown"
            print(f"  Role Name: {role_name}")
        elif "role/" in arn:
            role_name = arn.split("/")[-1] if "/" in arn else "Unknown"
            print(f"  Role Name: {role_name}")
        else:
            print("  Note: Not running as an IAM role")

        print()
        print("Raw JSON Response:")
        print(json.dumps(identity, indent=2))

    except subprocess.CalledProcessError as e:
        print(f"Error executing AWS CLI: {e}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
    except json.JSONDecodeError as e:
        print(f"Error parsing AWS CLI output: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    print()
    print("=" * 80)


with DAG(
    dag_id="aws_role_info",
    start_date=datetime.datetime.now(),
    schedule=None,  # Only run when manually triggered
    catchup=False,
    tags=["aws", "info", "debugging"],
    description="Print AWS role information from the Airflow runtime environment",
):
    check_role = PythonOperator(
        task_id="print_aws_role_info",
        python_callable=print_aws_role,
    )
