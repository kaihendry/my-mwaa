init: format requirements.txt
	#- aws s3 mb s3://march-dag-mwaa-test
	aws s3 sync --delete --exclude ".*" . s3://march-dag-mwaa-test 

format: 
	uvx black dags/

requirements.txt:
	curl -o constraints.txt https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.11.txt
	uv export -o requirements.txt
	uv pip compile requirements.txt --constraint constraints.txt

test: format
	uv run airflow dags test -S dags my_dag_name

logs:
	aws mwaa get-environment --name TryAirflowEnvironment \
        --query 'Environment.LastUpdate.Error.ErrorResponse.Errors[*].ErrorMessage' \
		--output text	