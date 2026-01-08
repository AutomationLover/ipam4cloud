# IPAM4Cloud - Hierarchical IP Address Management System

A complete containerized IP Address Management (IPAM) system for cloud environments with web interface, AWS integration, and hierarchical prefix management.

## 🎯 Features

- **🌐 Web Interface**: Vue.js frontend with tree/list views, filtering, and search
- **☁️ AWS Integration**: Automatic VPC subnet discovery and synchronization
- **🏗️ Hierarchical Structure**: Parent-child prefix relationships with inheritance
- **🔄 Multi-VRF Support**: Virtual Routing and Forwarding isolation
- **📊 Space Analysis**: Available space tracking and utilization reports
- **🏷️ Flexible Tagging**: JSONB metadata for prefixes and VPCs
- **🔒 Data Integrity**: Automatic validation and constraint enforcement
- **🎯 AWS IPAM-Style Subnet Allocation**: Automatically allocate first available subnets by size with tag matching

## 🚀 Quick Start

### Step 1: Environment Setup

**Interactive Setup (Recommended)**
```bash
./setup_env.sh
```

**Manual Setup**
```bash
# Copy environment template
cp env.example .env

# Edit with your AWS settings
nano .env
```

### Step 2: Generate Configuration

```bash
# Generate configuration files from environment variables
./generate_config_advanced.sh
```

### Step 3: Start the Application

```bash
# Start with fresh database
./manage.sh start --clean

# Or start with existing data
./manage.sh start
```

### Step 4: Access the Application

- **Admin Interface**: http://localhost:8080
- **Read-only Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs

## 📋 Prerequisites

- Docker and Docker Compose
- AWS CLI configured (for AWS integration)
- Valid AWS account with VPC permissions (optional)

## 🔧 Configuration

### Required Environment Variables

```bash
# AWS Configuration
AWS_DEFAULT_REGION=us-east-2
AWS_ACCOUNT_ID=012345678901

# Test VPC Configuration (if using AWS sync)
TEST_VPC_1_ID=vpc-0123456789abcdef0
TEST_VPC_1_CIDR=10.101.0.0/16
TEST_VPC_2_ID=vpc-0123456789abcdef1
TEST_VPC_2_CIDR=10.102.0.0/16

# Optional: AWS Credentials (can use AWS CLI profiles instead)
# AWS_ACCESS_KEY_ID=your_access_key
# AWS_SECRET_ACCESS_KEY=your_secret_key
```

### AWS VPC Setup (Optional)

If you want to test AWS integration, create test VPCs:

```bash
# Set your region
export AWS_DEFAULT_REGION=us-east-2

# Create test VPCs
aws ec2 create-vpc --cidr-block 10.101.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ipam4cloud-test-vpc-1}]'
aws ec2 create-vpc --cidr-block 10.102.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ipam4cloud-test-vpc-2}]'

# Update your .env file with the returned VPC IDs
```


## 🏗️ Architecture

### Components

- **PostgreSQL Database**: Stores VRFs, VPCs, prefixes, and associations
- **FastAPI Backend**: REST API with SQLAlchemy models
- **Vue.js Frontend**: Responsive web interface with admin and read-only views
- **AWS Sync Service**: Automatic VPC subnet discovery and synchronization
- **Docker Compose**: Container orchestration

### Database Schema

- **`vrf`**: Virtual Routing and Forwarding instances
- **`vpc`**: Cloud VPC definitions (AWS, Azure, GCP)
- **`prefix`**: Hierarchical IP prefix entries with parent-child relationships
- **`vpc_prefix_association`**: Engineer-managed VPC-to-prefix mappings

### Key Features

- **Hierarchical Structure**: Parent-child relationships with automatic indentation
- **Data Integrity**: Database triggers ensure parent contains child, routable inheritance
- **Auto VRF Creation**: Non-routable VPC prefixes get dedicated VRFs
- **Flexible Tagging**: JSONB tags for metadata
- **AWS Integration**: Automatic subnet discovery with `upsert_vpc_subnet()` function

## 🌐 Web Interface

### Prefix Management
- **Tree View**: Hierarchical display with expand/collapse
- **List View**: Sortable table with filtering and search
- **Manual Creation**: Create prefixes with specific CIDR blocks
- **Auto Allocation**: AWS IPAM-style subnet allocation by size and tags
- **Actions**: Create child prefixes, associate with VPCs
- **Filtering**: By VRF, source, routable status, cloud provider

### VRF Management
- **List all VRFs** with descriptions and prefix counts
- **Navigate to filtered prefix views**
- **Default VRF identification**

### VPC Management
- **Multi-cloud support** (AWS, Azure, GCP)
- **VPC details** with associated prefixes
- **Provider-specific information**

## 🎯 Automatic Subnet Allocation

### AWS IPAM-Style Pool Allocation

The system now supports automatic subnet allocation similar to AWS IPAM pools, where users can request subnets by size without specifying the exact network address.

#### How It Works

1. **Parent Selection**: Find parent prefixes by VRF and optional tag matching
2. **Space Calculation**: Calculate all possible subnets of requested size within parent
3. **Conflict Detection**: Check against existing child prefixes for overlaps
4. **First Available**: Allocate the numerically first available subnet

#### Web Interface

- **Guided Creation**: Tabbed interface with "Manual CIDR" and "Auto Allocate Subnet" options
- **Interactive Preview**: Real-time preview showing next available subnet and remaining capacity
- **Tag Matching**: Strict tag matching to find appropriate parent prefixes
- **Size Selection**: Dropdown with common subnet sizes (/16, /20, /24, /25, /26, /27, /28, /29, /30)

#### API Usage

```bash
# Allocate a /24 subnet with tag matching
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "prod-vrf",
    "subnet_size": 24,
    "tags": {"purpose": "vpc_reservation", "env": "prod"},
    "routable": true,
    "description": "Auto-allocated production subnet"
  }'

# Preview available subnets in a parent prefix
curl "http://localhost:8000/api/prefixes/manual-prod-vrf-10-1-0-0-16/available-subnets?subnet_size=24"
```

#### Features

- **Tag-Based Parent Selection**: Strict matching of parent prefix tags
- **Automatic Space Management**: Finds first available subnet without overlaps
- **Routable Inheritance**: Respects parent prefix routable constraints
- **Allocation Tracking**: Adds metadata tags showing allocation source and timestamp
- **Real-time Preview**: Shows next available subnet and remaining capacity

## ☁️ AWS Integration

### Automatic Sync Service

The AWS sync service automatically discovers and synchronizes VPC subnets:

```bash
# Monitor sync logs
docker compose -f containers/docker-compose.yml logs -f aws-sync
```

### Sync Configuration

```bash
# Sync settings in .env
SYNC_MODE=continuous          # or 'once' for single run
SYNC_INTERVAL=300            # seconds between syncs
AWS_PAGE_SIZE=100            # AWS API pagination size
MAX_SUBNETS_PER_VPC=1000     # safety limit
```

### What Gets Synced

- **VPC Subnets**: Automatically discovered and added as child prefixes
- **Routable Status**: Inherited from parent VPC prefix
- **Tags**: AWS subnet tags are preserved
- **Hierarchy**: Subnets are properly nested under VPC prefixes

## 🛠️ Management Commands

### Using the Management Script

```bash
# Start services
./manage.sh start              # Start with existing data
./manage.sh start --clean      # Start with fresh database

# Service management
./manage.sh status             # Check container status
./manage.sh restart            # Restart all services
./manage.sh restart --clean    # Restart with fresh database
./manage.sh stop               # Stop all services

# Logs and monitoring
./manage.sh logs backend       # View backend logs
./manage.sh logs aws-sync      # View AWS sync logs
./manage.sh logs --follow      # Follow all logs

# Database operations
./manage.sh reset              # Complete fresh start
./manage.sh db-shell           # Connect to database

# Help
./manage.sh --help             # Show all options
```

### Using Docker Compose Directly

```bash
# Start all services
docker compose -f containers/docker-compose.yml up -d

# View logs
docker compose -f containers/docker-compose.yml logs -f

# Stop services
docker compose -f containers/docker-compose.yml down

# Fresh start (removes database)
docker compose -f containers/docker-compose.yml down -v
docker compose -f containers/docker-compose.yml up --build
```

## 📊 Demo Scenarios

The system includes comprehensive demo scenarios:

### 1. Manual Prefix Planning
- Engineer creates root prefix `10.0.0.0/8` in `prod-vrf`
- Creates production environment reservation `10.0.0.0/12`
- Creates AWS VPCs for production and development
- Associates VPCs with their respective prefixes

### 2. AWS Subnet Discovery
- Automatic hourly sync discovers VPC subnets
- Ingests routable and non-routable subnets
- Demonstrates proper VRF inheritance and routable flag propagation

### 3. Web Interface Operations
- Tree view with hierarchical display
- Query specific prefixes by CIDR
- Filter by routable flag, source, and cloud provider
- Space analysis within parent prefixes

## 🔍 Troubleshooting

### Common Issues

**Database Connection Issues**
```bash
# Check container status
docker compose -f containers/docker-compose.yml ps

# View database logs
docker compose -f containers/docker-compose.yml logs postgres

# Connect to database manually
docker compose -f containers/docker-compose.yml exec postgres psql -U prefix_user -d prefix_management
```

**AWS Sync Issues**
```bash
# Check AWS credentials
aws sts get-caller-identity

# View sync logs
docker compose -f containers/docker-compose.yml logs aws-sync
```

**Configuration Issues**
```bash
# Regenerate configuration files
./generate_config_advanced.sh

# Validate generated JSON
python3 -m json.tool app/data/vpc_data.gen.json
```

**Port Conflicts**
```bash
# Clean up Docker resources
docker compose -f containers/docker-compose.yml down -v
docker system prune -f
```

### Fresh Start

If you encounter persistent issues:

```bash
# Complete reset
./manage.sh reset

# Or manually
docker compose -f containers/docker-compose.yml down -v
docker system prune -f
./generate_config_advanced.sh
docker compose -f containers/docker-compose.yml up --build
```

## 📊 Data Management

The system provides two distinct data management features:

### 🔄 Backup & Restore System
**Internal Docker storage with timeline functionality**

- **Purpose**: Quick system snapshots and recovery
- **Storage**: Inside Docker containers (`/app/backups/`)
- **Features**: Timeline view, one-click restore, automatic cleanup
- **Access**: Web GUI, CLI, API

```bash
# Create backup
./backup_restore_cli.sh backup "Before major update"

# List backups
./backup_restore_cli.sh list

# Restore from backup
./backup_restore_cli.sh restore 20250920_143022

# View backup details
./backup_restore_cli.sh details 20250920_143022

# Cleanup old backups (keep 5 recent)
./backup_restore_cli.sh cleanup 5
```

**Web Interface**: http://localhost:8080/backup-restore

### 📁 PC Export & Import System
**Export to your PC folders and import from external sources**

- **Purpose**: Data migration and external sharing
- **Storage**: User's PC folders (any path)
- **Features**: Custom paths, folder scanning, validation
- **Access**: Web GUI, CLI, API

```bash
# Export to PC
./pc_export_import_cli.sh export "/Users/john/ipam-exports" "my_export"

# Import from PC
./pc_export_import_cli.sh import "/Users/john/ipam-exports/my_export"

# Scan PC folder for exports
./pc_export_import_cli.sh scan "/Users/john/ipam-exports"

# Validate PC folder
./pc_export_import_cli.sh validate "/Users/john/ipam-exports/my_export"
```

**Web Interface**: http://localhost:8080/pc-export-import


## 🔒 Security

- **Environment Variables**: All AWS-specific values are externalized
- **Git Ignored**: Generated configuration files are not tracked
- **IAM Permissions**: Use minimal required AWS permissions
- **Network Isolation**: Services communicate through Docker networks

## 📁 File Structure

```
ipam4cloud/
├── README.md                    # This file
├── manage.sh                    # Management script
├── setup_env.sh                 # Interactive environment setup
├── generate_config_advanced.sh  # Configuration generator
├── requirements.txt             # Python dependencies
├── .env                         # Your environment configuration (git-ignored)
├── env.example                  # Environment template
├── docs/                        # Documentation
│   ├── ENV_SETUP.md             # Detailed environment setup
│   ├── WEB_APP_README.md        # Web interface guide
│   ├── AWS_SYNC_README.md       # AWS sync documentation
│   └── DEMO_RESULTS.md          # Demo output examples
├── containers/                  # Container orchestration
│   ├── docker-compose.yml       # Container orchestration
│   ├── app/                     # Python application
│   │   ├── main.py              # Demo implementation
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── aws_vpc_sync.py      # AWS synchronization service
│   │   └── data/                # Configuration data
│   │       ├── *.template.json  # Configuration templates
│   │       └── *.gen.json       # Generated files (git-ignored)
│   ├── backend/                 # FastAPI backend
│   │   └── main.py              # REST API server
│   ├── frontend/                # Vue.js admin interface
│   ├── frontend-readonly/       # Vue.js read-only interface
│   └── init/                    # Database initialization
│       ├── 01_schema.sql        # Database schema
│       └── 02_seed_data.sql     # Initial data
└── .aws-local/                  # User AWS files (git-ignored)
    ├── vpc_details.json         # Your VPC details
    └── commands.sh              # Your AWS CLI commands
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

See [LICENSE](LICENSE) file for details.

---

## 📚 Additional Documentation

For more detailed information, see the `docs/` directory:

- **[Environment Setup Guide](docs/ENV_SETUP.md)** - Detailed environment configuration
- **[Web Interface Guide](docs/WEB_APP_README.md)** - Complete web interface documentation
- **[AWS Sync Guide](docs/AWS_SYNC_README.md)** - AWS integration and sync service details
- **[Backup & Restore Guide](docs/BACKUP_RESTORE_FEATURE.md)** - Internal backup system documentation
- **[PC Export/Import Guide](docs/PC_EXPORT_IMPORT_FEATURE.md)** - PC folder export/import system
- **[Demo Results](docs/DEMO_RESULTS.md)** - Example output and demo scenarios

**Need help?** Check the troubleshooting section above or open an issue on GitHub.
