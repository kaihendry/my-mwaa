import datetime
import json
import subprocess

from airflow import DAG
from airflow.operators.python import PythonOperator


def test_snowflake_connection(**context):
    """Test connecting to Snowflake using key-pair authentication from AWS Secrets Manager.

    This function:
    - Reads Snowflake credentials from AWS Secrets Manager
    - Uses key-pair authentication with private key
    - Connects to Snowflake and runs a test query
    """
    print("=" * 80)
    print("Snowflake Connection Test")
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

    # Step 1: Read secret from AWS Secrets Manager
    secret_name = "mwaa/test-secret"
    print(f"Step 1: Reading secret: {secret_name}")
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
        secret_string = secret_data.get("SecretString", "")

        if not secret_string:
            print("✗ Secret is empty!")
            raise ValueError("Secret has no SecretString")

        secrets = json.loads(secret_string)

        # Extract Snowflake credentials
        sf_account = secrets.get("snowflake_account")
        sf_user = secrets.get("snowflake_user")
        sf_role = secrets.get("snowflake_role")
        sf_private_key = secrets.get("snowflake_private_key")

        print("✓ Secret retrieved successfully!")
        print(f"  Account: {sf_account}")
        print(f"  User: {sf_user}")
        print(f"  Role: {sf_role}")
        print(f"  Private Key: {'Present' if sf_private_key else 'Missing'}")
        print()

        if not all([sf_account, sf_user, sf_role, sf_private_key]):
            missing = []
            if not sf_account:
                missing.append("snowflake_account")
            if not sf_user:
                missing.append("snowflake_user")
            if not sf_role:
                missing.append("snowflake_role")
            if not sf_private_key:
                missing.append("snowflake_private_key")

            print(f"✗ Missing required Snowflake credentials: {', '.join(missing)}")
            raise ValueError(f"Missing credentials: {', '.join(missing)}")

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr
        print("✗ Failed to retrieve secret!")
        print(f"  Error: {error_msg}")
        raise
    except json.JSONDecodeError as e:
        print(f"✗ Error parsing secret: {e}")
        raise

    # Step 2: Prepare private key for Snowflake
    print("Step 2: Processing private key for Snowflake authentication")
    print("─" * 80)

    try:
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import serialization

        # Load the private key
        p_key = serialization.load_pem_private_key(
            sf_private_key.encode("utf-8"),
            password=None,  # No passphrase
            backend=default_backend(),
        )

        # Convert to DER format (required by Snowflake)
        pkb = p_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        print("✓ Private key processed successfully")
        print(f"  Key size: {len(pkb)} bytes")
        print()

    except Exception as e:
        print(f"✗ Error processing private key: {e}")
        raise

    # Step 3: Connect to Snowflake
    print("Step 3: Connecting to Snowflake")
    print("─" * 80)

    try:
        import snowflake.connector

        # Create connection
        conn = snowflake.connector.connect(
            account=sf_account,
            user=sf_user,
            role=sf_role,
            private_key=pkb,
        )

        print("✓ Connected to Snowflake successfully!")
        print()

        # Step 4: Run test queries
        print("Step 4: Running test queries")
        print("─" * 80)

        cursor = conn.cursor()

        # Query 1: SELECT 1
        print("Query 1: SELECT 1")
        cursor.execute("SELECT 1 AS test_value")
        result = cursor.fetchone()
        print(f"  Result: {result[0]}")
        print()

        # Query 2: Get current account info
        print("Query 2: SHOW PARAMETERS LIKE 'ACCOUNT%'")
        cursor.execute("SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE()")
        result = cursor.fetchone()
        print(f"  Account: {result[0]}")
        print(f"  User: {result[1]}")
        print(f"  Role: {result[2]}")
        print()

        # Query 3: Get version
        print("Query 3: SELECT CURRENT_VERSION()")
        cursor.execute("SELECT CURRENT_VERSION()")
        result = cursor.fetchone()
        print(f"  Snowflake Version: {result[0]}")
        print()

        # Query 4: List databases (if permissions allow)
        try:
            print("Query 4: SHOW DATABASES")
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            print(f"  Found {len(databases)} database(s):")
            for db in databases[:5]:  # Show first 5
                print(f"    - {db[1]}")  # database name is in column 1
            if len(databases) > 5:
                print(f"    ... and {len(databases) - 5} more")
            print()
        except Exception as e:
            print(f"  ⚠ Could not list databases: {e}")
            print()

        cursor.close()
        conn.close()

        print("✓ All queries executed successfully!")
        print()
        print("=" * 80)
        print("✓ SNOWFLAKE CONNECTION TEST PASSED!")
        print("=" * 80)

    except Exception as e:
        print(f"✗ Snowflake connection failed: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Verify the Snowflake account identifier is correct")
        print("  2. Ensure the user exists and the public key is registered:")
        print("     ALTER USER TERRAFORM_SVC SET RSA_PUBLIC_KEY='<public_key>'")
        print("  3. Check that the role ACCOUNTADMIN is granted to the user")
        print("  4. Verify network connectivity from MWAA to Snowflake")
        print()
        raise


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
