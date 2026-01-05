# IPAM4Cloud Deployment Guide - AWS Instance Sizing

## Overview

This guide provides recommendations for selecting the appropriate AWS EC2 instance type for deploying the IPAM4Cloud application based on workload analysis and resource requirements.

## Application Architecture

The IPAM4Cloud system consists of the following containerized services:

1. **PostgreSQL 15** - Primary database for prefix management
2. **Backend API** - FastAPI-based REST API service
3. **Admin Frontend** - Vue.js admin portal (port 8080)
4. **Read-Only Frontend** - Vue.js read-only portal (port 8081)
5. **App Service** - Python initialization and demo application
6. **AWS Sync Service** - Continuous VPC subnet synchronization service

## Resource Requirements Analysis

### Container Resource Breakdown

| Component | CPU | RAM | Storage | Notes |
|-----------|-----|-----|---------|-------|
| PostgreSQL | 1-2 vCPU | 2-4 GB | 20-50 GB | Database with persistent data |
| Backend API | 0.5-1 vCPU | 512 MB - 1 GB | Minimal | FastAPI service |
| Frontend (x2) | 0.5 vCPU each | 300-500 MB each | Minimal | Vue.js dev servers |
| App Service | 0.5 vCPU | 256-512 MB | Minimal | Initialization service |
| AWS Sync | 0.5-1 vCPU | 256-512 MB | Minimal | Continuous sync service |
| OS + Docker | 0.5 vCPU | 1-2 GB | 20 GB | System overhead |
| **Total** | **3-5 vCPU** | **5-8 GB** | **50-100 GB** | Recommended minimums |

### Workload Characteristics

- **CPU Usage**: Moderate, variable workload with periodic AWS API calls
- **Memory Usage**: Consistent, primarily driven by PostgreSQL and application services
- **Network**: Moderate bandwidth requirements for API calls and data synchronization
- **Storage**: Primarily for PostgreSQL data and Docker images

## AWS Instance Type Recommendations

### Region: ap-southeast-2 (Sydney)

### Option 1: Development/Testing Environments

#### **t3a.large** (Recommended for Development)
- **vCPUs**: 2 (burstable)
- **RAM**: 8 GB
- **Network**: Up to 5 Gbps
- **Estimated Cost**: ~$0.09/hour (~$65/month)
- **Best For**: Development, testing, and low-to-moderate traffic production environments
- **Pros**: Cost-effective, sufficient resources for typical workloads
- **Cons**: Burstable CPU may throttle under sustained high load

#### **t3.large** (Alternative)
- **vCPUs**: 2 (burstable)
- **RAM**: 8 GB
- **Network**: Up to 5 Gbps
- **Estimated Cost**: ~$0.10/hour (~$73/month)
- **Best For**: Similar to t3a.large, Intel-based alternative
- **Pros**: Slightly better single-threaded performance
- **Cons**: Slightly higher cost than t3a.large

### Option 2: Production Environments

#### **m6a.large** (Recommended for Production)
- **vCPUs**: 2 (dedicated)
- **RAM**: 8 GB
- **Network**: Up to 12.5 Gbps
- **Estimated Cost**: ~$0.11/hour (~$80/month)
- **Best For**: Production environments with consistent workload
- **Pros**: Dedicated vCPUs, better network performance, predictable performance
- **Cons**: Slightly higher cost than burstable instances

#### **m6i.large** (Alternative)
- **vCPUs**: 2 (dedicated)
- **RAM**: 8 GB
- **Network**: Up to 12.5 Gbps
- **Estimated Cost**: ~$0.12/hour (~$88/month)
- **Best For**: Production environments requiring Intel-based processors
- **Pros**: Dedicated vCPUs, excellent performance
- **Cons**: Higher cost than AMD-based alternatives

### Option 3: High-Growth/Heavy Workload Environments

#### **t3.xlarge** (For Growth and Heavy Queries)
- **vCPUs**: 4 (burstable)
- **RAM**: 16 GB
- **Network**: Up to 5 Gbps
- **Estimated Cost**: ~$0.20/hour (~$146/month)
- **Best For**: 
  - Environments expecting significant growth
  - Heavy database query workloads
  - Large-scale VPC synchronization operations
  - High concurrent user access
  - Complex prefix management operations
- **Pros**: Double the resources, room for growth, handles peak loads better
- **Cons**: Higher cost, may be over-provisioned for initial deployment

#### **m6i.xlarge** (For Production with Heavy Loads)
- **vCPUs**: 4 (dedicated)
- **RAM**: 16 GB
- **Network**: Up to 12.5 Gbps
- **Estimated Cost**: ~$0.24/hour (~$175/month)
- **Best For**: Production environments with heavy, consistent workloads
- **Pros**: Dedicated resources, excellent performance, better network
- **Cons**: Higher cost

## Storage Recommendations

### Root Volume
- **Size**: 30-50 GB
- **Type**: GP3 SSD
- **Purpose**: Operating system, Docker images, application code

### Database Volume (Optional)
- **Size**: 50-100 GB (depending on data volume)
- **Type**: GP3 SSD
- **Purpose**: PostgreSQL data directory
- **Note**: Can be attached as additional EBS volume if needed

### Total Storage Estimate
- **Minimum**: 50 GB
- **Recommended**: 100 GB
- **For Growth**: 200+ GB

## Selection Criteria

### Choose **t3a.large** or **t3.large** if:
- Development or testing environment
- Low-to-moderate traffic
- Cost optimization is a priority
- Workload is variable with idle periods

### Choose **m6a.large** or **m6i.large** if:
- Production environment
- Consistent, steady workload
- Predictable performance is required
- Budget allows for dedicated resources

### Choose **t3.xlarge** or **m6i.xlarge** if:
- Expecting significant growth in users or data
- Heavy database query workloads
- Large-scale VPC synchronization (hundreds of VPCs)
- High concurrent access requirements
- Complex prefix management operations
- Need headroom for future expansion

## Cost Comparison (ap-southeast-2)

| Instance Type | vCPU | RAM | Monthly Cost* | Use Case |
|--------------|------|-----|---------------|----------|
| t3a.large | 2 | 8 GB | ~$65 | Development/Testing |
| t3.large | 2 | 8 GB | ~$73 | Development/Testing |
| m6a.large | 2 | 8 GB | ~$80 | Production |
| m6i.large | 2 | 8 GB | ~$88 | Production |
| t3.xlarge | 4 | 16 GB | ~$146 | Growth/Heavy Load |
| m6i.xlarge | 4 | 16 GB | ~$175 | Production Heavy Load |

*Costs are approximate and based on on-demand pricing. Actual costs may vary.

## Monitoring and Optimization

### Key Metrics to Monitor

1. **CPU Utilization**: Watch for sustained high usage (>80%)
2. **Memory Usage**: Ensure sufficient RAM headroom (>20% free)
3. **Database Performance**: Monitor query times and connection pool usage
4. **Network I/O**: Track AWS API call rates and data transfer
5. **Storage I/O**: Monitor database read/write operations

### Scaling Considerations

- **Vertical Scaling**: Upgrade instance type if resources are consistently maxed
- **Horizontal Scaling**: Consider separating database to RDS for larger deployments
- **Storage Scaling**: Add EBS volumes or increase volume size as data grows

## Terraform Configuration Example

```hcl
resource "aws_instance" "ipam4cloud_jumphost" {
    ami           = data.aws_ami.amazon_linux_2023.id
    instance_type = "t3a.large"  # or m6a.large for production
    
    # ... other configuration ...
    
    root_block_device {
        volume_type = "gp3"
        volume_size = 50
        encrypted   = true
    }
}
```

## Conclusion

For most deployments, **t3a.large** or **m6a.large** provides an optimal balance of performance and cost. Choose larger instance types (t3.xlarge or m6i.xlarge) when expecting growth, handling heavy database queries, or managing large-scale VPC synchronization operations.

Always monitor your actual resource usage and adjust instance types accordingly to optimize costs while maintaining performance.

