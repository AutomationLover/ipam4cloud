# Prefix Management System - Containerized Demo

This directory contains a complete containerized implementation of the hierarchical prefix management system for cloud environments.

## Architecture

- **PostgreSQL Database**: Stores VRFs, VPCs, prefixes, and associations
- **Python Application**: SQLAlchemy models and demo implementation
- **Docker Compose**: Orchestrates the multi-container setup

## Quick Start

### Using the Management Script (Recommended)

1. **Start with fresh database:**
   ```bash
   cd containers/
   ./manage.sh start --clean
   ```

2. **Or start with existing data:**
   ```bash
   ./manage.sh start
   ```

3. **Other useful commands:**
   ```bash
   ./manage.sh status          # Check container status
   ./manage.sh logs backend    # View backend logs
   ./manage.sh restart --clean # Restart with fresh DB
   ./manage.sh reset           # Complete fresh start
   ./manage.sh --help          # Show all options
   ```

### Using Docker Compose Directly

1. **Start the system:**
   ```bash
   docker-compose up --build
   ```

2. **For fresh database:**
   ```bash
   docker-compose down -v  # Clean database
   docker-compose up --build
   ```

### What Happens on Startup

The demo will automatically:
   - Run the complete user story scenarios
   - Display tree views and query results
   - Show space analysis

3. **View logs:**
   ```bash
   docker-compose logs -f app
   ```

4. **Stop the system:**
   ```bash
   docker-compose down
   ```

## Demo Scenarios

### 1. Manual Prefix Planning
- Engineer creates root prefix `10.0.0.0/8` in `prod-vrf`
- Creates production environment reservation `10.0.0.0/12`
- Creates AWS VPCs for production and development
- Reserves `10.0.0.0/16` as routable for prod VPC
- Reserves `10.1.0.0/16` as non-routable for dev VPC
- Associates VPCs with their respective prefixes

### 2. Auto Script Ingestion
- Simulates hourly cron job discovering VPC subnets
- Ingests routable subnets (`10.0.1.0/24`, `10.0.2.0/24`, `10.0.10.0/24`)
- Ingests non-routable subnets (`10.1.1.0/24`, `10.1.2.0/24`)
- Demonstrates proper VRF inheritance and routable flag propagation

### 3. Client Query Operations
- Tree view with hierarchical display
- Query specific prefixes by CIDR
- List children of parent prefixes
- Filter by routable flag, source, and cloud provider
- Space analysis within parent prefixes

## Database Schema Features

### Tables
- `vrf`: Virtual Routing and Forwarding instances
- `vpc`: Cloud VPC definitions
- `prefix`: Hierarchical IP prefix entries
- `vpc_prefix_association`: Engineer-managed VPC-to-prefix mappings

### Key Features
- **Hierarchical Structure**: Parent-child relationships with automatic indentation
- **Data Integrity**: Triggers ensure parent contains child, routable inheritance
- **Auto VRF Creation**: Non-routable VPC prefixes get dedicated VRFs
- **Flexible Tagging**: JSONB tags for metadata
- **Ingestion Function**: `upsert_vpc_subnet()` for idempotent subnet discovery

### Constraints
- Parent prefixes must contain child prefixes
- Non-routable parents cannot have routable children
- Unique CIDR per VRF
- VPC-sourced prefixes must reference a VPC

## File Structure

```
containers/
├── docker-compose.yml          # Container orchestration
├── Dockerfile                  # Python app container
├── requirements.txt            # Python dependencies
├── init/
│   ├── 01_schema.sql          # Database schema and functions
│   └── 02_seed_data.sql       # Initial data (default VRF)
└── app/
    ├── models.py              # SQLAlchemy models and managers
    ├── main.py                # Demo implementation
    └── README.md              # This file
```

## Example Output

```
🚀 Starting Prefix Management System Demo
============================================================
✓ Database connection established

============================================================
DEMO: Manual Prefix Planning
============================================================

1. Creating root prefix 10.0.0.0/8 for prod-vrf...
   ✓ Created: manual-prod-vrf-10-0-0-0-8

2. Creating 10.0.0.0/12 reservation for prod environment...
   ✓ Created: manual-prod-vrf-10-0-0-0-12

[... continues with full demo ...]

🌳 Final Prefix Tree:

=== Prefix Tree for VRF: prod-vrf ===

VRF: prod-vrf
--------------------------------------------------
[M] 10.0.0.0/8 (✓) - manual-prod-vrf-10-0-0-0-8
    Tags: env:prod, managed_by:engineer
  [M] 10.0.0.0/12 (✓) - manual-prod-vrf-10-0-0-0-12
      Tags: env:prod, purpose:prod_reservation
    [M] 10.0.0.0/16 (✓) - manual-prod-vrf-10-0-0-0-16
        Tags: vpc_id:..., purpose:vpc_reservation
      [V] 10.0.1.0/24 (✓) - ...-subnet-10-0-1-0-24
          Tags: Name:prod-app-subnet-1a, AZ:us-east-1a
    [M] 10.1.0.0/16 (✗) - manual-prod-vrf-10-1-0-0-16
        Tags: vpc_id:..., purpose:vpc_reservation
```

## Development

### Connect to Database
```bash
docker-compose exec postgres psql -U prefix_user -d prefix_management
```

### Run Custom Queries
```sql
-- View all prefixes in tree order
SELECT * FROM prefix_tree WHERE vrf_id = 'prod-vrf';

-- Check VRF assignments
SELECT vrf_id, COUNT(*) as prefix_count FROM prefix GROUP BY vrf_id;
```

### Modify Demo
Edit `app/main.py` to add custom scenarios or modify the existing user stories.

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL container is healthy: `docker-compose ps`
- Check logs: `docker-compose logs postgres`

### Schema Issues
- Recreate containers: `docker-compose down -v && docker-compose up --build`

### Application Errors
- Check app logs: `docker-compose logs app`
- Verify database schema: Connect to PostgreSQL and check tables
