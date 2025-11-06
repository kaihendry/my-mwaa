#!/bin/bash
# Quick script to unpause a DAG

DAG_ID=${1:-failing_dag}
REGION=${AWS_REGION:-eu-west-2}
ENV_NAME=${MWAA_ENVIRONMENT_NAME:-MyAirflowEnvironment}

echo "Unpausing DAG: $DAG_ID"

# Get CLI token
TOKEN_DATA=$(aws mwaa create-cli-token --name "$ENV_NAME" --region "$REGION")
TOKEN=$(echo "$TOKEN_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin)['CliToken'])")
HOSTNAME=$(echo "$TOKEN_DATA" | python3 -c "import sys, json; print(json.load(sys.stdin)['WebServerHostname'])")

# Unpause the DAG
RESPONSE=$(curl -s -X POST "https://$HOSTNAME/aws_mwaa/cli" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/plain" \
  -d "dags unpause $DAG_ID")

# Decode base64 response
echo "$RESPONSE" | python3 -c "
import sys, json, base64
data = json.load(sys.stdin)
stdout = base64.b64decode(data.get('stdout', '')).decode('utf-8')
print(stdout)
"

echo "✓ DAG unpaused successfully"
