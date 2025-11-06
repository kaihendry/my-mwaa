import datetime
import json
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator


def read_secrets(**context):
    """Read secrets from AWS Secrets Manager.

    This function detects how the DAG was triggered and then reads
    a test secret from AWS Secrets Manager to verify permissions.
    """
    print("=" * 80)
    print("AWS Secrets Manager Test")
    print("=" * 80)
    print()

    # Get DAG run context information
    dag_run = context.get("dag_run")
    if dag_run:
        print("DAG Run Trigger Information:")
        print(f"  Run ID:       {dag_run.run_id}")
        print(f"  Run Type:     {dag_run.run_type}")

        # Check if triggered with configuration
        conf = dag_run.conf or {}
        if conf:
            triggered_by = conf.get("triggered_by", "N/A")
            trigger_source = conf.get("trigger_source", "N/A")
            print(f"  Triggered By: {triggered_by}")
            print(f"  Trigger Source: {trigger_source}")
        else:
            if dag_run.run_type == "manual":
                print("  Triggered By: Manual trigger from Airflow UI")
            elif dag_run.run_type == "scheduled":
                print("  Triggered By: Airflow Scheduler")
        print()

    # First, verify our AWS identity
    print("Current AWS Identity:")
    try:
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=True,
        )
        identity = json.loads(result.stdout)
        print(f"  ARN: {identity.get('Arn', 'N/A')}")
        print()
    except Exception as e:
        print(f"  Error getting identity: {e}")
        print()

    # Read secret from AWS Secrets Manager
    secret_name = "mwaa/test-secret"
    print(f"Reading secret: {secret_name}")
    print("─" * 80)

    try:
        result = subprocess.run(
            [
                "aws",
                "secretsmanager",
                "get-secret-value",
                "--secret-id",
                secret_name,
                "--region",
                "eu-west-2",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        secret_data = json.loads(result.stdout)

        print("✓ Secret retrieved successfully!")
        print()
        print("Secret Metadata:")
        print(f"  Name:          {secret_data.get('Name', 'N/A')}")
        print(f"  ARN:           {secret_data.get('ARN', 'N/A')}")
        print(f"  Created:       {secret_data.get('CreatedDate', 'N/A')}")
        print(f"  Version:       {secret_data.get('VersionId', 'N/A')}")
        print()

        # Parse the secret value
        secret_string = secret_data.get("SecretString", "")
        if secret_string:
            try:
                secret_json = json.loads(secret_string)
                print("Secret Contents:")
                for key, value in secret_json.items():
                    # Mask sensitive values partially
                    if len(str(value)) > 10:
                        masked_value = f"{str(value)[:4]}...{str(value)[-4:]}"
                    else:
                        masked_value = "***"
                    print(f"  {key}: {masked_value}")
            except json.JSONDecodeError:
                # Not JSON, treat as plain text
                print("Secret Contents (plain text):")
                if len(secret_string) > 20:
                    print(f"  {secret_string[:10]}...{secret_string[-10:]}")
                else:
                    print(f"  {'*' * len(secret_string)}")
        else:
            print("Secret Contents: (binary data)")

        print()
        print("✓ Secret access test PASSED!")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr
        print("✗ Failed to retrieve secret!")
        print()
        print("Error Details:")
        print(f"  {error_msg}")
        print()

        if "AccessDenied" in error_msg or "AccessDeniedException" in error_msg:
            print("Troubleshooting:")
            print("  1. Verify the MWAA execution role has secretsmanager:GetSecretValue permission")
            print("  2. Check the secret's resource policy allows the MWAA role")
            print("  3. Run: bash scripts/setup-secret.sh")
        elif "ResourceNotFoundException" in error_msg:
            print("Troubleshooting:")
            print("  1. The secret does not exist")
            print("  2. Run: bash scripts/setup-secret.sh")
        else:
            print("Troubleshooting:")
            print("  1. Check AWS credentials and permissions")
            print("  2. Verify the secret exists in the correct region (eu-west-2)")

        print()
        raise

    except json.JSONDecodeError as e:
        print(f"✗ Error parsing secret response: {e}")
        raise
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        raise

    print("=" * 80)


with DAG(
    dag_id="secrets_test",
    start_date=datetime.datetime.now(),
    schedule=None,  # Only run when manually triggered
    catchup=False,
    tags=["aws", "secrets", "testing"],
    description="Test reading secrets from AWS Secrets Manager",
):
    test_secrets = PythonOperator(
        task_id="read_aws_secrets",
        python_callable=read_secrets,
    )
