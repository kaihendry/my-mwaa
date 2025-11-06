AIRFLOW_VERSION := 2.10.3
PYTHON_VERSION := 3.11
MONTH=nov

init: format requirements.txt
	- aws s3 mb s3://$(MONTH)-dag-mwaa-test
	aws s3 sync --delete --exclude ".*" --exclude "*.pyc" dags s3://$(MONTH)-dag-mwaa-test/dags
	aws s3 cp requirements.txt s3://$(MONTH)-dag-mwaa-test/requirements.txt

requirements.txt: pyproject.toml
	curl -L "https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-$(PYTHON_VERSION).txt" > constraints.txt
	uv pip compile pyproject.toml --constraint constraints.txt -o requirements.txt

format:
	uvx ruff check dags/

test: format
	uv run airflow dags test -S dags my_dag_name
	uv run airflow dags test -S dags my_dag_with_git_hash

trigger-dag:
	@echo "Triggering DAG on MWAA..."
	@echo "Environment: $(MWAA_ENVIRONMENT_NAME)"
	@echo "DAG: $(DAG_ID)"
	AWS_REGION=$(AWS_REGION) \
	MWAA_ENVIRONMENT_NAME=$(MWAA_ENVIRONMENT_NAME) \
	DAG_ID=$(DAG_ID) \
	TIMEOUT_MINUTES=$(TIMEOUT_MINUTES) \
	python3 scripts/trigger_and_wait.py

# Default values for trigger-dag (can be overridden)
AWS_REGION ?= eu-west-2
MWAA_ENVIRONMENT_NAME ?= MyAirflowEnvironment
DAG_ID ?= my_dag_name
TIMEOUT_MINUTES ?= 10
S3_BUCKET ?= $(MONTH)-dag-mwaa-test

# Configure MWAA environment with requirements.txt and enable DAGs by default
configure-mwaa:
	@echo "Configuring MWAA environment: $(MWAA_ENVIRONMENT_NAME)"
	@echo "1. Setting requirements.txt path..."
	aws mwaa update-environment \
		--name $(MWAA_ENVIRONMENT_NAME) \
		--region $(AWS_REGION) \
		--requirements-s3-path requirements.txt \
		--airflow-configuration-options "core.dags_are_paused_at_creation=False"
	@echo "Configuration update initiated. This will take 20-30 minutes to complete."
	@echo "Monitor status with: make check-mwaa-status"

# Check MWAA environment status
check-mwaa-status:
	@aws mwaa get-environment \
		--name $(MWAA_ENVIRONMENT_NAME) \
		--region $(AWS_REGION) \
		--query 'Environment.{Status:Status,LastUpdate:LastUpdate.Status,RequirementsS3Path:RequirementsS3Path,AirflowConfigurationOptions:AirflowConfigurationOptions}' \
		--output table

# Quick trigger for aws_role_info DAG
check-aws-role:
	@echo "Checking AWS role in MWAA runtime..."
	AWS_REGION=$(AWS_REGION) \
	MWAA_ENVIRONMENT_NAME=$(MWAA_ENVIRONMENT_NAME) \
	DAG_ID=aws_role_info \
	TIMEOUT_MINUTES=5 \
	uv run scripts/trigger_and_wait.py

# Test secrets access in MWAA
test-secrets:
	@echo "Testing AWS Secrets Manager access..."
	AWS_REGION=$(AWS_REGION) \
	MWAA_ENVIRONMENT_NAME=$(MWAA_ENVIRONMENT_NAME) \
	DAG_ID=secrets_test \
	TIMEOUT_MINUTES=5 \
	uv run scripts/trigger_and_wait.py

# Setup secrets for testing
setup-secrets:
	@echo "Setting up AWS Secrets Manager for MWAA..."
	bash scripts/setup-secret.sh

# Cleanup secrets
cleanup-secrets:
	@echo "Cleaning up AWS Secrets Manager resources..."
	bash scripts/cleanup-secret.sh
