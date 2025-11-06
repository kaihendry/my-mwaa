#!/bin/bash
# Add current temporary AWS credentials to GitHub Secrets
# WARNING: These expire in ~1 hour and need to be refreshed

set -e

echo "============================================================"
echo "Add Temporary AWS Credentials to GitHub Secrets"
echo "============================================================"
echo ""

# Check for required environment variables
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_SESSION_TOKEN" ]; then
    echo "Error: AWS credentials not found in environment"
    echo "Make sure you're authenticated with AWS SSO"
    exit 1
fi

# Get current repository
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "unknown")
if [ "$REPO" = "unknown" ]; then
    echo "Error: Not in a git repository or gh CLI not authenticated"
    exit 1
fi

echo "Repository: $REPO"
echo ""

# Show expiration warning
if [ -n "$AWS_CREDENTIAL_EXPIRATION" ]; then
    echo "⚠️  WARNING: These are TEMPORARY credentials!"
    echo "   Expiration: $AWS_CREDENTIAL_EXPIRATION"
    echo "   You will need to refresh these credentials before they expire"
    echo ""
fi

echo "Current credentials:"
echo "  Access Key: ${AWS_ACCESS_KEY_ID:0:8}..."
echo "  Session Token: ${AWS_SESSION_TOKEN:0:20}..."
echo ""

read -p "Continue adding temporary credentials to GitHub? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled"
    exit 1
fi

# Add secrets to GitHub
echo ""
echo "Adding secrets to GitHub repository..."
echo ""

# Add AWS_ACCESS_KEY_ID
echo "Adding AWS_ACCESS_KEY_ID..."
echo "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID
echo "✓ AWS_ACCESS_KEY_ID added"

# Add AWS_SECRET_ACCESS_KEY
echo "Adding AWS_SECRET_ACCESS_KEY..."
echo "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY
echo "✓ AWS_SECRET_ACCESS_KEY added"

# Add AWS_SESSION_TOKEN
echo "Adding AWS_SESSION_TOKEN..."
echo "$AWS_SESSION_TOKEN" | gh secret set AWS_SESSION_TOKEN
echo "✓ AWS_SESSION_TOKEN added"

# Verify secrets were added
echo ""
echo "Verifying secrets..."
gh secret list

echo ""
echo "============================================================"
echo "✓ Temporary Credentials Added!"
echo "============================================================"
echo ""
echo "⚠️  IMPORTANT:"
echo "   These credentials expire at: $AWS_CREDENTIAL_EXPIRATION"
echo "   After expiration, you'll need to run this script again"
echo ""
echo "GitHub repository: $REPO"
echo "Secrets configured:"
echo "  ✓ AWS_ACCESS_KEY_ID"
echo "  ✓ AWS_SECRET_ACCESS_KEY"
echo "  ✓ AWS_SESSION_TOKEN"
echo ""
echo "The workflows have been updated to use the session token."
echo "You can now trigger workflows manually or push to test!"
echo "============================================================"
