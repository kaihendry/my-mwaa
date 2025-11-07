# Snowflake Connection Test DAG

This DAG tests connecting to Snowflake from MWAA using key-pair authentication with credentials stored in AWS Secrets Manager.

## Overview

The `snowflake_test` DAG demonstrates:
- Reading Snowflake credentials from AWS Secrets Manager
- Processing RSA private key for key-pair authentication
- Connecting to Snowflake using the `snowflake-connector-python` library
- Running test queries to verify connectivity and permissions

## Prerequisites

### 1. Snowflake Setup

You need to register the public key with your Snowflake user account:

```sql
-- Connect to Snowflake as an admin
USE ROLE ACCOUNTADMIN;

-- Set the RSA public key for the user
ALTER USER TERRAFORM_SVC SET RSA_PUBLIC_KEY='MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArDUKC28SXrViZSVohlb5
3rawygQXPlXVKBNOUxOktnPOGRR/7h8vYB5QRQ/cesbsLs88Ja47GaceNlm36Taa
+iDjM0CaeUNcwfeQncyDE4WuLQxV07NIbYahadR9v0pM8/NUWFgYyM/9vRU6Prke
/m7b+YDyKv8PT6bYskocq4GYn2yDDAyL5Y20P5JTaB/p6lqM/MCzWKBhA05tWEWk
D50/QW8cW3JCXIDeMEqZw7vH+Fy+n2bWP0y+CqWSHSblNbNDnw5fsB6mIzi2zH+w
QeX5uOKVWBnIWV+2O6LMJleO1wSkb0FU2xD/34V7Np8i0RN5Oog++rpgIWmJX+0Z
AQIDAQAB';

-- Verify the key was set
DESC USER TERRAFORM_SVC;
```

**Important**: The public key should be in a single line without the `-----BEGIN PUBLIC KEY-----` and `-----END PUBLIC KEY-----` headers.

### 2. AWS Setup

Run the setup script to create the secret and configure permissions:

```bash
make setup-secrets
# or
bash scripts/setup-secret.sh
```

This will:
- Create/update secret `mwaa/test-secret` with:
  - `snowflake_account`: xbjfxng-qm18685
  - `snowflake_user`: TERRAFORM_SVC
  - `snowflake_role`: ACCOUNTADMIN
  - `snowflake_private_key`: RSA private key (PEM format)
  - `snowflake_public_key`: RSA public key (PEM format)
- Add IAM policy to MWAA execution role for Secrets Manager access

### 3. MWAA Setup

The `requirements.txt` now includes `snowflake-connector-python==3.12.3` (compatible with Airflow 2.10.3).

**Note**: MWAA will need to update its Python environment when you upload the new `requirements.txt`. This can take **20-30 minutes**.

To upload the new requirements:

```bash
aws s3 cp requirements.txt s3://nov-dag-mwaa-test/requirements.txt
```

Then check status:

```bash
make check-mwaa-status
```

Wait until the status shows `AVAILABLE` before testing.

## Deployment

### 1. Deploy the DAG

```bash
aws s3 cp dags/secrets_test/snowflake_test.py s3://nov-dag-mwaa-test/dags/secrets_test/snowflake_test.py
```

### 2. Wait for MWAA to pick up the DAG

Wait 30 seconds for MWAA to detect the new DAG.

### 3. Enable the DAG

In the Airflow UI, enable the `snowflake_test` DAG.

## Running the Test

### Via Makefile (Recommended)

```bash
make test-snowflake
```

### Via trigger script

```bash
make trigger-dag DAG_ID=snowflake_test TIMEOUT_MINUTES=10
```

### Via Airflow UI

Click the play button next to `snowflake_test` in the Airflow UI.

## What the DAG Does

### Step 1: Read Secret
- Connects to AWS Secrets Manager
- Retrieves the `mwaa/test-secret` secret
- Extracts Snowflake credentials

### Step 2: Process Private Key
- Loads the PEM-formatted private key
- Converts to DER format with PKCS8 encoding (required by Snowflake)
- Uses the `cryptography` library for key processing

### Step 3: Connect to Snowflake
- Establishes connection using key-pair authentication
- Parameters:
  - Account: xbjfxng-qm18685
  - User: TERRAFORM_SVC
  - Role: ACCOUNTADMIN
  - Private Key: (from secret)

### Step 4: Run Test Queries

1. **SELECT 1** - Basic connectivity test
2. **Current account info** - Verify account, user, and role
3. **Current version** - Show Snowflake version
4. **Show databases** - List available databases (if permissions allow)

## Expected Output

```
================================================================================
Snowflake Connection Test
================================================================================

DAG Run Trigger Information:
  Run ID:       manual__2025-11-06T17:00:00+00:00
  Run Type:     manual
  Triggered By: your-username
  Trigger Source: github-actions-script

Step 1: Reading secret: mwaa/test-secret
────────────────────────────────────────────────────────────────────────────────
✓ Secret retrieved successfully!
  Account: xbjfxng-qm18685
  User: TERRAFORM_SVC
  Role: ACCOUNTADMIN
  Private Key: Present

Step 2: Processing private key for Snowflake authentication
────────────────────────────────────────────────────────────────────────────────
✓ Private key processed successfully
  Key size: 1216 bytes

Step 3: Connecting to Snowflake
────────────────────────────────────────────────────────────────────────────────
✓ Connected to Snowflake successfully!

Step 4: Running test queries
────────────────────────────────────────────────────────────────────────────────
Query 1: SELECT 1
  Result: 1

Query 2: SHOW PARAMETERS LIKE 'ACCOUNT%'
  Account: XBJFXNG-QM18685
  User: TERRAFORM_SVC
  Role: ACCOUNTADMIN

Query 3: SELECT CURRENT_VERSION()
  Snowflake Version: 8.40.2

Query 4: SHOW DATABASES
  Found 5 database(s):
    - SNOWFLAKE
    - UTIL_DB
    - SNOWFLAKE_SAMPLE_DATA
    - TEST_DB
    - DEV_DB

✓ All queries executed successfully!

================================================================================
✓ SNOWFLAKE CONNECTION TEST PASSED!
================================================================================
```

## Troubleshooting

### Error: "JWT token is invalid"

This usually means the public key is not registered with Snowflake or doesn't match the private key.

**Solution**:
1. Verify the public key is registered: `DESC USER TERRAFORM_SVC;`
2. Ensure the public key matches the private key
3. Re-run the ALTER USER command with the correct public key

### Error: "250001: Could not connect to Snowflake backend"

Network connectivity issue between MWAA and Snowflake.

**Solution**:
1. Verify MWAA VPC has internet access (NAT Gateway or VPC endpoints)
2. Check security groups allow outbound HTTPS (port 443)
3. Verify Snowflake account identifier is correct: `xbjfxng-qm18685`

### Error: "Secret not found"

The secret doesn't exist or the name is wrong.

**Solution**:
```bash
make setup-secrets
```

### Error: "AccessDeniedException" when reading secret

MWAA execution role doesn't have Secrets Manager permissions.

**Solution**:
```bash
# Re-run setup script to fix permissions
make setup-secrets
```

### Error: "User does not exist" or "Authentication failed"

The Snowflake user doesn't exist or isn't configured correctly.

**Solution**:
1. Verify user exists: `SHOW USERS LIKE 'TERRAFORM_SVC';`
2. Verify RSA_PUBLIC_KEY is set: `DESC USER TERRAFORM_SVC;`
3. Ensure role is granted to user: `SHOW GRANTS TO USER TERRAFORM_SVC;`

## Files

- `snowflake_test.py` - The DAG definition
- `../../scripts/setup-secret.sh` - Setup script (includes Snowflake keys)
- `../../scripts/cleanup-secret.sh` - Cleanup script
- `../../keys/snowflake_tf_snow_key.p8` - Private key (PEM format)
- `../../keys/snowflake_tf_snow_key.pub` - Public key (PEM format)
- `SNOWFLAKE_README.md` - This file

## Security Notes

1. **Private Key Storage**: The private key is stored in AWS Secrets Manager with encryption at rest
2. **IAM Permissions**: MWAA role has least-privilege access to only the `mwaa/*` secrets
3. **No Password**: Key-pair authentication eliminates the need for password management
4. **Key Rotation**: To rotate keys:
   - Generate new key pair
   - Update secret in AWS Secrets Manager
   - Update public key in Snowflake
   - Test with this DAG

## References

- [Snowflake Key-Pair Authentication](https://docs.snowflake.com/en/user-guide/key-pair-auth)
- [Snowflake Connector for Python](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [MWAA IAM Roles](https://docs.aws.amazon.com/mwaa/latest/userguide/mwaa-create-role.html)
