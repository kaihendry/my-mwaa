#!/bin/bash
# Setup GitHub Actions secrets for MWAA deployment

set -e

echo "============================================================"
echo "GitHub Actions Secrets Setup for MWAA"
echo "============================================================"
echo ""

# Configuration
IAM_USER="github-actions-mwaa-deployer"
POLICY_FILE="scripts/iam-policy.json"

# Check if user already exists
echo "Step 1: Checking if IAM user exists..."
if aws iam get-user --user-name "$IAM_USER" 2>/dev/null; then
    echo "⚠️  IAM user '$IAM_USER' already exists"
    read -p "Do you want to use the existing user? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Please delete the existing user first or choose a different name."
        exit 1
    fi
    USER_EXISTS=true
else
    echo "✓ User does not exist, will create it"
    USER_EXISTS=false
fi

# Create IAM user if it doesn't exist
if [ "$USER_EXISTS" = false ]; then
    echo ""
    echo "Step 2: Creating IAM user..."
    aws iam create-user --user-name "$IAM_USER"
    echo "✓ IAM user created: $IAM_USER"
else
    echo ""
    echo "Step 2: Skipping user creation (already exists)"
fi

# Attach policy
echo ""
echo "Step 3: Attaching IAM policy..."
aws iam put-user-policy \
    --user-name "$IAM_USER" \
    --policy-name "MWAADagDeployment" \
    --policy-document "file://$POLICY_FILE"
echo "✓ Policy attached successfully"

# Check for existing access keys
echo ""
echo "Step 4: Checking for existing access keys..."
EXISTING_KEYS=$(aws iam list-access-keys --user-name "$IAM_USER" --query 'AccessKeyMetadata[*].AccessKeyId' --output text)

if [ -n "$EXISTING_KEYS" ]; then
    echo "⚠️  Found existing access keys:"
    echo "$EXISTING_KEYS"
    echo ""
    read -p "Do you want to create a NEW access key? (existing keys will remain) (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Please provide your existing credentials:"
        read -p "AWS_ACCESS_KEY_ID: " ACCESS_KEY_ID
        read -sp "AWS_SECRET_ACCESS_KEY: " SECRET_ACCESS_KEY
        echo ""
        CREATE_KEY=false
    else
        CREATE_KEY=true
    fi
else
    CREATE_KEY=true
fi

# Create new access key if needed
if [ "$CREATE_KEY" = true ]; then
    echo ""
    echo "Step 5: Creating access key..."
    KEY_OUTPUT=$(aws iam create-access-key --user-name "$IAM_USER")

    ACCESS_KEY_ID=$(echo "$KEY_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['AccessKey']['AccessKeyId'])")
    SECRET_ACCESS_KEY=$(echo "$KEY_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin)['AccessKey']['SecretAccessKey'])")

    echo "✓ Access key created successfully"
    echo ""
    echo "⚠️  IMPORTANT: Save these credentials securely!"
    echo "Access Key ID: $ACCESS_KEY_ID"
    echo "Secret Access Key: $SECRET_ACCESS_KEY"
    echo ""
    read -p "Press Enter once you've saved these credentials..."
else
    echo ""
    echo "Step 5: Using provided credentials"
fi

# Get current repository
echo ""
echo "Step 6: Detecting GitHub repository..."
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
echo "✓ Repository: $REPO"

# Add secrets to GitHub
echo ""
echo "Step 7: Adding secrets to GitHub repository..."
echo ""

# Add AWS_ACCESS_KEY_ID
echo "Adding AWS_ACCESS_KEY_ID..."
echo "$ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID
echo "✓ AWS_ACCESS_KEY_ID added"

# Add AWS_SECRET_ACCESS_KEY
echo "Adding AWS_SECRET_ACCESS_KEY..."
echo "$SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY
echo "✓ AWS_SECRET_ACCESS_KEY added"

# Verify secrets were added
echo ""
echo "Step 8: Verifying secrets..."
gh secret list

echo ""
echo "============================================================"
echo "✓ Setup Complete!"
echo "============================================================"
echo ""
echo "GitHub Actions secrets have been configured:"
echo "  ✓ AWS_ACCESS_KEY_ID"
echo "  ✓ AWS_SECRET_ACCESS_KEY"
echo ""
echo "IAM User: $IAM_USER"
echo "Permissions:"
echo "  ✓ S3 bucket access (nov-dag-mwaa-test)"
echo "  ✓ MWAA CLI token creation"
echo "  ✓ CloudWatch Logs access"
echo ""
echo "You can now push to main branch to trigger the workflows!"
echo "============================================================"
