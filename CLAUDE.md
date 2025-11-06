# CLAUDE.md

## Project Overview

This is a playground to better understand AWS MWAA (Managed Airflow) and associated DAG Operators.

We manually provision in the AWS console the [latest version 2.10.3 with Python
3.11](https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html).
We use the Wizard to create the VPC and all logging is enabled to debug
requirements.txt issue with our test bucket: s3://march-dag-mwaa-test

https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/operators/sqs.html

## AWS Environment

mwaa $ aws sts get-caller-identity
{
    "UserId": "AROASKRH5RYAHBKRAPZGL:kai.hendry@thoughtworks.com",
    "Account": "160071257600",
    "Arn": "arn:aws:sts::160071257600:assumed-role/AWSReservedSSO_PowerUserPlusRole_db88d920cf78a35f/kai.hendry@thoughtworks.com"
}
mwaa $ aws mwaa list-environments
{
    "Environments": [
        "MyAirflowEnvironment"
    ]
}

This is AWS Managed Airflow 2.x test environment using the AWS_PROFILE
PowerUserPlusRole-160071257600 which needs to be renewed every hour, via
`assume`.

Use uv for Python packaging and management https://docs.astral.sh/uv

## GitHub Actions: Deploy and Test DAGs

We have two GitHub Actions workflows that automatically test DAG execution:

### 1. Test Positive Case (`.github/workflows/test-positive.yml`)

Tests successful DAG execution:
- ✅ Deploys DAGs to S3 on push to main branch
- ✅ Triggers `my_dag_name` (expected to succeed)
- ✅ Waits for completion with inline logs
- ✅ Reports success/failure
- ✅ Shows who triggered it (${{ github.actor }})

### 2. Test Negative Case (`.github/workflows/test-negative.yml`)

Tests error detection and handling:
- ✅ Deploys DAGs to S3 on push to main branch
- ✅ Triggers `failing_dag` (expected to fail)
- ✅ Verifies the failure is detected (exit code 1)
- ✅ **Workflow passes** if DAG fails as expected
- ✅ Shows error logs inline with highlighting

Both workflows run automatically on push to main and can be triggered manually via workflow_dispatch.

### Required GitHub Secrets

Navigate to: Repository Settings → Secrets and Variables → Actions → New repository secret

Add the following secrets:

- **AWS_ACCESS_KEY_ID**: IAM user access key with permissions for:
  - `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on S3 bucket
  - `airflow:CreateCliToken` on MWAA environment
  - `logs:GetLogEvents` for CloudWatch logs

- **AWS_SECRET_ACCESS_KEY**: IAM user secret access key

### Configuration

The workflows use these environment variables:

```yaml
AWS_REGION: eu-west-2
MWAA_ENVIRONMENT_NAME: MyAirflowEnvironment
S3_BUCKET: nov-dag-mwaa-test
TIMEOUT_MINUTES: 10 (positive) / 5 (negative)
```

### Local Testing

You can trigger DAGs locally using:

```bash
# Test successful DAG
make trigger-dag DAG_ID=my_dag_name

# Test failing DAG
make trigger-dag DAG_ID=failing_dag

# Custom parameters
make trigger-dag DAG_ID=my_dag_with_git_hash TIMEOUT_MINUTES=15
```

### Features

All workflows include:
- 👤 User attribution (shows who triggered the run)
- 🔗 Direct Airflow UI links
- 📄 Inline CloudWatch logs (no need to click links!)
- 🔴 Error highlighting for failures
- ✅ Complete traceability
