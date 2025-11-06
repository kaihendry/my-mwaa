#!/bin/bash
# Add AWS credentials to GitHub Secrets
# Supports both permanent IAM user credentials and temporary SSO credentials

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

# Check if AWS_PROFILE is set
if [ -n "$AWS_PROFILE" ]; then
    echo "Detected AWS_PROFILE: $AWS_PROFILE"
    echo "Attempting to extract temporary credentials from profile..."
    echo ""

    # Export credentials from the current profile
    CREDS=$(aws configure export-credentials --profile "$AWS_PROFILE" --format env 2>/dev/null || echo "")

    if [ -n "$CREDS" ]; then
        # Extract credentials from export output
        ACCESS_KEY_ID=$(echo "$CREDS" | grep AWS_ACCESS_KEY_ID | cut -d= -f2)
        SECRET_ACCESS_KEY=$(echo "$CREDS" | grep AWS_SECRET_ACCESS_KEY | cut -d= -f2)
        SESSION_TOKEN=$(echo "$CREDS" | grep AWS_SESSION_TOKEN | cut -d= -f2)
        EXPIRATION=$(echo "$CREDS" | grep AWS_CREDENTIAL_EXPIRATION | cut -d= -f2)

        if [ -n "$ACCESS_KEY_ID" ] && [ -n "$SECRET_ACCESS_KEY" ]; then
            echo "✓ Successfully extracted credentials from profile"
            if [ -n "$SESSION_TOKEN" ]; then
                echo "✓ Temporary credentials detected (includes session token)"
                if [ -n "$EXPIRATION" ]; then
                    echo "⏰ Credentials expire at: $EXPIRATION"
                fi
            fi
            echo ""
        else
            echo "⚠ Failed to extract credentials from profile"
            CREDS=""
        fi
    else
        echo "⚠ Could not export credentials from profile"
    fi
fi

# If we couldn't get credentials from profile, prompt for manual entry
if [ -z "$CREDS" ]; then
    echo "Please enter your AWS credentials:"
    echo "(These will be stored as GitHub secrets)"
    echo ""

    read -p "AWS_ACCESS_KEY_ID: " ACCESS_KEY_ID
    read -sp "AWS_SECRET_ACCESS_KEY: " SECRET_ACCESS_KEY
    echo ""
    read -sp "AWS_SESSION_TOKEN (optional, for temporary credentials): " SESSION_TOKEN
    echo ""
    echo ""
fi

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

# Add AWS_SESSION_TOKEN if present
if [ -n "$SESSION_TOKEN" ]; then
    echo "Adding AWS_SESSION_TOKEN..."
    echo "$SESSION_TOKEN" | gh secret set AWS_SESSION_TOKEN
    echo "✓ AWS_SESSION_TOKEN added"
fi

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
if [ -n "$SESSION_TOKEN" ]; then
    echo "  ✓ AWS_SESSION_TOKEN"
    if [ -n "$EXPIRATION" ]; then
        echo ""
        echo "⚠ WARNING: These are temporary credentials!"
        echo "   They will expire at: $EXPIRATION"
        echo "   You'll need to refresh them before they expire."
    fi
fi
echo ""
echo "You can now push to trigger the GitHub Actions workflows!"
echo "============================================================"
