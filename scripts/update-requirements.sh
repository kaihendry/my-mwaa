#!/bin/bash
# Force MWAA to reinstall requirements.txt
# This triggers MWAA to re-read and install packages from requirements.txt in S3

set -e

AWS_REGION="${AWS_REGION:-eu-west-2}"
MWAA_ENV_NAME="${MWAA_ENVIRONMENT_NAME:-MyAirflowEnvironment}"
S3_BUCKET="${S3_BUCKET:-nov-dag-mwaa-test}"

echo "============================================================"
echo "Force MWAA Requirements Update"
echo "============================================================"
echo ""
echo "Environment:      $MWAA_ENV_NAME"
echo "Region:           $AWS_REGION"
echo "S3 Bucket:        $S3_BUCKET"
echo "Requirements:     s3://$S3_BUCKET/requirements.txt"
echo ""

# Check when requirements.txt was last modified in S3
echo "Checking requirements.txt in S3..."
LAST_MODIFIED=$(aws s3api head-object \
    --bucket "$S3_BUCKET" \
    --key requirements.txt \
    --query 'LastModified' \
    --output text \
    --profile "${AWS_PROFILE:-default}" 2>/dev/null || echo "unknown")

echo "  Last Modified: $LAST_MODIFIED"
echo ""

# Show current MWAA status
echo "Current MWAA environment status..."
CURRENT_INFO=$(aws mwaa get-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --query 'Environment.{Status:Status,LastUpdate:LastUpdate.CreatedAt,RequirementsPath:RequirementsS3Path}' \
    --output json)

echo "$CURRENT_INFO" | jq .
echo ""

# Confirm
read -p "Trigger environment update to reinstall requirements? (20-30 min) (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Triggering environment update..."

# Force update by updating the environment with the same requirements path
# This causes MWAA to re-read and reinstall from requirements.txt
aws mwaa update-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --requirements-s3-path requirements.txt > /dev/null

if [ $? -eq 0 ]; then
    echo "✓ Environment update initiated"
else
    echo "✗ Failed to trigger update"
    exit 1
fi

echo ""
echo "============================================================"
echo "✓ Requirements Update Triggered!"
echo "============================================================"
echo ""
echo "What's happening:"
echo "  1. MWAA is updating the environment (status: UPDATING)"
echo "  2. Workers are being replaced with new packages"
echo "  3. This takes 20-30 minutes"
echo ""
echo "Monitor progress:"
echo "  make check-mwaa-status"
echo ""
echo "After completion, run the diagnostics DAG:"
echo "  make trigger-dag DAG_ID=check_packages"
echo ""
echo "This will show all installed packages including snowflake-connector-python"
echo "============================================================"
