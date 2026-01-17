variable "aws_region" {
  description = "AWS region for infrastructure deployment"
  type        = string
  # No default - user must provide their region
}

variable "aws_sync_region" {
  description = "AWS region for VPC sync operations (can be different from infrastructure region)"
  type        = string
}

variable "aws_account_id" {
  description = "AWS Account ID for sync operations"
  type        = string
}

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

variable "vpc_id" {
  description = "VPC ID where the application instance will be deployed"
  type        = string
  # No default - user must provide their VPC ID
}

variable "subnet_id" {
  description = "Subnet ID for the EC2 instance"
  type        = string
  # No default - user must provide their subnet ID
}

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

# Key Pair Configuration
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
