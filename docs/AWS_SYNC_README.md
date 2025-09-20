# AWS VPC Subnet Synchronization Service

🚀 **Automatically sync AWS VPC subnet data with your IPAM database using Docker Compose**

## 🏗️ Architecture

The AWS sync service runs as a separate Docker Compose service that:
- ✅ Continuously monitors your AWS VPCs for subnet changes
- ✅ Automatically adds new subnets to the database
- ✅ Updates existing subnet metadata (tags, state, etc.)
- ✅ Marks deleted subnets (soft delete)
- ✅ Runs independently from your main application
- ✅ Provides comprehensive logging and health monitoring

## 🚀 Quick Start

### 1. **Start the AWS Sync Service**
```bash
# Start just the sync service
./manage_aws_sync.sh start

# Or include it when starting the full application
docker-compose up -d  # This will start ALL services including aws-sync
```

### 2. **Configure AWS Credentials**
The service needs AWS credentials. Choose one method:

**Option A: AWS CLI (Recommended)**
```bash
aws configure
# Your credentials will be automatically mounted into the container
```

**Option B: Environment Variables**
```bash
# Create aws_sync.env file
cp aws_sync.env.example aws_sync.env
# Edit the file with your credentials
```

### 3. **Monitor and Manage**
```bash
# Check service status
./manage_aws_sync.sh status

# View logs
./manage_aws_sync.sh logs

# Follow logs in real-time
./manage_aws_sync.sh logs -f

# Run a one-time test
./manage_aws_sync.sh test

# Restart service
./manage_aws_sync.sh restart

# Stop service
./manage_aws_sync.sh stop
```

## 🎛️ Configuration

### Docker Compose Service Configuration

The `aws-sync` service in `docker-compose.yml` has these key settings:

```yaml
aws-sync:
  environment:
    SYNC_INTERVAL: 300        # Sync every 5 minutes
    AWS_DEFAULT_REGION: us-east-2
    SYNC_MODE: continuous     # Run continuously vs 'once'
  restart: unless-stopped     # Auto-restart on failure
  healthcheck:               # Monitor service health
    interval: 30s
  logging:                   # Rotate logs automatically
    max-size: "10m"
    max-file: "3"
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SYNC_INTERVAL` | 300 | Seconds between sync cycles |
| `AWS_DEFAULT_REGION` | us-east-2 | AWS region to sync |
| `SYNC_MODE` | continuous | 'continuous' or 'once' |
| `MAX_RETRIES` | 3 | Retry failed operations |
| `BATCH_SIZE` | 10 | Process VPCs in batches |

## 📊 Monitoring

### Service Status
```bash
./manage_aws_sync.sh status
```
Shows:
- ✅ Running status
- 🏥 Health check status  
- 📋 Recent activity
- 🔗 Container details

### Logs
```bash
# Recent logs
./manage_aws_sync.sh logs

# Follow live logs
./manage_aws_sync.sh logs -f

# Docker Compose logs
docker-compose logs aws-sync

# Log files (inside container)
docker-compose exec aws-sync cat logs/aws_sync.log
```

### Web Interface
After sync completes, check:
- **VPCs:** http://localhost:8080/vpcs
- **Prefixes:** http://localhost:8080/prefixes

## 🔧 Management Commands

### Start/Stop/Restart
```bash
# Start the sync service
./manage_aws_sync.sh start

# Stop the sync service  
./manage_aws_sync.sh stop

# Restart the sync service
./manage_aws_sync.sh restart
```

### Testing
```bash
# Run one-time sync test
./manage_aws_sync.sh test

# This will:
# 1. Temporarily stop continuous sync
# 2. Run one sync cycle
# 3. Restart continuous sync
# 4. Show results
```

### Troubleshooting
```bash
# Check logs for errors
./manage_aws_sync.sh logs | grep ERROR

# Check AWS connectivity
docker-compose exec aws-sync aws sts get-caller-identity

# Check database connectivity  
docker-compose exec aws-sync python -c "
from models import DatabaseManager
import os
db = DatabaseManager(os.getenv('DATABASE_URL'))
session = db.get_session()
print('DB connection OK')
session.close()
"

# Restart with fresh container
docker-compose stop aws-sync
docker-compose rm -f aws-sync
docker-compose up -d aws-sync
```

## 🔍 What Gets Synced

### For Each VPC Subnet:
- ✅ **CIDR block** (e.g., `10.101.1.0/24`)
- ✅ **AWS subnet ID** (e.g., `subnet-abc123`)
- ✅ **Availability Zone** (e.g., `us-east-2a`)
- ✅ **State** (e.g., `available`)
- ✅ **Tags** (all AWS tags)
- ✅ **Last sync timestamp**

### Database Integration:
- 🏗️ **Creates** new subnet prefixes automatically
- 🔄 **Updates** existing subnet metadata
- 🗑️ **Soft deletes** removed subnets (marks as deleted)
- 🔗 **Associates** with parent VPC prefixes
- 📝 **Logs** all operations

## 📁 File Structure

```
ipam4cloud/
├── docker-compose.yml       # Service definition
├── manage_aws_sync.sh       # Management script  
├── aws_sync.env.example     # Configuration template
├── app/
│   ├── aws_vpc_sync.py      # Main sync script
│   └── logs/
│       └── aws_sync.log     # Sync logs
└── AWS_SYNC_README.md       # This file
```

## 🚨 Important Notes

### Security
- 🔐 AWS credentials are mounted read-only
- 🔒 Database access uses same credentials as main app
- 📝 All operations are logged
- 🛡️ Soft deletes preserve data integrity

### Performance  
- ⚡ Only syncs VPCs registered in your database
- 🔄 Batch processing for large VPC lists
- 💾 Minimal database impact (inserts/updates only)
- 🎯 Smart sync (only changes what's different)

### Reliability
- 🔄 Auto-restart on container failure
- ❤️ Health checks monitor service status
- 📊 Comprehensive error handling
- 🔁 Retry logic for transient failures

## 🎉 Success!

When everything is working, you'll see:
1. **Service running:** `./manage_aws_sync.sh status` shows "Running ✅"
2. **Regular sync logs:** New entries every 5 minutes
3. **Web interface:** New subnets appear at http://localhost:8080/prefixes
4. **Healthy status:** Health checks passing

Happy syncing! 🚀
