#!/bin/bash
# Add AWS credentials to GitHub Secrets
# Use this after your admin creates the IAM user

set -e

echo "============================================================"
echo "Add AWS Credentials to GitHub Secrets"
echo "============================================================"
echo ""

# Get current repository
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "unknown")
if [ "$REPO" = "unknown" ]; then
    echo "Error: Not in a git repository or gh CLI not authenticated"
    exit 1
fi

echo "Repository: $REPO"
echo ""

# Prompt for credentials
echo "Please enter your AWS credentials:"
echo "(These will be stored as GitHub secrets)"
echo ""

read -p "AWS_ACCESS_KEY_ID: " ACCESS_KEY_ID
read -sp "AWS_SECRET_ACCESS_KEY: " SECRET_ACCESS_KEY
echo ""
echo ""

# Validate inputs
if [ -z "$ACCESS_KEY_ID" ] || [ -z "$SECRET_ACCESS_KEY" ]; then
    echo "Error: Both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are required"
    exit 1
fi

# Add secrets to GitHub
echo "Adding secrets to GitHub repository..."
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
echo "Verifying secrets..."
gh secret list

echo ""
echo "============================================================"
echo "✓ Secrets Added Successfully!"
echo "============================================================"
echo ""
echo "GitHub repository: $REPO"
echo "Secrets configured:"
echo "  ✓ AWS_ACCESS_KEY_ID"
echo "  ✓ AWS_SECRET_ACCESS_KEY"
echo ""
echo "You can now push to trigger the GitHub Actions workflows!"
echo "============================================================"
