provider "aws" {
  region = var.aws_region
}

provider "tls" {
  # No configuration needed
}

resource "aws_security_group" "ipam4cloud_app" {
  name        = "${var.project_name}-app"
  description = "Security group for ipam4cloud application: SSH (22), Admin Portal (8080), Read-Only Portal (8081), Backend API (8000), Database (5432), and ICMP (ping)"
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
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow Database access"
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
    Name        = "${var.project_name}-app"
    Project     = var.project_name
    Environment = var.environment
  }
}

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
  filename        = "${var.project_name}-${var.environment}-allinone-deployer-key"
  file_permission = "0600"
}

# Save public key locally (gitignored)
resource "local_file" "public_key" {
  count           = var.create_key_pair ? 1 : 0
  content         = tls_private_key.deployer[0].public_key_openssh
  filename        = "${var.project_name}-${var.environment}-allinone-deployer-key.pub"
  file_permission = "0644"
}

# Upload public key to AWS
resource "aws_key_pair" "deployer" {
  count      = var.create_key_pair ? 1 : 0
  key_name   = "${var.project_name}-${var.environment}-allinone-deployer-key"
  public_key = tls_private_key.deployer[0].public_key_openssh

  tags = {
    Name        = "${var.project_name}-${var.environment}-allinone-deployer-key"
    Project     = var.project_name
    Environment = var.environment
  }
}

# Amazon Linux 2023 (easier Docker installation)
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

resource "aws_instance" "ipam4cloud_app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  vpc_security_group_ids = [aws_security_group.ipam4cloud_app.id]
  subnet_id              = var.subnet_id

  instance_type = var.instance_type
  key_name      = var.create_key_pair ? aws_key_pair.deployer[0].key_name : var.existing_key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = var.root_volume_size
    encrypted   = true
  }
  
  user_data_replace_on_change = true
  user_data                   = <<-EOF
              #!/bin/bash
              # Amazon Linux 2023 uses dnf/yum package manager
              exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
              sudo dnf update -y
              sudo dnf install -y unzip git
              # Verify git installation
              git --version
              # Install Docker Engine v2 (Amazon Linux 2023 has Docker available via dnf)
              sudo dnf install -y docker
              # Start and enable Docker service
              sudo systemctl start docker
              sudo systemctl enable docker
              # Add ec2-user to docker group
              sudo usermod -aG docker ec2-user
              # Install Docker Compose v2 as Docker CLI plugin
              # Create plugin directory
              sudo mkdir -p /usr/local/lib/docker/cli-plugins
              # Download Docker Compose v2 binary (using latest release)
              # Use Python JSON parsing for reliable version extraction
              DOCKER_COMPOSE_VERSION=`curl -s https://api.github.com/repos/docker/compose/releases/latest | python3 -c "import sys, json; print(json.load(sys.stdin)['tag_name'])"`
              sudo curl -f -L "https://github.com/docker/compose/releases/download/$${DOCKER_COMPOSE_VERSION}/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose || { echo "Failed to download Docker Compose version $${DOCKER_COMPOSE_VERSION}"; exit 1; }
              # Make it executable
              sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
              # Create symlink for docker-compose command (optional, for backward compatibility)
              sudo ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose
              # Install Docker Buildx (required for docker compose build)
              # Use Python JSON parsing for reliable version extraction
              BUILDX_VERSION=`curl -s https://api.github.com/repos/docker/buildx/releases/latest | python3 -c "import sys, json; print(json.load(sys.stdin)['tag_name'])"`
              # Download Buildx binary
              sudo curl -f -L "https://github.com/docker/buildx/releases/download/$${BUILDX_VERSION}/buildx-$${BUILDX_VERSION}.linux-amd64" -o /usr/local/lib/docker/cli-plugins/docker-buildx || { echo "Failed to download Docker Buildx version $${BUILDX_VERSION}"; exit 1; }
              # Make it executable
              sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-buildx
              # Create builder instance (required for buildx to work)
              sudo docker buildx create --name builder --use || true
              sudo docker buildx inspect --bootstrap || true
              # Verify installations
              sudo docker version || echo "Docker version check failed"
              sudo docker compose version || echo "Docker compose version check failed"
              sudo docker-compose version || echo "Docker-compose version check failed"
              sudo docker buildx version || echo "Docker buildx version check failed"
              # Ensure ec2-user home directory has proper permissions
              sudo chown -R ec2-user:ec2-user /home/ec2-user
              sudo chmod 755 /home/ec2-user
              # Remove ipam4cloud directory if it exists (from previous runs)
              sudo rm -rf /home/ec2-user/ipam4cloud
              # Clone ipam4cloud repository as ec2-user
              sudo -u ec2-user bash -c "cd /home/ec2-user && git clone ${var.repository_url}"
              # Ensure proper ownership and permissions (double-check after clone)
              sudo chown -R ec2-user:ec2-user /home/ec2-user/ipam4cloud
              sudo chmod -R 755 /home/ec2-user/ipam4cloud
              sudo chmod -R u+w /home/ec2-user/ipam4cloud
              # Make manage.sh executable
              sudo chmod +x /home/ec2-user/ipam4cloud/manage.sh
              # Run ipam4cloud setup as ec2-user
              sudo -u ec2-user bash -c "cd /home/ec2-user/ipam4cloud && ./manage.sh restart --clean" || echo "manage.sh failed, but continuing"
              echo "User-data script completed successfully at $(date)"
              EOF
              
  tags = {
    Name        = "${var.project_name}-app"
    Role        = "ipam-app"
    Project     = var.project_name
    Environment = var.environment
  }
}

output "instance_private_ip" {
  value       = aws_instance.ipam4cloud_app.private_ip
  description = "Private IP address of the instance"
}

output "instance_public_ip" {
  value       = aws_instance.ipam4cloud_app.public_ip
  description = "Public IP address of the instance (if available)"
}

output "private_key_file" {
  value       = var.create_key_pair ? local_file.private_key[0].filename : "N/A (using existing key pair)"
  description = "Path to the generated private key file (if create_key_pair is true)"
}

output "ssh_command_to_ipam4cloud" {
  value       = <<-EOT
  SSH to ipam4cloud-app host:
  
  Using Public IP:
  ssh -i ${var.create_key_pair ? "${var.project_name}-${var.environment}-allinone-deployer-key" : "deployer-key.pem"} ec2-user@${aws_instance.ipam4cloud_app.public_ip}
  
  Using Private IP (if accessing from within VPC):
  ssh -i ${var.create_key_pair ? "${var.project_name}-${var.environment}-allinone-deployer-key" : "deployer-key.pem"} ec2-user@${aws_instance.ipam4cloud_app.private_ip}
  
  Instance Details:
  - Private IP: ${aws_instance.ipam4cloud_app.private_ip}
  - Public IP:  ${aws_instance.ipam4cloud_app.public_ip != "" ? aws_instance.ipam4cloud_app.public_ip : "N/A (may not have public IP)"}
  - AMI: Amazon Linux 2023 (with Docker v2 support)
  
  ================================================================================
  CHECK IF USER-DATA INITIALIZATION IS COMPLETE
  ================================================================================
  
  Best method - Check cloud-init status:
  sudo cloud-init status
  # Status will be: "status: running" or "status: done" or "status: error"
  
  Wait until complete (blocks until done):
  sudo cloud-init status --wait
  
  Quick status check:
  sudo cloud-init status | grep -q "done" && echo "✓ Initialization complete" || echo "✗ Still initializing or error"
  
  Check user-data script completion:
  sudo tail -1 /var/log/user-data.log | grep -q "completed successfully" && echo "✓ User-data script complete" || echo "✗ User-data script not complete"
  
  ================================================================================
  USER-DATA LOG LOCATION
  ================================================================================
  
  View last 20 lines:
  sudo tail -20 /var/log/user-data.log
  
  Follow log in real-time:
  sudo tail -f /var/log/user-data.log
  
  View full log:
  sudo cat /var/log/user-data.log
  
  Alternative log locations:
  sudo cat /var/log/cloud-init-output.log
  sudo cat /var/lib/cloud/data/result.json  # Cloud-init result status
  EOT
  description = "SSH connection information and initialization status check guide"
}
