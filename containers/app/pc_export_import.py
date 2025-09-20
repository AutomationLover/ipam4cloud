#!/usr/bin/env python3
"""
PC Export/Import System for IPAM4Cloud
Handles data export to user's PC and import from user's PC folders
"""

import os
import json
import shutil
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

from models import DatabaseManager
from data_export_import import DataExporter, DataImporter


class PCExportImportManager:
    """Manages export to PC and import from PC folders"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.exporter = DataExporter(db_manager)
        self.importer = DataImporter(db_manager)
    
    def export_to_pc(self, pc_folder_path: str, export_name: str = None) -> Dict[str, Any]:
        """Export data to a specific folder on user's PC"""
        try:
            # Validate PC folder path
            pc_path = Path(pc_folder_path)
            if not pc_path.exists():
                return {
                    "status": "error",
                    "error": f"PC folder does not exist: {pc_folder_path}"
                }
            
            if not pc_path.is_dir():
                return {
                    "status": "error",
                    "error": f"Path is not a directory: {pc_folder_path}"
                }
            
            # Create export name if not provided
            if not export_name:
                export_name = f"ipam_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Create export subdirectory
            export_dir = pc_path / export_name
            export_dir.mkdir(exist_ok=True)
            
            # Export data using existing exporter
            exported_files = self.exporter.export_all_data(str(export_dir))
            
            # Create PC export metadata
            pc_export_info = {
                "export_name": export_name,
                "export_path": str(export_dir),
                "timestamp": datetime.now().isoformat(),
                "export_type": "pc_export",
                "created_by": "user",
                "source_system": "ipam4cloud",
                "files": exported_files,
                "pc_folder": pc_folder_path
            }
            
            # Save PC export metadata
            metadata_file = export_dir / "pc_export_info.json"
            with open(metadata_file, 'w') as f:
                json.dump(pc_export_info, f, indent=2, default=str)
            
            return {
                "status": "success",
                "export_name": export_name,
                "export_path": str(export_dir),
                "pc_folder": pc_folder_path,
                "files_created": len(exported_files),
                "export_info": pc_export_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"PC export failed: {str(e)}"
            }
    
    def import_from_pc(self, pc_folder_path: str) -> Dict[str, Any]:
        """Import data from a specific folder on user's PC"""
        try:
            # Validate PC folder path
            pc_path = Path(pc_folder_path)
            if not pc_path.exists():
                return {
                    "status": "error",
                    "error": f"PC folder does not exist: {pc_folder_path}"
                }
            
            if not pc_path.is_dir():
                return {
                    "status": "error",
                    "error": f"Path is not a directory: {pc_folder_path}"
                }
            
            # Look for manifest file
            manifest_files = list(pc_path.glob("export_manifest_*.json"))
            if not manifest_files:
                return {
                    "status": "error",
                    "error": f"No export manifest found in: {pc_folder_path}"
                }
            
            # Use the first manifest file found
            manifest_file = str(manifest_files[0])
            
            # Perform import using existing importer
            import_results = self.importer.import_from_manifest(manifest_file)
            
            if import_results["summary"]["status"] == "success":
                return {
                    "status": "success",
                    "pc_folder": pc_folder_path,
                    "manifest_file": manifest_file,
                    "import_results": import_results,
                    "message": f"Successfully imported data from {pc_folder_path}"
                }
            else:
                return {
                    "status": "error",
                    "error": f"Import failed: {import_results['summary'].get('error')}",
                    "import_results": import_results
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"PC import failed: {str(e)}"
            }
    
    def scan_pc_folder(self, pc_folder_path: str) -> Dict[str, Any]:
        """Scan a PC folder for importable IPAM exports"""
        try:
            pc_path = Path(pc_folder_path)
            if not pc_path.exists():
                return {
                    "status": "error",
                    "error": f"PC folder does not exist: {pc_folder_path}"
                }
            
            exports_found = []
            
            # Look for export directories and files
            for item in pc_path.iterdir():
                if item.is_dir():
                    # Check if directory contains IPAM export
                    manifest_files = list(item.glob("export_manifest_*.json"))
                    if manifest_files:
                        try:
                            with open(manifest_files[0], 'r') as f:
                                manifest = json.load(f)
                            
                            export_info = {
                                "folder_name": item.name,
                                "folder_path": str(item),
                                "manifest_file": str(manifest_files[0]),
                                "timestamp": manifest.get("export_info", {}).get("timestamp", "unknown"),
                                "summary": manifest.get("summary", {}),
                                "files": manifest.get("exported_files", {}),
                                "is_valid": True
                            }
                            exports_found.append(export_info)
                            
                        except Exception as e:
                            # Invalid export directory
                            exports_found.append({
                                "folder_name": item.name,
                                "folder_path": str(item),
                                "error": f"Invalid export: {str(e)}",
                                "is_valid": False
                            })
            
            return {
                "status": "success",
                "pc_folder": pc_folder_path,
                "exports_found": exports_found,
                "valid_exports": len([e for e in exports_found if e.get("is_valid", False)]),
                "total_items": len(exports_found)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to scan PC folder: {str(e)}"
            }
    
    def validate_pc_export(self, pc_folder_path: str) -> Dict[str, Any]:
        """Validate that a PC folder contains a valid IPAM export"""
        try:
            pc_path = Path(pc_folder_path)
            if not pc_path.exists() or not pc_path.is_dir():
                return {
                    "status": "error",
                    "error": "Invalid folder path"
                }
            
            # Check for required files
            required_files = [
                "export_manifest_*.json",
                "vrfs_export_*.json",
                "manual_prefixes_export_*.json",
                "vpc_data_export_*.json"
            ]
            
            validation_results = {
                "folder_path": pc_folder_path,
                "is_valid": True,
                "missing_files": [],
                "found_files": [],
                "warnings": []
            }
            
            for pattern in required_files:
                files = list(pc_path.glob(pattern))
                if files:
                    validation_results["found_files"].extend([f.name for f in files])
                else:
                    validation_results["missing_files"].append(pattern)
                    validation_results["is_valid"] = False
            
            # Check manifest if present
            manifest_files = list(pc_path.glob("export_manifest_*.json"))
            if manifest_files:
                try:
                    with open(manifest_files[0], 'r') as f:
                        manifest = json.load(f)
                    
                    validation_results["manifest_info"] = {
                        "timestamp": manifest.get("export_info", {}).get("timestamp"),
                        "version": manifest.get("export_info", {}).get("version"),
                        "summary": manifest.get("summary", {})
                    }
                    
                except Exception as e:
                    validation_results["warnings"].append(f"Manifest file is corrupted: {str(e)}")
            
            return {
                "status": "success",
                "validation": validation_results
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Validation failed: {str(e)}"
            }


def main():
    """CLI interface for PC export/import operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="IPAM PC Export/Import System")
    parser.add_argument("action", choices=["export", "import", "scan", "validate"], 
                       help="Action to perform")
    parser.add_argument("--pc-folder", required=True, help="PC folder path")
    parser.add_argument("--export-name", help="Name for export (auto-generated if not provided)")
    parser.add_argument("--database-url", help="Database URL", 
                       default=os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management'))
    
    args = parser.parse_args()
    
    # Initialize PC export/import manager
    db_manager = DatabaseManager(args.database_url)
    pc_manager = PCExportImportManager(db_manager)
    
    if args.action == "export":
        print(f"📤 Exporting to PC folder: {args.pc_folder}")
        result = pc_manager.export_to_pc(args.pc_folder, args.export_name)
        
        if result["status"] == "success":
            print(f"✅ Export completed successfully!")
            print(f"   Export Name: {result['export_name']}")
            print(f"   Export Path: {result['export_path']}")
            print(f"   Files Created: {result['files_created']}")
        else:
            print(f"❌ Export failed: {result['error']}")
            return 1
    
    elif args.action == "import":
        print(f"📥 Importing from PC folder: {args.pc_folder}")
        result = pc_manager.import_from_pc(args.pc_folder)
        
        if result["status"] == "success":
            print(f"✅ Import completed successfully!")
            print(f"   {result['message']}")
        else:
            print(f"❌ Import failed: {result['error']}")
            return 1
    
    elif args.action == "scan":
        print(f"🔍 Scanning PC folder: {args.pc_folder}")
        result = pc_manager.scan_pc_folder(args.pc_folder)
        
        if result["status"] == "success":
            print(f"📋 Scan Results:")
            print(f"   Valid Exports: {result['valid_exports']}")
            print(f"   Total Items: {result['total_items']}")
            
            for export in result["exports_found"]:
                if export.get("is_valid"):
                    print(f"   ✅ {export['folder_name']} - {export.get('timestamp', 'unknown')}")
                else:
                    print(f"   ❌ {export['folder_name']} - {export.get('error', 'invalid')}")
        else:
            print(f"❌ Scan failed: {result['error']}")
            return 1
    
    elif args.action == "validate":
        print(f"🔍 Validating PC folder: {args.pc_folder}")
        result = pc_manager.validate_pc_export(args.pc_folder)
        
        if result["status"] == "success":
            validation = result["validation"]
            if validation["is_valid"]:
                print(f"✅ Valid IPAM export found!")
                print(f"   Found Files: {len(validation['found_files'])}")
                if validation.get("manifest_info"):
                    manifest = validation["manifest_info"]
                    print(f"   Timestamp: {manifest.get('timestamp', 'unknown')}")
                    summary = manifest.get("summary", {})
                    print(f"   VRFs: {summary.get('total_vrfs', 0)}")
                    print(f"   VPCs: {summary.get('total_vpcs', 0)}")
                    print(f"   Prefixes: {summary.get('total_prefixes', 0)}")
            else:
                print(f"❌ Invalid IPAM export")
                print(f"   Missing Files: {validation['missing_files']}")
            
            if validation.get("warnings"):
                for warning in validation["warnings"]:
                    print(f"   ⚠️  {warning}")
        else:
            print(f"❌ Validation failed: {result['error']}")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
