# CLAUDE.md

## Project Overview

This is a playground to better understand AWS MWAA (Managed Airflow) and associated DAG Operators.

We manually provision in the AWS console the [latest version 2.10.3 with Python
3.11](https://docs.aws.amazon.com/mwaa/latest/userguide/airflow-versions.html).
We use the Wizard to create the VPC and all logging is enabled to debug
requirements.txt issue with our test bucket: s3://march-dag-mwaa-test

https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/operators/sqs.html

