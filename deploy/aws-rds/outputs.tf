# ============================================================================
# RDS Outputs
# ============================================================================

output "rds_endpoint" {
  description = "RDS instance endpoint (hostname)"
  value       = aws_db_instance.main.endpoint
}

output "rds_address" {
  description = "RDS instance address (hostname only, without port)"
  value       = aws_db_instance.main.address
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_db_name" {
  description = "Database name"
  value       = aws_db_instance.main.db_name
}

output "rds_username" {
  description = "Database master username"
  value       = aws_db_instance.main.username
}

output "rds_password" {
  description = "Database password (sensitive)"
  value       = random_password.db_password.result
  sensitive   = true
}

output "rds_security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.rds.id
}

output "database_url" {
  description = "Complete database connection URL (sensitive)"
  value       = "postgresql://${aws_db_instance.main.username}:${urlencode(random_password.db_password.result)}@${aws_db_instance.main.address}:${aws_db_instance.main.port}/${aws_db_instance.main.db_name}"
  sensitive   = true
}

output "secrets_manager_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the password"
  value       = aws_secretsmanager_secret.db_password.arn
}

output "secrets_manager_secret_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.db_password.name
}

output "rds_subnet_ids" {
  description = "Subnet IDs used for RDS subnet group"
  value       = var.db_subnet_ids
}

# ============================================================================
# EC2 Outputs
# ============================================================================

output "instance_id" {
  description = "EC2 instance ID"
  value       = aws_instance.ipam4cloud_app.id
}

output "instance_private_ip" {
  description = "Private IP address of the instance"
  value       = aws_instance.ipam4cloud_app.private_ip
}

output "instance_public_ip" {
  description = "Public IP address of the instance (if available)"
  value       = aws_instance.ipam4cloud_app.public_ip
}

output "ec2_security_group_id" {
  description = "Security group ID for EC2 instance"
  value       = local.ec2_security_group_id
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = <<-EOT
  SSH to ipam4cloud-app host:
  
  Using Public IP:
  ssh -i ${var.create_key_pair ? "${var.project_name}-aws-rds-deployer-key" : var.existing_key_name != "" ? var.existing_key_name : "deployer-key.pem"} ec2-user@${aws_instance.ipam4cloud_app.public_ip}
  
  Using Private IP (if accessing from within VPC):
  ssh -i ${var.create_key_pair ? "${var.project_name}-aws-rds-deployer-key" : var.existing_key_name != "" ? var.existing_key_name : "deployer-key.pem"} ec2-user@${aws_instance.ipam4cloud_app.private_ip}
  
  Instance Details:
  - Instance ID: ${aws_instance.ipam4cloud_app.id}
  - Private IP: ${aws_instance.ipam4cloud_app.private_ip}
  - Public IP:  ${aws_instance.ipam4cloud_app.public_ip != "" ? aws_instance.ipam4cloud_app.public_ip : "N/A (may not have public IP)"}
  - Security Group ID: ${local.ec2_security_group_id}
  ${var.create_key_pair ? "\n  Note: Private key saved as: ${var.project_name}-aws-rds-deployer-key" : ""}
  EOT
}

output "application_urls" {
  description = "Application access URLs"
  value = {
    admin_portal   = "http://${aws_instance.ipam4cloud_app.public_ip}:8080"
    readonly_portal = "http://${aws_instance.ipam4cloud_app.public_ip}:8081"
    backend_api     = "http://${aws_instance.ipam4cloud_app.public_ip}:8000"
  }
}

# ============================================================================
# Combined Deployment Summary
# ============================================================================

output "deployment_summary" {
  description = "Summary of the combined deployment"
  value = <<-EOT
  ================================================================================
  IPAM4Cloud Deployment Summary
  ================================================================================
  
  RDS Database:
  - Endpoint: ${aws_db_instance.main.address}
  - Port: ${aws_db_instance.main.port}
  - Database: ${aws_db_instance.main.db_name}
  - Username: ${aws_db_instance.main.username}
  - Security Group: ${aws_security_group.rds.id}
  
  EC2 Instance:
  - Instance ID: ${aws_instance.ipam4cloud_app.id}
  - Private IP: ${aws_instance.ipam4cloud_app.private_ip}
  - Public IP: ${aws_instance.ipam4cloud_app.public_ip != "" ? aws_instance.ipam4cloud_app.public_ip : "N/A"}
  - Security Group: ${local.ec2_security_group_id}
  
  Application URLs:
  - Admin Portal: http://${aws_instance.ipam4cloud_app.public_ip}:8080
  - Read-Only Portal: http://${aws_instance.ipam4cloud_app.public_ip}:8081
  - Backend API: http://${aws_instance.ipam4cloud_app.public_ip}:8000
  
  ================================================================================
  EOT
}
