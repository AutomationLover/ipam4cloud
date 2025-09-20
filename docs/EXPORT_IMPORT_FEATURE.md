# Export/Import Feature Documentation

## 🎯 Overview

The IPAM4Cloud system now includes comprehensive export/import functionality that allows you to:

- **Export** all system data (VRFs, VPCs, Prefixes, Associations) to JSON files
- **Import** data from exported JSON files to restore or migrate systems
- **Backup** your IPAM configuration for disaster recovery
- **Migrate** between environments (dev, staging, production)
- **Share** configurations between teams or deployments

## 📊 Data Types Supported

| Data Type | Description | Export File |
|-----------|-------------|-------------|
| **VRFs** | Virtual Routing and Forwarding tables | `vrfs_export_TIMESTAMP.json` |
| **Manual Prefixes** | User-defined IP ranges and hierarchies | `manual_prefixes_export_TIMESTAMP.json` |
| **VPC Data** | VPCs, associations, and subnets | `vpc_data_export_TIMESTAMP.json` |
| **Public IPs** | Public IP address assignments | `public_ips_export_TIMESTAMP.json` |
| **Manifest** | Export metadata and import instructions | `export_manifest_TIMESTAMP.json` |

## 🚀 Usage Methods

### 1. Command Line Interface (Recommended)

```bash
# Export all data
./export_import_data.sh export

# Export to custom directory
./export_import_data.sh export --output-dir /backup/ipam

# Import from export
./export_import_data.sh import --manifest exports/export_manifest_20241220_143022.json

# Get help
./export_import_data.sh --help
```

### 2. Direct Python Script

```bash
# Export
docker compose -f containers/docker-compose.yml --env-file .env exec app \
  python data_export_import.py export --output-dir exports

# Import
docker compose -f containers/docker-compose.yml --env-file .env exec app \
  python data_export_import.py import --manifest exports/export_manifest_20241220_143022.json
```

### 3. REST API Endpoints

```bash
# Export data
curl -X POST "http://localhost:8000/api/export?output_dir=exports"

# List available exports
curl "http://localhost:8000/api/exports?export_dir=exports"

# Import data
curl -X POST "http://localhost:8000/api/import" \
  -H "Content-Type: application/json" \
  -d '{"manifest_file": "exports/export_manifest_20241220_143022.json"}'
```

## 📁 Export File Structure

### Export Directory Layout
```
exports/
├── vrfs_export_20241220_143022.json           # VRF definitions
├── manual_prefixes_export_20241220_143022.json # Manual prefix hierarchies
├── vpc_data_export_20241220_143022.json        # VPC configurations
├── public_ips_export_20241220_143022.json      # Public IP assignments
└── export_manifest_20241220_143022.json        # Import manifest (use this!)
```

### Manifest File Example
```json
{
  "export_info": {
    "timestamp": "20241220_143022",
    "export_type": "complete_system_export",
    "version": "1.0"
  },
  "summary": {
    "total_vrfs": 2,
    "total_vpcs": 4,
    "total_prefixes": 15,
    "manual_prefixes": 8,
    "vpc_prefixes": 7,
    "vpc_associations": 4
  },
  "exported_files": {
    "vrfs": "exports/vrfs_export_20241220_143022.json",
    "manual_prefixes": "exports/manual_prefixes_export_20241220_143022.json",
    "vpc_data": "exports/vpc_data_export_20241220_143022.json",
    "public_ips": "exports/public_ips_export_20241220_143022.json"
  }
}
```

## 🔄 Import Process

### Import Order (Automatic)
1. **VRFs** - Virtual routing tables (if needed)
2. **Manual Prefixes** - User-defined IP hierarchies
3. **VPC Data** - Cloud provider VPCs and associations
4. **Public IPs** - Public IP address assignments

### Import Behavior
- **Existing Data**: Items with same IDs are skipped (no overwrite)
- **Dependencies**: Parent-child relationships are preserved
- **Validation**: All data is validated before import
- **Rollback**: Failed imports don't partially modify the database

## 🛡️ Data Compatibility

### JSON Format Compatibility
The export/import system uses the **same JSON format** as the existing configuration files:

- `manual_prefixes_export.json` ↔ `manual_prefixes.template.json`
- `vpc_data_export.json` ↔ `vpc_data.template.json`
- `public_ips_export.json` ↔ `public_ips.template.json`

This means you can:
- Export from a live system and use as configuration templates
- Import configuration templates into a live system
- Mix and match exported data with manual configurations

### Environment Variables
Exported files contain **actual values**, not environment variable placeholders:
- Export: `"provider_account_id": "267406360448"`
- Template: `"provider_account_id": "${AWS_ACCOUNT_ID}"`

## 🧪 Testing

Run the test suite to verify functionality:

```bash
./test_export_import.sh
```

The test will:
- ✅ Export current system data
- ✅ Validate JSON file structure
- ✅ Test API endpoints
- ✅ Verify data integrity
- ✅ Clean up test files

## 📋 Use Cases

### 1. Backup and Disaster Recovery
```bash
# Daily backup
./export_import_data.sh export --output-dir /backup/ipam/$(date +%Y%m%d)

# Restore from backup
./export_import_data.sh import --manifest /backup/ipam/20241220/export_manifest_20241220_143022.json
```

### 2. Environment Migration
```bash
# Export from production
./export_import_data.sh export --output-dir prod_export

# Import to staging (after copying files)
./export_import_data.sh import --manifest staging_import/export_manifest_20241220_143022.json
```

### 3. Configuration Sharing
```bash
# Export specific configuration
./export_import_data.sh export --output-dir team_config

# Share the export_manifest_*.json file with team members
# They can import using the same manifest
```

### 4. Development Setup
```bash
# Export from a configured system
./export_import_data.sh export --output-dir dev_seed

# New developers can import to get started quickly
./export_import_data.sh import --manifest dev_seed/export_manifest_20241220_143022.json
```

## ⚠️ Important Notes

### Security Considerations
- **Exported files contain real data** (IP addresses, VPC IDs, account IDs)
- **Store exports securely** - they may contain sensitive network information
- **Review exports** before sharing to ensure no sensitive data is exposed

### Git Ignore
Export files are automatically git-ignored:
```gitignore
# Export/Import files
exports/
*.export.json
*_export_*.json
```

### Performance
- **Large datasets**: Export/import handles pagination for large VPCs and prefix hierarchies
- **Batch processing**: Database operations are batched for efficiency
- **Memory usage**: Files are processed incrementally to handle large exports

## 🔧 Troubleshooting

### Common Issues

**Export fails with "Database connection failed"**
```bash
# Check if containers are running
./manage.sh status

# Start containers if needed
./manage.sh start
```

**Import fails with "Manifest file not found"**
```bash
# Use absolute path or ensure file exists
ls -la exports/export_manifest_*.json

# Use the correct manifest file path
./export_import_data.sh import --manifest exports/export_manifest_20241220_143022.json
```

**API endpoints return 500 errors**
```bash
# Check backend logs
./manage.sh logs backend

# Restart backend if needed
./manage.sh restart
```

### Debug Mode
Enable detailed logging by setting environment variables:
```bash
export LOG_LEVEL=DEBUG
./export_import_data.sh export
```

## 🎉 Summary

The export/import feature provides:

- ✅ **Complete data portability** - Export everything or specific data types
- ✅ **Multiple interfaces** - CLI, Python API, REST API
- ✅ **Format compatibility** - Works with existing JSON configurations
- ✅ **Safe operations** - Validation and rollback protection
- ✅ **Production ready** - Handles large datasets with pagination
- ✅ **Well tested** - Comprehensive test suite included

This feature makes IPAM4Cloud suitable for enterprise deployments requiring backup, migration, and configuration management capabilities! 🚀
