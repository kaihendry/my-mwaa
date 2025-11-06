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
