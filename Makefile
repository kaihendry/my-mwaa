AIRFLOW_VERSION := 2.10.3
PYTHON_VERSION := 3.11

init: format requirements.txt
	#aws s3 mb s3://march-dag-mwaa-test
	aws s3 sync --delete --exclude ".*" . s3://march-dag-mwaa-test

format:
	uvx black dags/

requirements.txt:
	uv export -o requirements.txt

test: format
	uv run airflow dags test -S dags my_dag_name

logs:
	aws mwaa get-environment --name TryAirflowEnvironment \
        --query 'Environment.LastUpdate.Error.ErrorResponse.Errors[*].ErrorMessage' \
		--output text

pipinstall:
	uv pip install "apache-airflow[celery,cncf.kubernetes,google,amazon,snowflake]==$(AIRFLOW_VERSION)" \
		--constraint \
		"https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-$(PYTHON_VERSION).txt"
