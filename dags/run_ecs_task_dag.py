import boto3
from airflow import DAG
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator
from airflow.utils.dates import days_ago

# Read paramters
CLUSTER_NAME = "KAIELMO"
TASK_DEFINITION = "foobar-testing"
LOG_GROUP = "/aws/ecs/task/"
LOG_PREFIX = "KE"

# Run KE Processing task
with DAG(
    dag_id="run_ecs_task_dag-1127",
    schedule_interval=None,
    catchup=False,
    start_date=days_ago(1),
) as dag:
    KE_PROCESSING_TASK = EcsRunTaskOperator(
        task_id="KE_PROCESSING_TASK",
        task_definition=TASK_DEFINITION,
        cluster=CLUSTER_NAME,
        launch_type="FARGATE",
        network_configuration={
            "awsvpcConfiguration": {
                "securityGroups": ["sg-03fab90cb34b89959"],
                "subnets": ["subnet-01aec0913b39ce651", "subnet-0c1e6f247fdf204d0"],
            },
        },
        overrides={
            "containerOverrides": [],
        },
        awslogs_group=LOG_GROUP,
        awslogs_stream_prefix=LOG_PREFIX,
        wait_for_completion=True,
    )
