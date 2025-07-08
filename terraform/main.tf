terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}

provider "aws" {
  region = "eu-west-2"
}

resource "random_string" "bucket_suffix" {
  length  = 8
  special = false
  upper   = false
}

resource "aws_s3tables_table_bucket" "iceberg_table_bucket" {
  name = "iceberg-table-${random_string.bucket_suffix.result}"
}

resource "aws_s3tables_namespace" "example" {
  namespace        = "example_namespace"
  table_bucket_arn = aws_s3tables_table_bucket.iceberg_table_bucket.arn
}

resource "aws_s3tables_table" "customer_table" {
  name             = "customer_table"
  namespace        = aws_s3tables_namespace.example.namespace
  table_bucket_arn = aws_s3tables_namespace.example.table_bucket_arn
  format           = "ICEBERG"
}

resource "aws_iam_role" "mwaa_iceberg_role" {
  name = "mwaa-iceberg-role-${random_string.bucket_suffix.result}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "airflow.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "mwaa_iceberg_policy" {
  name        = "mwaa-iceberg-policy-${random_string.bucket_suffix.result}"
  description = "Policy for MWAA to access S3 Tables"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3tables:GetTable",
          "s3tables:PutTableData",
          "s3tables:GetTableData",
          "s3tables:DeleteTableData",
          "s3tables:ListTables"
        ]
        Resource = [
          aws_s3tables_table_bucket.iceberg_table_bucket.arn,
          "${aws_s3tables_table_bucket.iceberg_table_bucket.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "mwaa_iceberg_policy_attachment" {
  role       = aws_iam_role.mwaa_iceberg_role.name
  policy_arn = aws_iam_policy.mwaa_iceberg_policy.arn
}

output "table_bucket_name" {
  description = "Name of the S3 Tables bucket for Iceberg table storage"
  value       = aws_s3tables_table_bucket.iceberg_table_bucket.name
}

output "table_bucket_arn" {
  description = "ARN of the S3 Tables bucket for Iceberg table storage"
  value       = aws_s3tables_table_bucket.iceberg_table_bucket.arn
}

output "customer_table_name" {
  description = "Name of the customer Iceberg table"
  value       = aws_s3tables_table.customer_table.name
}

output "customer_table_arn" {
  description = "ARN of the customer Iceberg table"
  value       = aws_s3tables_table.customer_table.arn
}

output "iam_role_arn" {
  description = "ARN of the IAM role for MWAA to access S3 Tables"
  value       = aws_iam_role.mwaa_iceberg_role.arn
}
