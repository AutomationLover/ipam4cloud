# ============================================================================
# AWS Configuration
# ============================================================================

variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
}

variable "aws_sync_region" {
  description = "AWS region for VPC sync operations (can be different from infrastructure region)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS Account ID for sync operations"
  type        = string
}

# ============================================================================
# Project Configuration
# ============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "ipam4cloud"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

# ============================================================================
# VPC Configuration
# ============================================================================

variable "vpc_id" {
  description = "VPC ID where resources will be deployed"
  type        = string
}

variable "db_subnet_ids" {
  description = "List of subnet IDs for DB subnet group. AWS RDS requires at least 2 subnets in different AZs (even for single-AZ instances)."
  type        = list(string)
}

variable "ec2_subnet_id" {
  description = "Subnet ID for EC2 instance"
  type        = string
}

# ============================================================================
# RDS Configuration
# ============================================================================

variable "db_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "15.15"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "Name of the database"
  type        = string
  default     = "prefix_management"
}

variable "db_username" {
  description = "Master username for the database"
  type        = string
  default     = "prefix_user"
}

variable "db_allocated_storage" {
  description = "Initial allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_max_allocated_storage" {
  description = "Maximum allocated storage for autoscaling in GB"
  type        = number
  default     = 100
}

variable "db_backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "db_multi_az" {
  description = "Enable Multi-AZ deployment for high availability"
  type        = bool
  default     = false
}

variable "db_deletion_protection" {
  description = "Enable deletion protection"
  type        = bool
  default     = false
}

variable "db_performance_insights_enabled" {
  description = "Enable Performance Insights"
  type        = bool
  default     = false
}

variable "db_monitoring_interval" {
  description = "Enhanced monitoring interval in seconds (0, 60, 300)"
  type        = number
  default     = 0
}

variable "db_monitoring_role_arn" {
  description = "IAM role ARN for enhanced monitoring (optional)"
  type        = string
  default     = ""
}

# ============================================================================
# EC2 Configuration
# ============================================================================

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.xlarge"
}

variable "root_volume_size" {
  description = "Root volume size in GB"
  type        = number
  default     = 50
}

variable "repository_url" {
  description = "Git repository URL to clone"
  type        = string
  default     = "https://github.com/AutomationLover/ipam4cloud.git"
}

# ============================================================================
# Security Group Configuration
# ============================================================================

variable "create_ec2_security_group" {
  description = "Create new security group for EC2"
  type        = bool
  default     = true
}

variable "existing_ec2_security_group_id" {
  description = "Existing security group ID to use (if create_ec2_security_group is false)"
  type        = string
  default     = ""
}

# ============================================================================
# Key Pair Configuration
# ============================================================================

variable "create_key_pair" {
  description = "Create new SSH key pair locally and upload to AWS. If false, use existing_key_name."
  type        = bool
  default     = true
}

variable "existing_key_name" {
  description = "Existing AWS key pair name to use (required if create_key_pair is false)"
  type        = string
  default     = ""
}
