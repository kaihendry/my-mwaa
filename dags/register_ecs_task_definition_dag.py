import os
import boto3
from airflow import DAG
from airflow.providers.amazon.aws.operators.ecs import EcsRegisterTaskDefinitionOperator
from airflow.utils.dates import days_ago

# ECR image URI - amazon
AWS_IMAGE = "amazonlinux:latest"
# ECS task
ECS_TASK_ROLE_ARN = "arn:aws:iam::160071257600:role/ecs-tasks-service-role"
# Family Name
FAMILY_NAME = "foobar-testing"

# DAG for Registering ECS Task definition
with DAG(
    dag_id="register_ecs_task_definition_dag-2",
    schedule_interval=None,
    catchup=False,
    start_date=days_ago(1),
) as dag:
    # Create ECS Task Definition
    # https://docs.aws.amazon.com/AmazonECS/latest/APIReference/API_TaskDefinition.html
    KE_TASK = EcsRegisterTaskDefinitionOperator(
        task_id="KE_TASK",
        family=FAMILY_NAME,
        container_definitions=[{"name": "aws-processing-image", "image": AWS_IMAGE}],
        register_task_kwargs={
            "cpu": "256",
            "memory": "512",
            "networkMode": "awsvpc",
            "executionRoleArn": ECS_TASK_ROLE_ARN,
            "requiresCompatibilities": ["FARGATE"],
        },
    )
