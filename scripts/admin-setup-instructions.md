# AWS Admin Setup Instructions

**For AWS Administrators:** Please execute these commands to set up GitHub Actions access for MWAA deployment.

## Prerequisites

- Admin access to AWS account 160071257600
- AWS CLI configured

## Step 1: Create IAM User

```bash
aws iam create-user --user-name github-actions-mwaa-deployer
```

## Step 2: Attach Policy

```bash
aws iam put-user-policy \
  --user-name github-actions-mwaa-deployer \
  --policy-name MWAADagDeployment \
  --policy-document file://scripts/iam-policy.json
```

Policy contents (`scripts/iam-policy.json`):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DagDeployment",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::nov-dag-mwaa-test",
        "arn:aws:s3:::nov-dag-mwaa-test/*"
      ]
    },
    {
      "Sid": "MWAACLIToken",
      "Effect": "Allow",
      "Action": [
        "airflow:CreateCliToken"
      ],
      "Resource": [
        "arn:aws:airflow:eu-west-2:160071257600:environment/MyAirflowEnvironment"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:eu-west-2:160071257600:log-group:airflow-MyAirflowEnvironment-Task:*"
      ]
    }
  ]
}
```

## Step 3: Create Access Key

```bash
aws iam create-access-key --user-name github-actions-mwaa-deployer
```

**Output will contain:**
```json
{
  "AccessKeyId": "AKIA...",
  "SecretAccessKey": "..."
}
```

⚠️ **Save these credentials securely and share them with the developer via a secure channel (NOT email/Slack).**

## Step 4: Developer Will Add to GitHub

The developer will run:
```bash
# Set the credentials (replace with actual values)
export AWS_ACCESS_KEY_ID="AKIA..."
export AWS_SECRET_ACCESS_KEY="..."

# Add to GitHub secrets
echo "$AWS_ACCESS_KEY_ID" | gh secret set AWS_ACCESS_KEY_ID
echo "$AWS_SECRET_ACCESS_KEY" | gh secret set AWS_SECRET_ACCESS_KEY
```

## Verification

Check the user was created successfully:
```bash
aws iam get-user --user-name github-actions-mwaa-deployer
aws iam list-user-policies --user-name github-actions-mwaa-deployer
aws iam list-access-keys --user-name github-actions-mwaa-deployer
```

## Security Notes

- This user has minimal permissions (S3, MWAA CLI token, CloudWatch logs only)
- Follows principle of least privilege
- Keys should be rotated periodically
- Only used for GitHub Actions automation

## Cleanup (if needed)

To remove the user:
```bash
# Delete access keys first
aws iam list-access-keys --user-name github-actions-mwaa-deployer
aws iam delete-access-key --user-name github-actions-mwaa-deployer --access-key-id AKIA...

# Delete inline policies
aws iam delete-user-policy --user-name github-actions-mwaa-deployer --policy-name MWAADagDeployment

# Delete user
aws iam delete-user --user-name github-actions-mwaa-deployer
```
