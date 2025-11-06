"""
A DAG that intentionally fails to test error handling and logging.
"""

from datetime import datetime
from airflow import DAG
from airflow.operators.python import PythonOperator


def task_that_fails(**context):
    """A task that intentionally raises an exception."""
    print("=" * 60)
    print("Starting task execution...")
    print("=" * 60)

    # Print some context
    print("\nDAG Run Info:")
    print(f"  DAG ID: {context['dag'].dag_id}")
    print(f"  Task ID: {context['task'].task_id}")
    print(f"  Execution Date: {context['execution_date']}")
    print(f"  Run ID: {context['dag_run'].run_id}")

    # Check if this was triggered by our script
    conf = context['dag_run'].conf or {}
    if conf:
        print(f"\nTriggered by: {conf.get('triggered_by', 'unknown')}")
        print(f"Trigger source: {conf.get('trigger_source', 'unknown')}")
        print(f"Timestamp: {conf.get('timestamp', 'unknown')}")

    print("\n" + "=" * 60)
    print("SIMULATING FAILURE")
    print("=" * 60)

    # Simulate some processing before the error
    print("\nProcessing step 1: Loading data... OK")
    print("Processing step 2: Validating input... OK")
    print("Processing step 3: Performing calculation...")

    # Now raise an exception
    print("\n❌ ERROR: Division by zero occurred!")
    print("This is an intentional error to demonstrate failure handling.\n")

    raise ZeroDivisionError(
        "Intentional failure: Cannot divide by zero! "
        "This error is expected and used for testing error handling."
    )


# Create the DAG
with DAG(
    dag_id="failing_dag",
    description="A DAG that fails intentionally for testing",
    schedule=None,  # Manual trigger only
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["testing", "error-handling", "demo"],
) as dag:

    fail_task = PythonOperator(
        task_id="intentional_failure",
        python_callable=task_that_fails,
        provide_context=True,
    )
