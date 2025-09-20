# 🔄 Backup & Restore System

The **Backup & Restore System** provides internal system snapshots with timeline functionality for quick recovery and system state management.

## 🎯 **Purpose**

- **Internal Docker Storage**: Backups stored inside Docker containers/volumes
- **Timeline Management**: Create timestamped restore points
- **Quick Recovery**: One-click restore to previous states
- **System Snapshots**: Full database backups with metadata

## 🏗️ **Architecture**

### **Storage Location**
- **Path**: `/app/backups/` inside Docker containers
- **Structure**: Each backup gets its own timestamped directory
- **Persistence**: Stored in Docker volumes (survives container restarts)

### **Backup Contents**
- All VRFs, VPCs, Prefixes, and associations
- Public IP data
- System metadata and timestamps
- Backup validation information

## 🖥️ **Usage**

### **Web GUI**
Access via: **Data Management → Backup & Restore**

**Features:**
- 📦 **Create Backup**: Add description and create instant backup
- 📅 **Timeline View**: Visual timeline of all backups
- 📊 **Statistics**: Total backups, size, latest backup info
- 🔍 **Backup Details**: View files, metadata, and validation status
- ⚡ **One-Click Restore**: Restore to any backup point
- 🗑️ **Cleanup**: Delete old backups, keep recent ones

### **CLI Interface**
```bash
# Create backup
./backup_restore_cli.sh backup "Before major update"

# List all backups
./backup_restore_cli.sh list

# Restore from backup
./backup_restore_cli.sh restore 20250920_143022

# View backup details
./backup_restore_cli.sh details 20250920_143022

# Delete backup
./backup_restore_cli.sh delete 20250920_143022

# Cleanup old backups (keep 5 recent)
./backup_restore_cli.sh cleanup 5
```

### **API Endpoints**
```bash
# Create backup
POST /api/backup?description=My backup

# List backups
GET /api/backups

# Restore backup
POST /api/restore/{backup_id}

# Get backup details
GET /api/backup/{backup_id}

# Delete backup
DELETE /api/backup/{backup_id}
```

## 📋 **Backup Metadata**

Each backup includes:
```json
{
  "backup_id": "20250920_143022",
  "timestamp": "2025-09-20T14:30:22.123456",
  "description": "Before major update",
  "created_by": "system",
  "backup_type": "full",
  "status": "completed",
  "restore_tested": false,
  "files": {
    "vrfs": "vrfs_export_20250920_143022.json",
    "prefixes": "manual_prefixes_export_20250920_143022.json",
    "vpcs": "vpc_data_export_20250920_143022.json",
    "public_ips": "public_ips_export_20250920_143022.json"
  }
}
```

## ⚠️ **Important Notes**

### **Restore Behavior**
- **Replaces ALL current data** with backup data
- **Cannot be undone** - create a backup first if needed
- **Validates backup** before restore
- **Updates metadata** to mark backup as restore-tested

### **Storage Management**
- Backups accumulate over time
- Use **cleanup** feature to manage disk space
- Default retention: 10 recent backups
- Monitor backup sizes in the GUI

### **Best Practices**
1. **Create backups before major changes**
2. **Add descriptive names** for easy identification
3. **Test restores periodically** to ensure backup integrity
4. **Clean up old backups** to manage storage
5. **Monitor backup timeline** for system health

## 🔧 **Technical Details**

### **Implementation**
- **Backend**: `containers/app/backup_restore.py`
- **Frontend**: `containers/frontend/src/views/BackupRestore.vue`
- **CLI**: `backup_restore_cli.sh`
- **API**: `containers/backend/main.py` (backup endpoints)

### **Dependencies**
- Uses existing `DataExporter` and `DataImporter` classes
- Requires PostgreSQL database connection
- Integrates with Docker Compose services

### **Error Handling**
- Validates backup integrity before restore
- Provides detailed error messages
- Graceful cleanup on failed operations
- Comprehensive logging for troubleshooting

## 🆚 **vs PC Export/Import**

| Feature | Backup/Restore | PC Export/Import |
|---------|----------------|------------------|
| **Storage** | Docker internal | User's PC folders |
| **Purpose** | System snapshots | Data migration |
| **Access** | GUI + CLI | GUI + CLI + File system |
| **Speed** | Very fast | Depends on PC access |
| **Use Case** | Quick recovery | External sharing |
| **Retention** | Automatic cleanup | Manual management |

Use **Backup/Restore** for system management and **PC Export/Import** for data portability.
