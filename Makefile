init: format
	- aws s3 mb s3://march-dag-mwaa-test
	aws s3 sync --exclude ".*" . s3://march-dag-mwaa-test

format: 
	uvx black dags/

test: format
	uv run airflow dags test -S dags my_dag_name