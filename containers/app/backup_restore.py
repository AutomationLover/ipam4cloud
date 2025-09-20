#!/usr/bin/env python3
"""
Internal Backup/Restore System for IPAM4Cloud
Manages internal backups with timeline restore functionality
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from models import DatabaseManager
from data_export_import import DataExporter, DataImporter


class BackupManager:
    """Manages internal system backups with timeline functionality"""
    
    def __init__(self, db_manager: DatabaseManager, backup_dir: str = "backups"):
        self.db_manager = db_manager
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize exporter/importer for actual data operations
        self.exporter = DataExporter(db_manager)
        self.importer = DataImporter(db_manager)
    
    def create_backup(self, description: str = None) -> Dict[str, Any]:
        """Create a new backup with timestamp and description"""
        timestamp = datetime.now()
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S")
        
        # Create backup directory
        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(exist_ok=True)
        
        try:
            # Export all data to backup directory
            exported_files = self.exporter.export_all_data(str(backup_path))
            
            # Create backup metadata
            backup_info = {
                "backup_id": backup_id,
                "timestamp": timestamp.isoformat(),
                "description": description or f"Backup created on {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "created_by": "system",
                "backup_type": "full",
                "status": "completed",
                "files": exported_files,
                "restore_tested": False
            }
            
            # Save backup metadata
            metadata_file = backup_path / "backup_info.json"
            with open(metadata_file, 'w') as f:
                json.dump(backup_info, f, indent=2, default=str)
            
            return {
                "status": "success",
                "backup_id": backup_id,
                "backup_path": str(backup_path),
                "backup_info": backup_info
            }
            
        except Exception as e:
            # Cleanup failed backup
            if backup_path.exists():
                shutil.rmtree(backup_path)
            
            return {
                "status": "error",
                "error": str(e),
                "backup_id": backup_id
            }
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups with metadata"""
        backups = []
        
        if not self.backup_dir.exists():
            return backups
        
        for backup_path in self.backup_dir.iterdir():
            if backup_path.is_dir():
                metadata_file = backup_path / "backup_info.json"
                
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            backup_info = json.load(f)
                        
                        # Add computed fields
                        backup_info["backup_path"] = str(backup_path)
                        backup_info["size"] = self._calculate_backup_size(backup_path)
                        backup_info["age_days"] = self._calculate_age_days(backup_info["timestamp"])
                        
                        backups.append(backup_info)
                        
                    except Exception as e:
                        # Skip corrupted backup metadata
                        continue
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups
    
    def restore_backup(self, backup_id: str) -> Dict[str, Any]:
        """Restore system from a specific backup"""
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            return {
                "status": "error",
                "error": f"Backup {backup_id} not found"
            }
        
        metadata_file = backup_path / "backup_info.json"
        if not metadata_file.exists():
            return {
                "status": "error",
                "error": f"Backup {backup_id} metadata not found"
            }
        
        try:
            # Load backup metadata
            with open(metadata_file, 'r') as f:
                backup_info = json.load(f)
            
            # Find the manifest file
            manifest_file = None
            for file_path in backup_path.glob("export_manifest_*.json"):
                manifest_file = str(file_path)
                break
            
            if not manifest_file:
                return {
                    "status": "error",
                    "error": f"Backup {backup_id} manifest not found"
                }
            
            # Perform restore using importer
            restore_results = self.importer.import_from_manifest(manifest_file)
            
            if restore_results["summary"]["status"] == "success":
                # Update backup metadata to mark as restore-tested
                backup_info["restore_tested"] = True
                backup_info["last_restore"] = datetime.now().isoformat()
                
                with open(metadata_file, 'w') as f:
                    json.dump(backup_info, f, indent=2, default=str)
                
                return {
                    "status": "success",
                    "backup_id": backup_id,
                    "restore_results": restore_results,
                    "message": f"Successfully restored from backup {backup_id}"
                }
            else:
                return {
                    "status": "error",
                    "error": f"Restore failed: {restore_results['summary'].get('error')}",
                    "restore_results": restore_results
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"Restore failed: {str(e)}",
                "backup_id": backup_id
            }
    
    def delete_backup(self, backup_id: str) -> Dict[str, Any]:
        """Delete a specific backup"""
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            return {
                "status": "error",
                "error": f"Backup {backup_id} not found"
            }
        
        try:
            shutil.rmtree(backup_path)
            return {
                "status": "success",
                "message": f"Backup {backup_id} deleted successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to delete backup {backup_id}: {str(e)}"
            }
    
    def get_backup_details(self, backup_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific backup"""
        backup_path = self.backup_dir / backup_id
        
        if not backup_path.exists():
            return {
                "status": "error",
                "error": f"Backup {backup_id} not found"
            }
        
        metadata_file = backup_path / "backup_info.json"
        if not metadata_file.exists():
            return {
                "status": "error",
                "error": f"Backup {backup_id} metadata not found"
            }
        
        try:
            with open(metadata_file, 'r') as f:
                backup_info = json.load(f)
            
            # Add file details
            files_info = []
            for file_path in backup_path.glob("*.json"):
                if file_path.name != "backup_info.json":
                    file_stat = file_path.stat()
                    files_info.append({
                        "name": file_path.name,
                        "size": file_stat.st_size,
                        "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                    })
            
            backup_info["files_info"] = files_info
            backup_info["total_size"] = self._calculate_backup_size(backup_path)
            
            return {
                "status": "success",
                "backup_info": backup_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to get backup details: {str(e)}"
            }
    
    def cleanup_old_backups(self, keep_count: int = 10) -> Dict[str, Any]:
        """Clean up old backups, keeping only the most recent ones"""
        backups = self.list_backups()
        
        if len(backups) <= keep_count:
            return {
                "status": "success",
                "message": f"No cleanup needed. {len(backups)} backups (≤ {keep_count})",
                "deleted_count": 0
            }
        
        # Delete oldest backups
        backups_to_delete = backups[keep_count:]
        deleted_count = 0
        errors = []
        
        for backup in backups_to_delete:
            result = self.delete_backup(backup["backup_id"])
            if result["status"] == "success":
                deleted_count += 1
            else:
                errors.append(f"Failed to delete {backup['backup_id']}: {result['error']}")
        
        return {
            "status": "success" if not errors else "partial",
            "message": f"Deleted {deleted_count} old backups, kept {keep_count} recent ones",
            "deleted_count": deleted_count,
            "errors": errors
        }
    
    def _calculate_backup_size(self, backup_path: Path) -> int:
        """Calculate total size of backup directory"""
        total_size = 0
        for file_path in backup_path.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _calculate_age_days(self, timestamp_str: str) -> int:
        """Calculate age of backup in days"""
        try:
            backup_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age = datetime.now() - backup_time.replace(tzinfo=None)
            return age.days
        except:
            return 0


def main():
    """CLI interface for backup operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="IPAM Backup/Restore System")
    parser.add_argument("action", choices=["backup", "restore", "list", "delete", "details", "cleanup"], 
                       help="Action to perform")
    parser.add_argument("--backup-id", help="Backup ID for restore/delete/details operations")
    parser.add_argument("--description", help="Description for new backup")
    parser.add_argument("--keep", type=int, default=10, help="Number of backups to keep during cleanup")
    parser.add_argument("--database-url", help="Database URL", 
                       default=os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management'))
    
    args = parser.parse_args()
    
    # Initialize backup manager
    db_manager = DatabaseManager(args.database_url)
    backup_manager = BackupManager(db_manager)
    
    if args.action == "backup":
        print("🔄 Creating backup...")
        result = backup_manager.create_backup(args.description)
        
        if result["status"] == "success":
            print(f"✅ Backup created successfully!")
            print(f"   Backup ID: {result['backup_id']}")
            print(f"   Location: {result['backup_path']}")
        else:
            print(f"❌ Backup failed: {result['error']}")
            return 1
    
    elif args.action == "list":
        print("📋 Available backups:")
        backups = backup_manager.list_backups()
        
        if not backups:
            print("   No backups found")
        else:
            for backup in backups:
                size_mb = backup["size"] / (1024 * 1024)
                print(f"   {backup['backup_id']} - {backup['description']}")
                print(f"      Created: {backup['timestamp']}")
                print(f"      Size: {size_mb:.1f} MB, Age: {backup['age_days']} days")
                print()
    
    elif args.action == "restore":
        if not args.backup_id:
            print("❌ --backup-id is required for restore")
            return 1
        
        print(f"🔄 Restoring from backup {args.backup_id}...")
        result = backup_manager.restore_backup(args.backup_id)
        
        if result["status"] == "success":
            print(f"✅ Restore completed successfully!")
            print(f"   {result['message']}")
        else:
            print(f"❌ Restore failed: {result['error']}")
            return 1
    
    elif args.action == "delete":
        if not args.backup_id:
            print("❌ --backup-id is required for delete")
            return 1
        
        result = backup_manager.delete_backup(args.backup_id)
        if result["status"] == "success":
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['error']}")
            return 1
    
    elif args.action == "details":
        if not args.backup_id:
            print("❌ --backup-id is required for details")
            return 1
        
        result = backup_manager.get_backup_details(args.backup_id)
        if result["status"] == "success":
            backup = result["backup_info"]
            print(f"📋 Backup Details: {args.backup_id}")
            print(f"   Description: {backup['description']}")
            print(f"   Created: {backup['timestamp']}")
            print(f"   Type: {backup['backup_type']}")
            print(f"   Status: {backup['status']}")
            print(f"   Total Size: {backup['total_size'] / (1024 * 1024):.1f} MB")
            print(f"   Restore Tested: {backup['restore_tested']}")
            print(f"   Files: {len(backup['files_info'])}")
        else:
            print(f"❌ {result['error']}")
            return 1
    
    elif args.action == "cleanup":
        print(f"🧹 Cleaning up old backups (keeping {args.keep} recent)...")
        result = backup_manager.cleanup_old_backups(args.keep)
        print(f"✅ {result['message']}")
        if result.get("errors"):
            for error in result["errors"]:
                print(f"⚠️  {error}")
    
    return 0


if __name__ == "__main__":
    exit(main())
