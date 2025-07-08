.PHONY: init plan apply destroy clean fmt validate

# Initialize terraform
init:
	terraform init

# Plan terraform changes
plan:
	terraform plan

# Apply terraform changes
apply:
	terraform apply

# Destroy terraform infrastructure
destroy:
	terraform destroy

# Format terraform files
fmt:
	terraform fmt

# Validate terraform configuration
validate:
	terraform validate

# Clean terraform state and cache
clean:
	rm -rf .terraform/
	rm -f .terraform.lock.hcl
	rm -f terraform.tfstate*

# Show current state
show:
	terraform show

# Get bucket name from outputs
bucket-name:
	terraform output bucket_name

# Get bucket ARN from outputs
bucket-arn:
	terraform output bucket_arn

# Get IAM role ARN from outputs
role-arn:
	terraform output iam_role_arn

help:
	@echo "Available targets:"
	@echo "  init        - Initialize terraform"
	@echo "  plan        - Plan terraform changes"
	@echo "  apply       - Apply terraform changes"
	@echo "  destroy     - Destroy terraform infrastructure"
	@echo "  fmt         - Format terraform files"
	@echo "  validate    - Validate terraform configuration"
	@echo "  clean       - Clean terraform state and cache"
	@echo "  show        - Show current state"
	@echo "  bucket-name - Get S3 bucket name"
	@echo "  bucket-arn  - Get S3 bucket ARN"
	@echo "  role-arn    - Get IAM role ARN"