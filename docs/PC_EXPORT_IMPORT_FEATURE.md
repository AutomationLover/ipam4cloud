# 📁 PC Export & Import System

The **PC Export & Import System** enables data portability by exporting to and importing from user's local PC folders, facilitating data migration and external sharing.

## 🎯 **Purpose**

- **PC Folder Storage**: Export to any folder on user's PC
- **Data Migration**: Move data between systems
- **External Sharing**: Share data via file system
- **Custom Paths**: User selects export/import locations

## 🏗️ **Architecture**

### **Storage Location**
- **User-Defined**: Any folder path on user's PC
- **Flexible Paths**: Windows, macOS, Linux support
- **File Access**: Direct file system access
- **Portability**: Files can be moved, copied, shared

### **Export Contents**
- All VRFs, VPCs, Prefixes, and associations
- Public IP data
- Export metadata and manifest
- PC-specific export information

## 🖥️ **Usage**

### **Web GUI**
Access via: **Data Management → PC Export & Import**

**Export Tab:**
- 📤 **Export to PC**: Specify PC folder path and optional name
- 🏷️ **Custom Naming**: Auto-generated or custom export names
- 📋 **Recent Exports**: Track recent export operations

**Import Tab:**
- 📥 **Import from PC**: Specify PC folder containing export
- 🔍 **Scan Results**: View found exports with validation
- ✅ **Validation**: Check export integrity before import

**Browse Tab:**
- 🔍 **Browse PC Folders**: Scan directories for IPAM exports
- 📂 **Folder Selection**: Select exports for import
- 📊 **Export Summary**: View export contents and metadata

### **CLI Interface**
```bash
# Export to PC folder
./pc_export_import_cli.sh export "/Users/john/ipam-exports" "my_export"
./pc_export_import_cli.sh export "C:\\Users\\john\\ipam-exports"

# Import from PC folder
./pc_export_import_cli.sh import "/Users/john/ipam-exports/my_export"

# Scan PC folder for exports
./pc_export_import_cli.sh scan "/Users/john/ipam-exports"

# Validate PC folder export
./pc_export_import_cli.sh validate "/Users/john/ipam-exports/my_export"
```

### **API Endpoints**
```bash
# Export to PC
POST /api/pc-export?pc_folder=/path/to/folder&export_name=my_export

# Import from PC
POST /api/pc-import?pc_folder=/path/to/folder

# Scan PC folder
GET /api/pc-scan?pc_folder=/path/to/folder

# Validate PC folder
GET /api/pc-validate?pc_folder=/path/to/folder
```

## 📋 **Export Structure**

Each PC export creates:
```
my_export/
├── export_manifest_20250920_143022.json    # Main manifest
├── pc_export_info.json                     # PC-specific metadata
├── vrfs_export_20250920_143022.json        # VRF data
├── manual_prefixes_export_20250920_143022.json  # Prefix data
├── vpc_data_export_20250920_143022.json    # VPC data
└── public_ips_export_20250920_143022.json  # Public IP data
```

### **PC Export Metadata**
```json
{
  "export_name": "my_export",
  "export_path": "/Users/john/ipam-exports/my_export",
  "timestamp": "2025-09-20T14:30:22.123456",
  "export_type": "pc_export",
  "created_by": "user",
  "source_system": "ipam4cloud",
  "pc_folder": "/Users/john/ipam-exports"
}
```

## 🔧 **Path Examples**

### **macOS/Linux**
```bash
# Home directory
/Users/john/Documents/ipam-exports
/home/john/Documents/ipam-exports

# Desktop
/Users/john/Desktop/ipam-backup
/home/john/Desktop/ipam-backup

# External drive
/Volumes/USB-Drive/ipam-exports
/media/john/USB-Drive/ipam-exports
```

### **Windows**
```bash
# Documents (use double backslashes or forward slashes)
C:\\Users\\john\\Documents\\ipam-exports
C:/Users/john/Documents/ipam-exports

# Desktop
C:\\Users\\john\\Desktop\\ipam-backup
C:/Users/john/Desktop/ipam-backup

# External drive
D:\\ipam-exports
D:/ipam-exports
```

## 🔍 **Validation & Scanning**

### **Export Validation**
- ✅ **Required Files**: Checks for all necessary export files
- 📄 **Manifest Integrity**: Validates manifest file structure
- 🔗 **File References**: Ensures all referenced files exist
- ⚠️ **Warnings**: Reports non-critical issues

### **Folder Scanning**
- 🔍 **Recursive Search**: Finds exports in subdirectories
- 📊 **Summary Statistics**: Counts VRFs, VPCs, Prefixes
- ✅ **Validity Check**: Identifies valid vs invalid exports
- 📅 **Timestamp Info**: Shows creation dates

## ⚠️ **Important Notes**

### **Path Requirements**
- **Absolute Paths**: Use full paths for best results
- **Permissions**: Ensure read/write access to folders
- **Existing Folders**: Export folders must exist
- **Cross-Platform**: Handle path separators correctly

### **Import Behavior**
- **Additive**: Adds new data, updates existing
- **Conflict Resolution**: May overwrite existing items
- **Validation**: Checks data integrity before import
- **Error Handling**: Provides detailed error messages

### **File Management**
- **Manual Cleanup**: User manages PC files
- **No Auto-Deletion**: Files persist until manually removed
- **Backup Copies**: Consider keeping backup copies
- **Version Control**: Use descriptive export names

## 🛠️ **Troubleshooting**

### **Common Issues**

**"PC folder does not exist"**
- Ensure the folder exists before export
- Check path spelling and permissions
- Use absolute paths

**"No export manifest found"**
- Verify folder contains IPAM export files
- Check for `export_manifest_*.json` files
- Ensure export completed successfully

**"Invalid export"**
- Run validation to see specific issues
- Check file permissions and integrity
- Re-export if files are corrupted

### **Docker Container Access**
- PC folders must be accessible from Docker containers
- Use mounted volumes for container access
- Consider using `/app/exports` for testing

## 🔧 **Technical Details**

### **Implementation**
- **Backend**: `containers/app/pc_export_import.py`
- **Frontend**: `containers/frontend/src/views/PCExportImport.vue`
- **CLI**: `pc_export_import_cli.sh`
- **API**: `containers/backend/main.py` (PC export endpoints)

### **Dependencies**
- Uses existing `DataExporter` and `DataImporter` classes
- Requires file system access permissions
- Integrates with Docker Compose services

## 🆚 **vs Backup/Restore**

| Feature | PC Export/Import | Backup/Restore |
|---------|------------------|----------------|
| **Storage** | User's PC folders | Docker internal |
| **Purpose** | Data migration | System snapshots |
| **Access** | File system + GUI | GUI only |
| **Portability** | High (files can be moved) | Low (Docker internal) |
| **Use Case** | External sharing | Quick recovery |
| **Management** | Manual | Automatic cleanup |

Use **PC Export/Import** for data portability and **Backup/Restore** for system management.
