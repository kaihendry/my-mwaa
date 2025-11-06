# AWS Secrets Manager Test DAG

This DAG tests reading secrets from AWS Secrets Manager in the MWAA runtime environment.

## Overview

The `secrets_test` DAG demonstrates:
- Reading secrets from AWS Secrets Manager
- Displaying trigger information (who triggered it and how)
- Proper IAM permission configuration for MWAA

## Setup

### 1. Create the Secret and Configure Permissions

Run the setup script to:
- Create a test secret: `mwaa/test-secret`
- Add IAM policy to MWAA execution role
- Verify permissions

```bash
make setup-secrets
# or
bash scripts/setup-secret.sh
```

This script:
1. Gets the MWAA execution role ARN
2. Creates/updates the secret with test data:
   - `database_password`: Demo database password
   - `api_key`: Demo API key
   - `environment`: Environment name
3. Adds inline IAM policy `MWAASecretsManagerAccess` to the MWAA role

### 2. Deploy the DAG

```bash
aws s3 cp dags/secrets_test/secrets_test.py s3://nov-dag-mwaa-test/dags/secrets_test/secrets_test.py
```

Wait 30 seconds for MWAA to detect the new DAG.

### 3. Enable the DAG

In the Airflow UI, toggle the `secrets_test` DAG to enabled.

### 4. Run the DAG

**Via Makefile:**
```bash
make test-secrets
```

**Via trigger script:**
```bash
make trigger-dag DAG_ID=secrets_test
```

**Via Airflow UI:**
Click the play button next to `secrets_test`

## IAM Permissions

The MWAA execution role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:eu-west-2:160071257600:secret:mwaa/test-secret-*",
        "arn:aws:secretsmanager:eu-west-2:160071257600:secret:mwaa/*"
      ]
    }
  ]
}
```

This is automatically added by `scripts/setup-secret.sh` as an inline policy named `MWAASecretsManagerAccess`.

## What the DAG Does

1. Shows trigger information:
   - Run ID, run type, logical date
   - Who triggered it (username from $USER or "Manual trigger from Airflow UI")
   - Trigger source (github-actions-script or UI)

2. Displays current AWS identity (MWAA execution role)

3. Reads the secret `mwaa/test-secret` from AWS Secrets Manager

4. Shows secret metadata and contents (with sensitive values partially masked)

5. Provides troubleshooting hints if access fails

## Expected Output

```
================================================================================
AWS Secrets Manager Test
================================================================================

DAG Run Trigger Information:
  Run ID:       manual__2025-11-06T16:30:00+00:00
  Run Type:     manual
  Triggered By: your-username
  Trigger Source: github-actions-script

Current AWS Identity:
  ARN: arn:aws:sts::160071257600:assumed-role/AmazonMWAA-MyAirflowEnvironment-iCDDun/AmazonMWAA-airflow

Reading secret: mwaa/test-secret
────────────────────────────────────────────────────────────────────────────────
✓ Secret retrieved successfully!

Secret Metadata:
  Name:          mwaa/test-secret
  ARN:           arn:aws:secretsmanager:eu-west-2:160071257600:secret:mwaa/test-secret-o4zVlU
  Created:       2025-11-06 16:15:00
  Version:       abc123...

Secret Contents:
  database_password: MySe...d123
  api_key: sk-t...cdef
  environment: production

✓ Secret access test PASSED!
================================================================================
```

## Cleanup

To remove the secret and IAM permissions:

```bash
make cleanup-secrets
# or
bash scripts/cleanup-secret.sh
```

This will:
- Delete the IAM inline policy from MWAA role
- Schedule the secret for deletion (7-day recovery window)

## Troubleshooting

### AccessDeniedException

If you see `AccessDeniedException`:
1. Verify the IAM policy is attached:
   ```bash
   aws iam get-role-policy \
     --role-name AmazonMWAA-MyAirflowEnvironment-iCDDun \
     --policy-name MWAASecretsManagerAccess
   ```
2. Re-run the setup script: `make setup-secrets`

### ResourceNotFoundException

If you see `ResourceNotFoundException`:
1. The secret doesn't exist
2. Run: `make setup-secrets`

### Secret Not Visible

If the DAG doesn't see the secret:
1. Check the region is correct (eu-west-2)
2. Verify the secret name: `mwaa/test-secret`
3. Check AWS credentials in the MWAA runtime

## Files

- `secrets_test.py` - The DAG definition
- `../../scripts/setup-secret.sh` - Setup script for secret and permissions
- `../../scripts/cleanup-secret.sh` - Cleanup script
- `README.md` - This file

## References

- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [MWAA IAM Roles](https://docs.aws.amazon.com/mwaa/latest/userguide/mwaa-create-role.html)
- [Apache Airflow Secrets Backend](https://airflow.apache.org/docs/apache-airflow/stable/security/secrets/secrets-backend/index.html)
