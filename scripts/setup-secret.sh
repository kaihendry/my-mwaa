#!/bin/bash
# Setup AWS Secrets Manager secret for MWAA testing
# This script:
# 1. Creates a test secret in AWS Secrets Manager
# 2. Configures the secret's resource policy to allow MWAA access
# 3. Adds inline policy to MWAA execution role for Secrets Manager access

set -e

# Configuration
SECRET_NAME="mwaa/test-secret"
AWS_REGION="${AWS_REGION:-eu-west-2}"
MWAA_ENV_NAME="${MWAA_ENVIRONMENT_NAME:-MyAirflowEnvironment}"
AWS_ACCOUNT_ID="160071257600"

echo "============================================================"
echo "AWS Secrets Manager Setup for MWAA"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Secret Name:       $SECRET_NAME"
echo "  AWS Region:        $AWS_REGION"
echo "  MWAA Environment:  $MWAA_ENV_NAME"
echo "  AWS Account:       $AWS_ACCOUNT_ID"
echo ""

# Get MWAA execution role ARN
echo "Step 1: Getting MWAA execution role..."
MWAA_ROLE_ARN=$(aws mwaa get-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --query 'Environment.ExecutionRoleArn' \
    --output text)

if [ -z "$MWAA_ROLE_ARN" ]; then
    echo "Error: Could not get MWAA execution role ARN" >&2
    exit 1
fi

MWAA_ROLE_NAME=$(echo "$MWAA_ROLE_ARN" | awk -F'/' '{print $NF}')

echo "  MWAA Role ARN:  $MWAA_ROLE_ARN"
echo "  MWAA Role Name: $MWAA_ROLE_NAME"
echo ""

# Create or update the secret
echo "Step 2: Creating/updating secret in Secrets Manager..."

# Read Snowflake keys
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PRIVATE_KEY_FILE="$PROJECT_ROOT/keys/snowflake_tf_snow_key.p8"
PUBLIC_KEY_FILE="$PROJECT_ROOT/keys/snowflake_tf_snow_key.pub"

if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    echo "Error: Private key file not found: $PRIVATE_KEY_FILE" >&2
    exit 1
fi

if [ ! -f "$PUBLIC_KEY_FILE" ]; then
    echo "Error: Public key file not found: $PUBLIC_KEY_FILE" >&2
    exit 1
fi

echo "  Reading Snowflake keys..."
PRIVATE_KEY=$(cat "$PRIVATE_KEY_FILE")
PUBLIC_KEY=$(cat "$PUBLIC_KEY_FILE")

# Create JSON with escaped keys
SECRET_VALUE=$(jq -n \
  --arg db_pass "MySecretPassword123!" \
  --arg api_key "sk-test-1234567890abcdef" \
  --arg env "production" \
  --arg sf_account "xbjfxng-qm18685" \
  --arg sf_user "TERRAFORM_SVC" \
  --arg sf_role "ACCOUNTADMIN" \
  --arg private_key "$PRIVATE_KEY" \
  --arg public_key "$PUBLIC_KEY" \
  '{
    database_password: $db_pass,
    api_key: $api_key,
    environment: $env,
    snowflake_account: $sf_account,
    snowflake_user: $sf_user,
    snowflake_role: $sf_role,
    snowflake_private_key: $private_key,
    snowflake_public_key: $public_key
  }')

# Check if secret exists
SECRET_EXISTS=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" 2>/dev/null || echo "")

if [ -n "$SECRET_EXISTS" ]; then
    echo "  Secret already exists, updating value..."
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string "$SECRET_VALUE" \
        --region "$AWS_REGION" > /dev/null
    echo "  ✓ Secret updated"
else
    echo "  Creating new secret..."
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Test secret for MWAA DAG testing" \
        --secret-string "$SECRET_VALUE" \
        --region "$AWS_REGION" > /dev/null
    echo "  ✓ Secret created"
fi
echo ""

# Get the secret ARN
SECRET_ARN=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'ARN' \
    --output text)

echo "  Secret ARN: $SECRET_ARN"
echo ""

# Note: Skipping resource policy on the secret itself
# The IAM policy on the MWAA role is sufficient for access control
echo "Step 3: Skipping resource policy (IAM policy will be used instead)..."
echo "  ℹ IAM policy on the MWAA role will grant access"
echo ""

# Add inline policy to MWAA execution role
echo "Step 4: Adding Secrets Manager policy to MWAA role..."

POLICY_NAME="MWAASecretsManagerAccess"

IAM_POLICY=$(cat <<EOF
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
        "$SECRET_ARN",
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:mwaa/*"
      ]
    }
  ]
}
EOF
)

# Check if policy already exists
POLICY_EXISTS=$(aws iam get-role-policy \
    --role-name "$MWAA_ROLE_NAME" \
    --policy-name "$POLICY_NAME" 2>/dev/null || echo "")

if [ -n "$POLICY_EXISTS" ]; then
    echo "  Policy already exists, updating..."
else
    echo "  Creating new inline policy..."
fi

aws iam put-role-policy \
    --role-name "$MWAA_ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --policy-document "$IAM_POLICY"

echo "  ✓ IAM policy attached to role"
echo ""

# Verify setup
echo "Step 5: Verifying setup..."

# Check secret exists
SECRET_CHECK=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" \
    --query 'Name' \
    --output text)

if [ "$SECRET_CHECK" == "$SECRET_NAME" ]; then
    echo "  ✓ Secret exists and is accessible"
else
    echo "  ✗ Secret verification failed" >&2
fi

# Check IAM policy
POLICY_CHECK=$(aws iam get-role-policy \
    --role-name "$MWAA_ROLE_NAME" \
    --policy-name "$POLICY_NAME" \
    --query 'PolicyName' \
    --output text)

if [ "$POLICY_CHECK" == "$POLICY_NAME" ]; then
    echo "  ✓ IAM policy is attached"
else
    echo "  ✗ IAM policy verification failed" >&2
fi

echo ""
echo "============================================================"
echo "✓ Setup Complete!"
echo "============================================================"
echo ""
echo "Secret Information:"
echo "  Name: $SECRET_NAME"
echo "  ARN:  $SECRET_ARN"
echo ""
echo "Next Steps:"
echo "  1. Deploy the DAG:"
echo "     aws s3 cp dags/secrets_test/secrets_test.py s3://nov-dag-mwaa-test/dags/secrets_test/secrets_test.py"
echo ""
echo "  2. Wait 30 seconds for MWAA to pick up the DAG"
echo ""
echo "  3. Enable the 'secrets_test' DAG in Airflow UI"
echo ""
echo "  4. Trigger the DAG:"
echo "     make trigger-dag DAG_ID=secrets_test"
echo ""
echo "To clean up later, run:"
echo "  bash scripts/cleanup-secret.sh"
echo "============================================================"
