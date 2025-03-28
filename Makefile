init:
	- aws s3 mb s3://march-dag-mwaa-test
	aws s3 sync --exclude ".git*" . s3://march-dag-mwaa-test
