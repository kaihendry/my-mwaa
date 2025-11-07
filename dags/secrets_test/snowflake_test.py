import datetime
import json

import boto3
from airflow import DAG
from airflow.operators.python import PythonOperator


def get_secret(secret_name, region="eu-west-2"):
    """Retrieve secret from AWS Secrets Manager using boto3."""
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def process_private_key(private_key_pem):
    """Convert PEM private key to DER format for Snowflake."""
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    p_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"), password=None, backend=default_backend()
    )
    return p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def test_snowflake_connection(**context):
    """Test Snowflake connection using key-pair authentication from AWS Secrets Manager."""
    import snowflake.connector

    # Print trigger info
    dag_run = context.get("dag_run", {})
    conf = dag_run.conf or {} if dag_run else {}
    triggered_by = conf.get("triggered_by", "Manual" if dag_run and dag_run.run_type == "manual" else "Unknown")

    print(f"{'='*80}")
    print(f"Snowflake Connection Test - Triggered by: {triggered_by}")
    print(f"{'='*80}\n")

    # Fetch credentials from Secrets Manager
    print("📦 Fetching credentials from AWS Secrets Manager...")
    secrets = get_secret("mwaa/test-secret")

    required_keys = ["snowflake_account", "snowflake_user", "snowflake_role", "snowflake_private_key"]
    missing = [k for k in required_keys if not secrets.get(k)]
    if missing:
        raise ValueError(f"Missing credentials: {', '.join(missing)}")

    print(f"✓ Account: {secrets['snowflake_account']}")
    print(f"✓ User: {secrets['snowflake_user']}\n")

    # Process private key
    print("🔐 Processing private key...")
    private_key_bytes = process_private_key(secrets["snowflake_private_key"])
    print(f"✓ Key processed ({len(private_key_bytes)} bytes)\n")

    # Connect to Snowflake
    print("🔗 Connecting to Snowflake...")
    with snowflake.connector.connect(
        account=secrets["snowflake_account"],
        user=secrets["snowflake_user"],
        role=secrets["snowflake_role"],
        private_key=private_key_bytes,
    ) as conn:
        print("✓ Connected!\n")

        with conn.cursor() as cursor:
            # Test query
            cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE(), CURRENT_VERSION()")
            account, user, role, version = cursor.fetchone()
            print(f"Account:  {account}")
            print(f"User:     {user}")
            print(f"Role:     {role}")
            print(f"Version:  {version}\n")

            # List databases
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print(f"Databases: {len(databases)} found")
            for db in databases[:5]:
                print(f"  • {db[1]}")
            if len(databases) > 5:
                print(f"  ... and {len(databases) - 5} more\n")

    print(f"{'='*80}")
    print("✓ SNOWFLAKE CONNECTION TEST PASSED!")
    print(f"{'='*80}")


with DAG(
    dag_id="snowflake_test",
    start_date=datetime.datetime.now(),
    schedule=None,  # Only run when manually triggered
    catchup=False,
    tags=["snowflake", "secrets", "testing"],
    description="Test Snowflake connection using key-pair authentication from AWS Secrets Manager",
):
    test_connection = PythonOperator(
        task_id="test_snowflake_connection",
        python_callable=test_snowflake_connection,
    )
