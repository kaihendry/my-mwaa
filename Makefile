init: format requirements
	#- aws s3 mb s3://march-dag-mwaa-test
	aws s3 sync --delete --exclude ".*" . s3://march-dag-mwaa-test 

format: 
	uvx black dags/

requirements:
	uv export -o requirements.txt

test: format
	uv run airflow dags test -S dags my_dag_name

logs:
	aws mwaa get-environment --name TryAirflowEnvironment \
        --query 'Environment.LastUpdate.Error.ErrorResponse.Errors[*].ErrorMessage' \
		--output text	