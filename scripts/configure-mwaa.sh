#!/bin/bash
# Unified MWAA Configuration Script
# Configures all recommended settings for the MWAA environment

set -e

# Configuration
AWS_REGION="${AWS_REGION:-eu-west-2}"
MWAA_ENV_NAME="${MWAA_ENVIRONMENT_NAME:-MyAirflowEnvironment}"
S3_BUCKET="${S3_BUCKET:-nov-dag-mwaa-test}"
REQUIREMENTS_PATH="${REQUIREMENTS_PATH:-requirements.txt}"

# Airflow configuration options
# Use environment variables or defaults
DAG_DIR_LIST_INTERVAL="${DAG_DIR_LIST_INTERVAL:-30}"  # Default 300s, set to 30s for faster detection
MIN_FILE_PROCESS_INTERVAL="${MIN_FILE_PROCESS_INTERVAL:-30}"  # Default 30s
DAGS_PAUSED_AT_CREATION="${DAGS_PAUSED_AT_CREATION:-False}"  # Auto-enable new DAGs

echo "============================================================"
echo "MWAA Environment Configuration"
echo "============================================================"
echo ""
echo "Environment:"
echo "  Name:          $MWAA_ENV_NAME"
echo "  Region:        $AWS_REGION"
echo "  S3 Bucket:     $S3_BUCKET"
echo ""
echo "Requirements:"
echo "  Path:          $REQUIREMENTS_PATH"
echo ""
echo "Airflow Configuration Options:"
echo "  core.dags_are_paused_at_creation:      $DAGS_PAUSED_AT_CREATION"
echo "    → New DAGs will be automatically enabled"
echo ""
echo "  scheduler.dag_dir_list_interval:       $DAG_DIR_LIST_INTERVAL seconds"
echo "    → New DAGs will appear in ~$DAG_DIR_LIST_INTERVAL seconds (default: 300s)"
echo ""
echo "  scheduler.min_file_process_interval:   $MIN_FILE_PROCESS_INTERVAL seconds"
echo "    → DAG changes will be detected within $MIN_FILE_PROCESS_INTERVAL seconds (default: 30s)"
echo ""

# Get current configuration
echo "Checking current environment configuration..."
CURRENT_STATUS=$(aws mwaa get-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --query 'Environment.{Status:Status,RequirementsS3Path:RequirementsS3Path,AirflowConfigurationOptions:AirflowConfigurationOptions}' \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo "Error: Could not get environment information"
    echo "$CURRENT_STATUS"
    exit 1
fi

echo ""
echo "Current Configuration:"
echo "$CURRENT_STATUS" | jq .
echo ""

# Confirm with user
read -p "Apply this configuration to $MWAA_ENV_NAME? This will take 20-30 minutes. (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Applying configuration..."
echo ""

# Build the AWS CLI command
CMD="aws mwaa update-environment \
    --name $MWAA_ENV_NAME \
    --region $AWS_REGION \
    --requirements-s3-path $REQUIREMENTS_PATH \
    --airflow-configuration-options \
        core.dags_are_paused_at_creation=$DAGS_PAUSED_AT_CREATION \
        scheduler.dag_dir_list_interval=$DAG_DIR_LIST_INTERVAL \
        scheduler.min_file_process_interval=$MIN_FILE_PROCESS_INTERVAL"

# Execute the command
eval "$CMD" > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "✓ Configuration update initiated successfully"
else
    echo "✗ Configuration update failed"
    exit 1
fi

echo ""
echo "============================================================"
echo "✓ Configuration Update Initiated!"
echo "============================================================"
echo ""
echo "Timeline:"
echo "  1. Environment status changes to 'UPDATING' (immediately)"
echo "  2. MWAA applies the configuration changes (20-30 minutes)"
echo "  3. Environment status returns to 'AVAILABLE' (when complete)"
echo ""
echo "Monitor progress:"
echo "  make check-mwaa-status"
echo ""
echo "Or use AWS CLI:"
echo "  aws mwaa get-environment --name $MWAA_ENV_NAME --region $AWS_REGION --query 'Environment.Status'"
echo ""
echo "After the update completes:"
echo "  ✓ New DAGs will automatically be enabled (no manual toggle needed)"
echo "  ✓ New DAGs will appear in ~$DAG_DIR_LIST_INTERVAL seconds"
echo "  ✓ DAG changes will be detected within $MIN_FILE_PROCESS_INTERVAL seconds"
echo ""
echo "⚠ Performance Note:"
echo "  Lower scheduler intervals increase CPU usage but provide faster feedback."
echo "  Recommended for:"
echo "    - Development: 30-60 seconds (faster iteration)"
echo "    - Production:  300 seconds (default, lower CPU usage)"
echo ""
echo "To adjust these values, set environment variables before running:"
echo "  DAG_DIR_LIST_INTERVAL=60 bash scripts/configure-mwaa.sh"
echo "============================================================"
