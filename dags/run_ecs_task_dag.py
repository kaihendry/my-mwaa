import boto3
import os
from airflow import DAG
from datetime import datetime
import airflow
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator
from airflow.operators.python import PythonOperator

# Read paramters
CLUSTER_NAME = os.environ.get("AIRFLOW__CDK__CLUSTER_NAME")
TASK_DEFINITION = "foobar-testing"
LOG_GROUP = "/aws/ecs/task/"
LOG_PREFIX = "KE"


def airflow_info():
    airflow_env_arn = (
        "arn:aws:airflow:eu-west-2:160071257600:environment/KaisAirflowEnvironment"
    )
    client = boto3.client("mwaa", region_name="eu-west-2")
    response = client.get_environment(Name=airflow_env_arn.split("/")[-1])
    print("airflow information")
    print(response)

    # Parse and print subnets and security group
    network_config = response.get("Environment", {}).get("NetworkConfiguration", {})
    subnets = network_config.get("SubnetIds", [])
    security_groups = network_config.get("SecurityGroupIds", [])

    print("Subnets:", subnets)
    print("Security Groups:", security_groups)
    print("hello world")


# Run KE Processing task
with DAG(
    dag_id="run_ecs_task_dag",
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["versioning"],
) as dag:
    # Fetch networking info from the Airflow environment
    # requires airflow:GetEnvironment permissions

    print_info = PythonOperator(
        task_id="print_system_info", python_callable=airflow_info
    )

    KE_PROCESSING_TASK = EcsRunTaskOperator(
        task_id="KE_PROCESSING_TASK",
        task_definition=TASK_DEFINITION,
        cluster=CLUSTER_NAME,
        launch_type="FARGATE",
        network_configuration={
            "awsvpcConfiguration": {
                "securityGroups": ["sg-0cd64c4d346727558"],
                "subnets": ["subnet-053b2780dafc39ad8", "subnet-0831f5e120087dc7b"],
            },
        },
        overrides={
            "containerOverrides": [],
        },
        awslogs_group=LOG_GROUP,
        awslogs_stream_prefix=LOG_PREFIX,
        wait_for_completion=True,
    )
