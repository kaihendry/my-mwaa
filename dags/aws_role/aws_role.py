import datetime
import json
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator


def print_aws_role():
    """Print AWS role information from the Airflow runtime environment."""
    print("=" * 80)
    print("AWS Role Information")
    print("=" * 80)
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
