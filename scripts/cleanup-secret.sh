#!/bin/bash
# Cleanup AWS Secrets Manager secret and IAM policies
# This script removes the test secret and associated permissions

set -e

# Configuration
SECRET_NAME="mwaa/test-secret"
AWS_REGION="${AWS_REGION:-eu-west-2}"
MWAA_ENV_NAME="${MWAA_ENVIRONMENT_NAME:-MyAirflowEnvironment}"

echo "============================================================"
echo "AWS Secrets Manager Cleanup for MWAA"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Secret Name:       $SECRET_NAME"
echo "  AWS Region:        $AWS_REGION"
echo "  MWAA Environment:  $MWAA_ENV_NAME"
echo ""

# Get MWAA execution role name
echo "Step 1: Getting MWAA execution role..."
MWAA_ROLE_ARN=$(aws mwaa get-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --query 'Environment.ExecutionRoleArn' \
    --output text)

MWAA_ROLE_NAME=$(echo "$MWAA_ROLE_ARN" | awk -F'/' '{print $NF}')
echo "  MWAA Role Name: $MWAA_ROLE_NAME"
echo ""

# Remove IAM inline policy
echo "Step 2: Removing IAM policy from MWAA role..."
POLICY_NAME="MWAASecretsManagerAccess"

POLICY_EXISTS=$(aws iam get-role-policy \
    --role-name "$MWAA_ROLE_NAME" \
    --policy-name "$POLICY_NAME" 2>/dev/null || echo "")

if [ -n "$POLICY_EXISTS" ]; then
    aws iam delete-role-policy \
        --role-name "$MWAA_ROLE_NAME" \
        --policy-name "$POLICY_NAME"
    echo "  ✓ IAM policy removed"
else
    echo "  ⚠ IAM policy does not exist (already removed)"
fi
echo ""

# Delete the secret
echo "Step 3: Deleting secret..."

SECRET_EXISTS=$(aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" \
    --region "$AWS_REGION" 2>/dev/null || echo "")

if [ -n "$SECRET_EXISTS" ]; then
    # Schedule deletion (cannot be immediate)
    aws secretsmanager delete-secret \
        --secret-id "$SECRET_NAME" \
        --recovery-window-in-days 7 \
        --region "$AWS_REGION" > /dev/null
    echo "  ✓ Secret scheduled for deletion (7-day recovery window)"
    echo "  ℹ To delete immediately (no recovery):"
    echo "    aws secretsmanager delete-secret --secret-id $SECRET_NAME --force-delete-without-recovery --region $AWS_REGION"
else
    echo "  ⚠ Secret does not exist (already deleted)"
fi
echo ""

echo "============================================================"
echo "✓ Cleanup Complete!"
echo "============================================================"
echo ""
echo "What was removed:"
echo "  - IAM policy: $POLICY_NAME"
echo "  - Secret: $SECRET_NAME (scheduled for deletion)"
echo ""
echo "The secret will be permanently deleted after 7 days."
echo "============================================================"
