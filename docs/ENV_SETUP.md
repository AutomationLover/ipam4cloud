# Environment Setup Guide

This guide explains how to configure your environment for running the ipam4cloud application with AWS integration.

## Prerequisites

- Docker and Docker Compose
- AWS CLI configured with appropriate credentials
- Valid AWS account with VPC creation permissions

## Step 1: Create Environment Configuration

Copy the example environment file and customize it for your setup:

```bash
# Copy the example environment file
cp env.example .env

# Edit the .env file with your specific values
nano .env  # or your preferred editor
```

## Step 2: Configure AWS-Specific Settings

Update the following variables in your `.env` file:

### Required AWS Configuration
```bash
# Your AWS region
AWS_DEFAULT_REGION=us-east-2

# Your AWS account ID  
AWS_ACCOUNT_ID=012345678901

# Your test VPC IDs (create these using AWS CLI or Console)
TEST_VPC_1_ID=vpc-0123456789abcdef0
TEST_VPC_1_CIDR=10.101.0.0/16
TEST_VPC_1_NAME=ipam4cloud-test-vpc-1
TEST_VPC_1_ROUTABLE=true

TEST_VPC_2_ID=vpc-0123456789abcdef1
TEST_VPC_2_CIDR=10.102.0.0/16
TEST_VPC_2_NAME=ipam4cloud-test-vpc-2
TEST_VPC_2_ROUTABLE=false
```

### Optional AWS Credentials
If not using AWS CLI profiles or IAM roles, uncomment and set:
```bash
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
```

## Step 3: Generate Configuration Files

Generate the JSON configuration files from templates:

```bash
# Generate configuration files using your environment variables
python3 generate_config.py
```

This will create:
- `app/data/vpc_data.json` - VPC configurations with your specific values
- `app/data/manual_prefixes.json` - Prefix allocations with your VPC CIDRs

## Step 4: Create Test VPCs (Optional)

If you need to create test VPCs, use the provided commands:

```bash
# Set your AWS region
export AWS_DEFAULT_REGION=us-east-2

# Create VPC 1 (Routable)
aws ec2 create-vpc --cidr-block 10.101.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ipam4cloud-test-vpc-1}]'

# Create VPC 2 (Non-routable)  
aws ec2 create-vpc --cidr-block 10.102.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ipam4cloud-test-vpc-2}]'
```

Update your `.env` file with the returned VPC IDs.

## Step 5: Start the Application

```bash
# Generate configuration files first
python3 generate_config.py

# Start all services
docker-compose up -d

# Check that all services are running
docker-compose ps

# View AWS sync logs
docker-compose logs -f aws-sync
```

## Step 6: Verify Setup

1. **Check Web Interface**: Visit http://localhost:8080
2. **Verify VPCs**: Check http://localhost:8080/vpcs for your test VPCs
3. **Check Prefixes**: Visit http://localhost:8080/prefixes for prefix hierarchy
4. **Monitor Sync**: Check `docker-compose logs aws-sync` for sync status

## Configuration Reference

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AWS_DEFAULT_REGION` | AWS region for operations | `us-east-2` | Yes |
| `AWS_ACCOUNT_ID` | Your AWS account ID | - | Yes |
| `TEST_VPC_1_ID` | First test VPC ID | - | Yes |
| `TEST_VPC_1_CIDR` | First test VPC CIDR | - | Yes |
| `TEST_VPC_2_ID` | Second test VPC ID | - | Yes |
| `TEST_VPC_2_CIDR` | Second test VPC CIDR | - | Yes |
| `SYNC_MODE` | Sync mode (continuous/once) | `continuous` | No |
| `SYNC_INTERVAL` | Sync interval in seconds | `300` | No |
| `AWS_PAGE_SIZE` | AWS API page size | `100` | No |
| `DATABASE_URL` | Database connection URL | Auto-generated | No |

### File Structure
```
.
├── .env                              # Your environment configuration
├── env.example                       # Example environment file
├── generate_config.py               # Configuration generator
├── app/data/
│   ├── vpc_data.template.json       # VPC data template
│   ├── vpc_data.json               # Generated VPC configuration
│   ├── manual_prefixes.template.json # Prefix template
│   └── manual_prefixes.json        # Generated prefix configuration
└── docker-compose.yml              # Docker services configuration
```

## Troubleshooting

### Configuration Generation Issues
```bash
# Check for missing environment variables
python3 generate_config.py

# Validate generated JSON
python3 -m json.tool app/data/vpc_data.json
python3 -m json.tool app/data/manual_prefixes.json
```

### AWS Sync Issues
```bash
# Check AWS credentials
aws sts get-caller-identity

# View detailed sync logs
docker-compose logs aws-sync

# Test sync manually
docker-compose exec aws-sync python aws_vpc_sync.py
```

### Database Issues  
```bash
# Check database connectivity
docker-compose exec postgres psql -U prefix_user -d prefix_management -c "SELECT 1;"

# Reset database (⚠️  destroys all data)
docker-compose down
docker volume rm ipam4cloud_postgres_data
docker-compose up -d
```

## Security Notes

- The `.env` file is git-ignored to prevent credential exposure
- AWS credentials can be provided via environment variables, AWS CLI profiles, or IAM roles
- Use IAM roles when running in AWS environments
- Limit VPC permissions to minimum required for the application

## Next Steps

After setup is complete:
1. Create additional VPCs and subnets in AWS
2. Monitor the sync service for automatic updates
3. Use the web interface to manage prefix allocations
4. Set up monitoring and alerting for the sync service
