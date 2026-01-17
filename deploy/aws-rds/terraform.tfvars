# General Terraform variables file
# This file is gitignored and contains your actual values
#
# IMPORTANT: Also ensure network.auto.tfvars exists with your VPC and subnet IDs

# ============================================================================
# AWS Configuration
# ============================================================================
aws_sync_region = "us-east-2"  # AWS region for VPC sync operations (sync target VPCs)
aws_account_id = "267406360448"

# ============================================================================
# Project Configuration
# ============================================================================
project_name = "ipam4cloud"
environment = "dev"

# ============================================================================
# RDS Configuration
# ============================================================================
db_engine_version = "15.15"
db_instance_class = "db.t3.micro"
db_name = "prefix_management"
db_username = "prefix_user"
db_allocated_storage = 20
db_max_allocated_storage = 100
db_backup_retention_days = 7
db_multi_az = false
db_deletion_protection = false
db_performance_insights_enabled = false
db_monitoring_interval = 0

# ============================================================================
# EC2 Configuration
# ============================================================================
instance_type = "t3.xlarge"
root_volume_size = 50
repository_url = "https://github.com/AutomationLover/ipam4cloud.git"

# ============================================================================
# Security Group Configuration
# ============================================================================
create_ec2_security_group = true

# ============================================================================
# Key Pair Configuration
# ============================================================================
# Terraform will automatically generate SSH key locally and upload to AWS
# Private key will be saved as: ipam4cloud-aws-rds-deployer-key (gitignored)
# Public key will be saved as: ipam4cloud-aws-rds-deployer-key.pub (gitignored)
create_key_pair = true

# ============================================================================
# Sync Target VPCs (for reference - used by application, not Terraform)
# ============================================================================
# Sync target VPCs in us-east-2:
# - vpc-017ac1c51153a77ea
# - vpc-0bfab826e7f965381
# These are configured in the application's .env file, not Terraform
