#!/bin/bash
# Configure MWAA for faster DAG detection
# Reduces the time it takes for new DAGs to appear in the Airflow UI

set -e

# Configuration
AWS_REGION="${AWS_REGION:-eu-west-2}"
MWAA_ENV_NAME="${MWAA_ENVIRONMENT_NAME:-MyAirflowEnvironment}"

# New DAG detection interval (in seconds)
# Default is 300 seconds (5 minutes) - we'll set it to 30 seconds
DAG_DIR_LIST_INTERVAL="${DAG_DIR_LIST_INTERVAL:-30}"

# Individual DAG file re-parse interval (in seconds)
# Default is 30 seconds - keep as is
MIN_FILE_PROCESS_INTERVAL="${MIN_FILE_PROCESS_INTERVAL:-30}"

echo "============================================================"
echo "Configure MWAA for Faster DAG Detection"
echo "============================================================"
echo ""
echo "Current Configuration:"
echo "  AWS Region:        $AWS_REGION"
echo "  MWAA Environment:  $MWAA_ENV_NAME"
echo ""
echo "New Settings:"
echo "  scheduler.dag_dir_list_interval:      $DAG_DIR_LIST_INTERVAL seconds (was 300 seconds / 5 minutes)"
echo "  scheduler.min_file_process_interval:  $MIN_FILE_PROCESS_INTERVAL seconds (default)"
echo ""
echo "This means:"
echo "  - New DAGs will appear within ~$DAG_DIR_LIST_INTERVAL seconds (instead of 5 minutes)"
echo "  - DAG changes will be detected within $MIN_FILE_PROCESS_INTERVAL seconds"
echo ""

# Get current configuration
echo "Step 1: Getting current MWAA configuration..."
CURRENT_CONFIG=$(aws mwaa get-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --query 'Environment.AirflowConfigurationOptions' \
    --output json)

echo "  Current Airflow configuration options:"
echo "$CURRENT_CONFIG" | jq .
echo ""

# Build the new configuration
echo "Step 2: Building new configuration..."

# Start with existing config or empty object
if [ "$CURRENT_CONFIG" = "null" ] || [ "$CURRENT_CONFIG" = "{}" ]; then
    NEW_CONFIG="{}"
else
    NEW_CONFIG="$CURRENT_CONFIG"
fi

# Add/update the scheduler settings
NEW_CONFIG=$(echo "$NEW_CONFIG" | jq \
    --arg dag_dir "$DAG_DIR_LIST_INTERVAL" \
    --arg min_file "$MIN_FILE_PROCESS_INTERVAL" \
    '. + {"scheduler.dag_dir_list_interval": $dag_dir, "scheduler.min_file_process_interval": $min_file}')

echo "  New configuration:"
echo "$NEW_CONFIG" | jq .
echo ""

# Confirm with user
read -p "Apply this configuration to $MWAA_ENV_NAME? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Apply the configuration
echo ""
echo "Step 3: Applying configuration to MWAA environment..."
echo "  This will take 20-30 minutes to complete."
echo ""

# Convert JSON to CLI format (key=value pairs)
CONFIG_ARGS=$(echo "$NEW_CONFIG" | jq -r 'to_entries | map("--airflow-configuration-options " + .key + "=" + .value) | join(" ")')

# Update the environment
aws mwaa update-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    $(echo "$CONFIG_ARGS") > /dev/null

echo "✓ Configuration update initiated"
echo ""

# Show status
echo "Step 4: Checking environment status..."
STATUS=$(aws mwaa get-environment \
    --name "$MWAA_ENV_NAME" \
    --region "$AWS_REGION" \
    --query 'Environment.Status' \
    --output text)

echo "  Current status: $STATUS"
echo ""

echo "============================================================"
echo "✓ Configuration Update Initiated!"
echo "============================================================"
echo ""
echo "What happens next:"
echo "  1. MWAA will update the environment (20-30 minutes)"
echo "  2. Status will change from 'AVAILABLE' → 'UPDATING' → 'AVAILABLE'"
echo "  3. Once complete, new DAGs will appear in ~$DAG_DIR_LIST_INTERVAL seconds"
echo ""
echo "Monitor progress:"
echo "  make check-mwaa-status"
echo ""
echo "Or use AWS CLI:"
echo "  aws mwaa get-environment --name $MWAA_ENV_NAME --region $AWS_REGION --query 'Environment.Status'"
echo ""
echo "⚠ WARNING: Lower values increase CPU usage on the scheduler."
echo "   Recommended values:"
echo "   - Development: 30-60 seconds (faster iteration)"
echo "   - Production:  300 seconds (default, lower CPU usage)"
echo "============================================================"
