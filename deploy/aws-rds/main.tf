provider "aws" {
  region = var.aws_region
}

provider "tls" {
  # No configuration needed
}

# Generate random password for RDS
resource "random_password" "db_password" {
  length  = 16
  special = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store password in AWS Secrets Manager (optional but recommended)
resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.project_name}-${var.environment}-rds-password"
  description             = "RDS database password for ${var.project_name} (${var.environment})"
  recovery_window_in_days = 0 # For testing - set to 7+ for production
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

# ============================================================================
# EC2 Security Group (created first so RDS can reference it)
# ============================================================================

resource "aws_security_group" "ipam4cloud_ec2" {
  count = var.create_ec2_security_group ? 1 : 0
  
  name        = "${var.project_name}-${var.environment}-ec2-sg"
  description = "Security group for ipam4cloud EC2 instance: SSH (22), Admin Portal (8080), Read-Only Portal (8081), Backend API (8000), and ICMP (ping)"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow SSH access"
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Admin Portal access"
  }

  ingress {
    from_port   = 8081
    to_port     = 8081
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Read-Only Portal access"
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Backend API access"
  }

  ingress {
    from_port   = -1
    to_port     = -1
    protocol    = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow PING (ICMP)"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ec2-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

locals {
  # Determine EC2 security group ID
  ec2_security_group_id = var.create_ec2_security_group ? aws_security_group.ipam4cloud_ec2[0].id : var.existing_ec2_security_group_id
}

# ============================================================================
# RDS Resources
# ============================================================================

# DB Subnet Group - RDS needs to be in at least 2 AZs
# Validation is handled at the variable level (see variables.tf)
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.db_subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Security Group for RDS - allows inbound from EC2 security group
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for RDS PostgreSQL database"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [local.ec2_security_group_id]
    description     = "Allow PostgreSQL access from EC2 instances"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Project     = var.project_name
    Environment = var.environment
  }
}

# DB Parameter Group (optional - for custom PostgreSQL settings)
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-postgres15"
  family = "postgres15"

  # Example: Set timezone
  parameter {
    name  = "timezone"
    value = "UTC"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-postgres15-params"
    Project     = var.project_name
    Environment = var.environment
  }
}

# RDS PostgreSQL Instance
resource "aws_db_instance" "main" {
  identifier     = "${var.project_name}-${var.environment}-db"
  engine         = "postgres"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class

  # Database configuration
  db_name  = var.db_name
  username = var.db_username
  password = random_password.db_password.result

  # Storage configuration
  allocated_storage     = var.db_allocated_storage
  max_allocated_storage = var.db_max_allocated_storage
  storage_type         = "gp3"
  storage_encrypted     = true

  # Network configuration
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false # RDS in private subnet

  # Database configuration
  parameter_group_name = aws_db_parameter_group.main.name
  port                 = 5432

  # Backup configuration
  backup_retention_period = var.db_backup_retention_days
  backup_window          = "03:00-04:00" # UTC
  maintenance_window     = "mon:04:00-mon:05:00" # UTC

  # Multi-AZ (optional - set to true for production)
  multi_az = var.db_multi_az

  # Deletion protection (set to true for production)
  deletion_protection = var.db_deletion_protection
  skip_final_snapshot = !var.db_deletion_protection

  # Performance Insights (optional)
  performance_insights_enabled = var.db_performance_insights_enabled

  # Monitoring
  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]
  monitoring_interval            = var.db_monitoring_interval
  monitoring_role_arn            = var.db_monitoring_role_arn

  tags = {
    Name        = "${var.project_name}-${var.environment}-db"
    Project     = var.project_name
    Environment = var.environment
  }
}

# ============================================================================
# EC2 Resources
# ============================================================================

# Generate SSH key pair locally
resource "tls_private_key" "deployer" {
  count     = var.create_key_pair ? 1 : 0
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Save private key locally (gitignored)
resource "local_file" "private_key" {
  count           = var.create_key_pair ? 1 : 0
  content         = tls_private_key.deployer[0].private_key_pem
  filename        = "${var.project_name}-aws-rds-deployer-key"
  file_permission = "0600"
}

# Save public key locally (gitignored)
resource "local_file" "public_key" {
  count           = var.create_key_pair ? 1 : 0
  content         = tls_private_key.deployer[0].public_key_openssh
  filename        = "${var.project_name}-aws-rds-deployer-key.pub"
  file_permission = "0644"
}

# Upload public key to AWS
resource "aws_key_pair" "deployer" {
  count      = var.create_key_pair ? 1 : 0
  key_name   = "${var.project_name}-aws-rds-deployer-key"
  public_key = tls_private_key.deployer[0].public_key_openssh

  tags = {
    Name        = "${var.project_name}-aws-rds-deployer-key"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Get AMI for Amazon Linux 2023
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
}

# Generate environment file from RDS outputs
locals {
  # Direct reference to RDS resources - no remote state needed!
  rds_endpoint = aws_db_instance.main.address
  rds_port     = aws_db_instance.main.port
  rds_db_name  = aws_db_instance.main.db_name
  rds_username = aws_db_instance.main.username
  rds_password = random_password.db_password.result
  
  database_url = "postgresql://${local.rds_username}:${urlencode(local.rds_password)}@${local.rds_endpoint}:${local.rds_port}/${local.rds_db_name}"
}

# EC2 Instance
resource "aws_instance" "ipam4cloud_app" {
  # Wait for RDS to be available before creating EC2
  depends_on = [aws_db_instance.main]
  
  ami                    = data.aws_ami.amazon_linux_2023.id
  vpc_security_group_ids = [local.ec2_security_group_id]
  subnet_id              = var.ec2_subnet_id
  instance_type          = var.instance_type
  key_name               = var.create_key_pair ? aws_key_pair.deployer[0].key_name : var.existing_key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }

  user_data_replace_on_change = true
  user_data                   = <<EOF
#!/bin/bash
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

# Install dependencies
sudo dnf update -y
sudo dnf install -y unzip git postgresql15

# Install Docker
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user

# Install Docker Compose v2
sudo mkdir -p /usr/local/lib/docker/cli-plugins
DOCKER_COMPOSE_VERSION=`curl -s https://api.github.com/repos/docker/compose/releases/latest | python3 -c "import sys, json; print(json.load(sys.stdin)['tag_name'])"`
sudo curl -f -L "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
sudo ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

# Install Docker Buildx
BUILDX_VERSION=`curl -s https://api.github.com/repos/docker/buildx/releases/latest | python3 -c "import sys, json; print(json.load(sys.stdin)['tag_name'])"`
sudo curl -f -L "https://github.com/docker/buildx/releases/download/$${BUILDX_VERSION}/buildx-$${BUILDX_VERSION}.linux-amd64" -o /usr/local/lib/docker/cli-plugins/docker-buildx
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
sudo docker buildx create --name builder --use || true
sudo docker buildx inspect --bootstrap || true

# Clone repository
sudo rm -rf /home/ec2-user/ipam4cloud
sudo -u ec2-user bash -c "cd /home/ec2-user && git clone ${var.repository_url}"
sudo chown -R ec2-user:ec2-user /home/ec2-user/ipam4cloud
sudo chmod -R 755 /home/ec2-user/ipam4cloud
sudo chmod +x /home/ec2-user/ipam4cloud/manage.sh

# Create environment file with RDS connection details
cat > /home/ec2-user/ipam4cloud/.env <<ENVEOF
# Database Configuration (AWS RDS)
DATABASE_URL=${local.database_url}

# AWS Configuration for Sync Operations
AWS_DEFAULT_REGION=${var.aws_sync_region}
AWS_ACCOUNT_ID=${var.aws_account_id}

# AWS Sync Configuration
SYNC_MODE=continuous
SYNC_INTERVAL=300
AWS_PAGE_SIZE=100
MAX_SUBNETS_PER_VPC=1000
DB_BATCH_SIZE=50

# Application Configuration
LOG_LEVEL=INFO
LOG_DIR=logs
DEFAULT_VRF_ID=prod-vrf

# Use RDS instead of container DB
USE_RDS=true
ENVEOF

sudo chown ec2-user:ec2-user /home/ec2-user/ipam4cloud/.env
sudo chmod 600 /home/ec2-user/ipam4cloud/.env

# Wait for RDS to be ready (check connection)
echo "Waiting for RDS to be ready..."
export PGPASSWORD='${local.rds_password}'
for i in {1..30}; do
  if PGPASSWORD='${local.rds_password}' psql -h ${local.rds_endpoint} -p ${local.rds_port} -U ${local.rds_username} -d ${local.rds_db_name} -c "SELECT 1;" > /dev/null 2>&1; then
    echo "RDS is ready!"
    break
  fi
  echo "Waiting for RDS... ($i/30)"
  sleep 10
done

# Run database initialization script (if available)
if [ -f /home/ec2-user/ipam4cloud/deploy/aws-rds/scripts/init-rds-db.sh ]; then
  echo "Running database initialization script..."
  sudo chmod +x /home/ec2-user/ipam4cloud/deploy/aws-rds/scripts/init-rds-db.sh
  sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud && PGHOST='${local.rds_endpoint}' PGPORT='${local.rds_port}' PGDATABASE='${local.rds_db_name}' PGUSER='${local.rds_username}' PGPASSWORD='${local.rds_password}' deploy/aws-rds/scripts/init-rds-db.sh" || echo "Database initialization completed with warnings (may already be initialized)"
else
  # Fallback: Run SQL files directly
  echo "Running SQL initialization files directly..."
  sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud && PGPASSWORD='${local.rds_password}' psql -h ${local.rds_endpoint} -p ${local.rds_port} -U ${local.rds_username} -d ${local.rds_db_name} -f containers/init/01_schema.sql" || echo "Schema already exists or error occurred"
  sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud && PGPASSWORD='${local.rds_password}' psql -h ${local.rds_endpoint} -p ${local.rds_port} -U ${local.rds_username} -d ${local.rds_db_name} -f containers/init/02_seed_data.sql" || echo "Seed data already exists or error occurred"
  sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud && PGPASSWORD='${local.rds_password}' psql -h ${local.rds_endpoint} -p ${local.rds_port} -U ${local.rds_username} -d ${local.rds_db_name} -f containers/init/03_idempotency.sql" || echo "Idempotency schema already exists or error occurred"
  sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud && PGPASSWORD='${local.rds_password}' psql -h ${local.rds_endpoint} -p ${local.rds_port} -U ${local.rds_username} -d ${local.rds_db_name} -f containers/init/04_add_device42_source.sql" || echo "Device42 source already exists or error occurred"
fi

# Ensure docker-compose.rds.yml exists (it should be in the repo, but create if missing)
if [ ! -f /home/ec2-user/ipam4cloud/containers/docker-compose.rds.yml ]; then
  echo "Warning: docker-compose.rds.yml not found in repo, it should be committed to the repository"
fi

# Start application with standalone RDS docker-compose file
echo "Starting application containers with RDS..."
cd /home/ec2-user/ipam4cloud/containers
export $(grep -v '^#' /home/ec2-user/ipam4cloud/.env | xargs)
sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud/containers && export \$(grep -v '^#' ../.env | xargs) && docker compose -f docker-compose.rds.yml up -d --build" || echo "Docker compose failed, check logs for details"

echo "User-data script completed successfully at $(date)"
EOF

  tags = {
    Name        = "${var.project_name}-${var.environment}-app"
    Role        = "ipam-app"
    Project     = var.project_name
    Environment = var.environment
  }
}
