# Demo 2: AWS VPC Sync Demonstration

This demo shows how the AWS sync service automatically discovers and synchronizes VPC subnets from AWS into the IPAM system.

## Prerequisites

- Application running with AWS sync service configured
- AWS credentials configured (via environment variables or `~/.aws` directory)
- At least one AWS VPC registered in the IPAM system
- AWS CLI installed and configured (for creating test subnets)

## Overview

The AWS sync service:
1. Connects to AWS EC2 API
2. Discovers VPCs registered in the IPAM system
3. Fetches all subnets for each VPC
4. Creates/updates prefix entries for discovered subnets
5. Maintains hierarchical relationships (VPC → Subnets)

## Step-by-Step Guide

### Step 1: Set Up AWS Account and VPC Configuration

**Configure Environment Variables:**

Ensure your `.env` file or environment has the following AWS configuration:

```bash
# AWS Configuration
AWS_DEFAULT_REGION=us-east-2
AWS_ACCOUNT_ID=123456789012

# AWS Credentials (one of the following methods)
# Method 1: Environment variables
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Method 2: Use AWS CLI profile (recommended)
# Mount ~/.aws directory in docker-compose.yml
```

**Register VPC in IPAM:**

If you haven't already, register your AWS VPC in the IPAM system:

```bash
curl -X POST "http://localhost:8000/api/vpcs" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Test VPC for sync demo",
    "provider": "aws",
    "provider_account_id": "123456789012",
    "provider_vpc_id": "vpc-0123456789abcdef0",
    "region": "us-east-2",
    "tags": {"Name": "sync-demo-vpc"}
  }'
```

**Note the VPC ID** returned in the response (UUID format).

### Step 2: Verify Sync Service Configuration

**Check Docker Compose Configuration:**

The AWS sync service should be configured in `containers/docker-compose.yml`:

```yaml
aws-sync:
  environment:
    DATABASE_URL: ${DATABASE_URL}
    AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION}
    AWS_ACCOUNT_ID: ${AWS_ACCOUNT_ID}
    SYNC_MODE: ${SYNC_MODE:-continuous}
    SYNC_INTERVAL: ${SYNC_INTERVAL:-300}
```

**Check Sync Service Status:**

```bash
# Check if the sync container is running
docker compose -f containers/docker-compose.yml ps aws-sync

# View sync service logs
docker compose -f containers/docker-compose.yml logs aws-sync
```

### Step 3: Run Initial Sync

**Option A: If sync is running in continuous mode**

The sync service runs automatically every 5 minutes (default). You can wait for the next sync cycle or trigger it manually.

**Option B: Run sync manually**

```bash
# Restart the sync container to trigger a sync cycle
docker compose -f containers/docker-compose.yml restart aws-sync

# Or execute sync directly in the container
docker compose -f containers/docker-compose.yml exec aws-sync python aws_vpc_sync.py
```

**Option C: Run sync once (if SYNC_MODE=once)**

```bash
# Set SYNC_MODE=once in .env, then restart
docker compose -f containers/docker-compose.yml restart aws-sync
```

### Step 4: Check Initial Sync Results

**View Container Logs:**

```bash
# Follow sync logs in real-time
docker compose -f containers/docker-compose.yml logs -f aws-sync

# View last 50 lines
docker compose -f containers/docker-compose.yml logs --tail=50 aws-sync
```

**Expected Log Output:**
```
INFO - Starting AWS VPC subnet synchronization cycle
INFO - AWS EC2 client initialized for region: us-east-2
INFO - Syncing VPC: vpc-0123456789abcdef0 (Test VPC for sync demo)
INFO - Found 3 subnets in VPC vpc-0123456789abcdef0
INFO - Created 3 new subnet prefixes
INFO - Sync cycle completed: 1/1 VPCs synced in 2.34s
```

**Check Frontend (Port 8080):**

1. Navigate to `http://localhost:8080`
2. Go to **"Prefixes"** page
3. Filter by **Source: VPC** to see synced subnets
4. Look for prefixes with `source: "vpc"` - these are from AWS sync

**Check via API:**

```bash
# Get all prefixes with source=vpc
curl "http://localhost:8000/api/prefixes?source=vpc"

# Get prefixes for a specific VPC
curl "http://localhost:8000/api/vpcs/{vpc_id}/associations"
```

### Step 5: Create a Subnet in AWS

Use AWS CLI to create a new subnet in your VPC:

```bash
# Set your AWS region
export AWS_DEFAULT_REGION=us-east-2

# Create a new subnet in your VPC
aws ec2 create-subnet \
  --vpc-id vpc-0123456789abcdef0 \
  --cidr-block 10.0.100.0/24 \
  --availability-zone us-east-2a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=sync-demo-subnet}]'
```

**Note the subnet ID** returned (e.g., `subnet-0123456789abcdef0`).

**Verify Subnet Creation:**

```bash
# List subnets in your VPC
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=vpc-0123456789abcdef0" \
  --query 'Subnets[*].[SubnetId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

### Step 6: Rerun Prefix AWS Sync

After creating the subnet in AWS, trigger another sync to discover it:

```bash
# Restart sync service to trigger immediate sync
docker compose -f containers/docker-compose.yml restart aws-sync

# Or wait for the next automatic sync cycle (default: 5 minutes)
```

**Monitor Sync Logs:**

```bash
# Watch logs in real-time
docker compose -f containers/docker-compose.yml logs -f aws-sync
```

**Expected Log Output:**
```
INFO - Starting AWS VPC subnet synchronization cycle
INFO - Syncing VPC: vpc-0123456789abcdef0 (Test VPC for sync demo)
INFO - Found 4 subnets in VPC vpc-0123456789abcdef0
INFO - Created 1 new subnet prefix (subnet-0123456789abcdef0)
INFO - Updated 3 existing subnet prefixes
INFO - Sync cycle completed: 1/1 VPCs synced in 2.45s
```

### Step 7: Verify New Subnet in Frontend

**Check Frontend (Port 8080):**

1. Navigate to `http://localhost:8080`
2. Go to **"Prefixes"** page
3. Filter by **Source: VPC**
4. Look for the new subnet `10.0.100.0/24`
5. Verify it appears under the VPC prefix in the tree view

**Check via API:**

```bash
# Get all VPC-sourced prefixes
curl "http://localhost:8000/api/prefixes?source=vpc" | jq '.[] | select(.cidr == "10.0.100.0/24")'

# Get VPC details with associations
curl "http://localhost:8000/api/vpcs/{vpc_id}"
```

### Step 8: Verify Subnet Details

**Check Prefix Details:**

The synced subnet should have:
- `source: "vpc"` (not "manual")
- `vpc_id` pointing to the VPC UUID
- Tags from AWS (if any)
- Proper parent-child relationship with the VPC prefix

**View in Tree Structure:**

```bash
# Get prefix tree view
curl "http://localhost:8000/api/prefixes/tree?vrf_id=prod-vrf" | jq '.'
```

The subnet should appear as a child of the VPC prefix.

## Understanding Sync Behavior

### What Gets Synced

- ✅ All subnets in registered VPCs
- ✅ Subnet CIDR blocks
- ✅ Subnet tags from AWS
- ✅ Routable status (inherited from VPC prefix)
- ✅ Hierarchical relationships

### What Doesn't Get Synced

- ❌ Subnets in VPCs not registered in IPAM
- ❌ Manual prefixes (source = "manual")
- ❌ VPCs from other AWS accounts/regions not configured

### Sync Modes

**Continuous Mode (default):**
- Runs automatically every `SYNC_INTERVAL` seconds (default: 300 = 5 minutes)
- Continuously monitors for changes
- Best for production environments

**Once Mode:**
- Runs once and exits
- Useful for testing or manual syncs
- Set `SYNC_MODE=once` in environment

### Sync Logs Location

Logs are stored in:
- Container: `/app/logs/aws_sync.log`
- Host: `containers/app/logs/aws_sync.log` (if volume mounted)

## Troubleshooting

### Sync Service Not Running

```bash
# Check container status
docker compose -f containers/docker-compose.yml ps aws-sync

# Check logs for errors
docker compose -f containers/docker-compose.yml logs aws-sync

# Restart the service
docker compose -f containers/docker-compose.yml restart aws-sync
```

### AWS Credentials Issues

```bash
# Test AWS credentials
aws sts get-caller-identity

# Verify AWS region
aws ec2 describe-regions --region-names us-east-2

# Check VPC access
aws ec2 describe-vpcs --vpc-ids vpc-0123456789abcdef0
```

### No Subnets Discovered

- Verify VPC is registered in IPAM system
- Check AWS region matches configuration
- Verify AWS account ID is correct
- Check VPC ID format (should start with `vpc-`)
- Ensure VPC exists in AWS and is accessible

### Subnets Not Appearing in Frontend

- Check sync logs for errors
- Verify database connection
- Check if VRF exists (subnets use default VRF or VRF from VPC prefix)
- Refresh the frontend page
- Check filters in frontend (ensure "Source: VPC" filter is not excluding results)

### Sync Performance Issues

- Increase `AWS_PAGE_SIZE` for large VPCs
- Adjust `SYNC_INTERVAL` for less frequent syncs
- Check `MAX_SUBNETS_PER_VPC` limit
- Monitor database performance

## Advanced: Testing Sync Script

Use the provided test script:

```bash
# Run sync test script
./scripts/utils/test_aws_sync.sh

# Monitor sync with dashboard
./scripts/utils/monitor_sync.sh
```

## Summary

You have successfully:
- ✅ Configured AWS sync service
- ✅ Registered an AWS VPC in IPAM
- ✅ Run initial sync to discover existing subnets
- ✅ Created a new subnet in AWS
- ✅ Rerun sync to discover the new subnet
- ✅ Verified the subnet appears in the frontend GUI

## Next Steps

- Explore the hierarchical tree view showing VPC → Subnets
- Create manual prefixes alongside VPC-sourced prefixes
- Set up multiple VPCs and regions
- Configure sync intervals for your environment

