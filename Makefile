AIRFLOW_VERSION := 2.10.3
PYTHON_VERSION := 3.11
AIRFLOW := KaiAirflowEnvironment
BUCKET := march-dag-mwaa-test

init: requirements.txt
	#aws s3 mb s3://$(BUCKET)
	aws s3 sync --delete --exclude ".*" dags s3://$(BUCKET)/dags/
	aws s3 cp requirements.txt s3://$(BUCKET)/requirements.txt

requirements.txt: pyproject.toml
	curl -L "https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-$(PYTHON_VERSION).txt" > constraints.txt
	uv pip compile pyproject.toml --constraint constraints.txt -o requirements.txt

test:
	uv run airflow dags test -S dags example_sqs

logs:
	aws mwaa get-environment --name $(AIRFLOW) \
        --query 'Environment.LastUpdate.Error.ErrorResponse.Errors[*].ErrorMessage' \
		--output text

pipinstall:
	uv pip install "apache-airflow[celery,cncf.kubernetes,google,amazon,snowflake]==$(AIRFLOW_VERSION)" \
		--constraint \
		"https://raw.githubusercontent.com/apache/airflow/constraints-$(AIRFLOW_VERSION)/constraints-$(PYTHON_VERSION).txt"
