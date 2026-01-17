# Deployment Options

This folder contains deployment configurations for IPAM4Cloud. Choose the deployment option that best fits your needs.

## Deployment Options

### 1. All-in-Container Deployment

**Location**: `deploy/all-in-container/`

All services (database, backend, frontend) run in Docker containers on a single EC2 instance.

**Best for**:
- Development and testing
- Single-server deployments
- Quick setup and teardown
- Cost-effective for small deployments

**See**: [All-in-Container README](./all-in-container/README.md)

### 2. AWS RDS Deployment

**Location**: `deploy/aws-rds/`

Uses AWS RDS PostgreSQL for the database, with application containers running on EC2.

**Best for**:
- Production deployments
- High availability requirements
- Managed database services
- Scalable architectures

**See**: [AWS RDS README](./aws-rds/README.md)

## Quick Comparison

| Feature | All-in-Container | AWS RDS |
|---------|------------------|---------|
| Database | Containerized PostgreSQL | AWS RDS PostgreSQL |
| Setup Complexity | Simple | Combined (RDS + EC2 in one run) |
| Cost | Lower (~$154/month) | Higher (~$170/month) |
| High Availability | Single instance | RDS Multi-AZ option |
| Backup | Manual/Container volumes | Automated RDS backups |
| Scalability | Limited | Better (RDS scaling) |
| Best For | Dev/Test | Production |

## Common Prerequisites

Both deployment options require:

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.0 installed
3. **AWS CLI** configured with credentials
4. **VPC and Subnet** IDs where you want to deploy
5. **SSH Key Pair** (existing or create new)

## Getting Started

1. **Choose your deployment option** based on your needs
2. **Read the specific README** for your chosen option
3. **Configure variables** by copying `terraform.tfvars.example` to `terraform.tfvars`
4. **Update terraform.tfvars** with your AWS account details (VPC ID, subnet IDs, etc.)
5. **Deploy** using Terraform

## Important Notes

### Security

- **terraform.tfvars files are gitignored** - they contain sensitive information
- Never commit terraform.tfvars files to version control
- Use `terraform.tfvars.example` as a template

### Variable Configuration

All deployment configurations require you to provide:
- AWS region
- VPC ID
- Subnet ID(s)
- AWS Account ID (for AWS RDS sync operations)

These values are **not hardcoded** and must be provided in your `terraform.tfvars` file.

### AWS RDS Deployment

The AWS RDS deployment creates both RDS and EC2 resources in a single Terraform run. RDS connection details are automatically passed to the EC2 instance via user-data script, so no manual parameter passing is needed.

## Design Document

For detailed architecture and design decisions, see [DESIGN.md](./DESIGN.md).

## Support

For issues or questions:
1. Check the specific deployment option README
2. Review the [Design Document](./DESIGN.md)
3. Check Terraform outputs for connection details
4. Review AWS CloudWatch logs
