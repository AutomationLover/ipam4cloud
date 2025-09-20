#!/usr/bin/env python3
"""
Data Export/Import Module for Prefix Management System
Exports and imports all system data (VRFs, VPCs, Prefixes, Associations) in JSON format
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import uuid

from models import DatabaseManager, VRF, VPC, Prefix, VPCPrefixAssociation
from json_loader import JSONDataLoader


class DataExporter:
    """Exports all system data to JSON format compatible with the existing loader"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def export_all_data(self, output_dir: str = "exports") -> Dict[str, str]:
        """
        Export all system data to JSON files
        Returns dict with file paths of exported files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        exported_files = {}
        
        # Export VRFs
        vrfs_file = output_path / f"vrfs_export_{timestamp}.json"
        self._export_vrfs(vrfs_file)
        exported_files['vrfs'] = str(vrfs_file)
        
        # Export manual prefixes
        prefixes_file = output_path / f"manual_prefixes_export_{timestamp}.json"
        self._export_manual_prefixes(prefixes_file)
        exported_files['manual_prefixes'] = str(prefixes_file)
        
        # Export VPC data (VPCs, associations, subnets)
        vpc_file = output_path / f"vpc_data_export_{timestamp}.json"
        self._export_vpc_data(vpc_file)
        exported_files['vpc_data'] = str(vpc_file)
        
        # Export public IPs
        public_ips_file = output_path / f"public_ips_export_{timestamp}.json"
        self._export_public_ips(public_ips_file)
        exported_files['public_ips'] = str(public_ips_file)
        
        # Create a complete export manifest
        manifest_file = output_path / f"export_manifest_{timestamp}.json"
        self._create_export_manifest(manifest_file, exported_files, timestamp)
        exported_files['manifest'] = str(manifest_file)
        
        return exported_files
    
    def _export_vrfs(self, output_file: Path):
        """Export all VRFs to JSON"""
        session = self.db_manager.get_session()
        try:
            vrfs = session.query(VRF).all()
            
            vrf_data = {
                "export_info": {
                    "type": "vrfs",
                    "timestamp": datetime.now().isoformat(),
                    "count": len(vrfs)
                },
                "vrfs": []
            }
            
            for vrf in vrfs:
                vrf_dict = {
                    "vrf_id": vrf.vrf_id,
                    "description": vrf.description,
                    "tags": vrf.tags,
                    "routable_flag": vrf.routable_flag,
                    "is_default": vrf.is_default
                }
                vrf_data["vrfs"].append(vrf_dict)
            
            with open(output_file, 'w') as f:
                json.dump(vrf_data, f, indent=2, default=str)
                
        finally:
            session.close()
    
    def _export_manual_prefixes(self, output_file: Path):
        """Export manual prefixes in the same format as manual_prefixes.json"""
        session = self.db_manager.get_session()
        try:
            # Get only manual prefixes (not VPC-sourced ones)
            manual_prefixes = session.query(Prefix).filter(
                Prefix.source == 'manual'
            ).order_by(Prefix.vrf_id, Prefix.cidr).all()
            
            prefix_data = {
                "export_info": {
                    "type": "manual_prefixes",
                    "timestamp": datetime.now().isoformat(),
                    "count": len(manual_prefixes)
                },
                "prefixes": []
            }
            
            for prefix in manual_prefixes:
                prefix_dict = {
                    "vrf_id": prefix.vrf_id,
                    "cidr": str(prefix.cidr),
                    "tags": prefix.tags,
                    "routable": prefix.routable,
                    "vpc_children_type_flag": prefix.vpc_children_type_flag
                }
                
                # Add parent_prefix_id if exists
                if prefix.parent_prefix_id:
                    prefix_dict["parent_prefix_id"] = prefix.parent_prefix_id
                
                prefix_data["prefixes"].append(prefix_dict)
            
            with open(output_file, 'w') as f:
                json.dump(prefix_data, f, indent=2, default=str)
                
        finally:
            session.close()
    
    def _export_vpc_data(self, output_file: Path):
        """Export VPC data in the same format as vpc_data.json"""
        session = self.db_manager.get_session()
        try:
            vpcs = session.query(VPC).all()
            associations = session.query(VPCPrefixAssociation).all()
            vpc_subnets = session.query(Prefix).filter(
                Prefix.source == 'vpc'
            ).all()
            
            vpc_data = {
                "export_info": {
                    "type": "vpc_data",
                    "timestamp": datetime.now().isoformat(),
                    "vpcs_count": len(vpcs),
                    "associations_count": len(associations),
                    "subnets_count": len(vpc_subnets)
                },
                "vpcs": [],
                "vpc_associations": [],
                "vpc_subnets": [],
                "public_ips": []  # Empty for now, handled separately
            }
            
            # Export VPCs
            for vpc in vpcs:
                vpc_dict = {
                    "description": vpc.description,
                    "provider": vpc.provider,
                    "provider_account_id": vpc.provider_account_id,
                    "provider_vpc_id": vpc.provider_vpc_id,
                    "region": vpc.region,
                    "tags": vpc.tags
                }
                vpc_data["vpcs"].append(vpc_dict)
            
            # Export VPC associations
            for assoc in associations:
                assoc_dict = {
                    "vpc_provider_vpc_id": assoc.vpc.provider_vpc_id,
                    "vpc_prefix_cidr": str(assoc.vpc_prefix_cidr),
                    "routable": assoc.routable,
                    "parent_prefix_id": assoc.parent_prefix_id
                }
                vpc_data["vpc_associations"].append(assoc_dict)
            
            # Export VPC subnets
            for subnet in vpc_subnets:
                subnet_dict = {
                    "vpc_provider_vpc_id": subnet.vpc.provider_vpc_id,
                    "subnet_cidr": str(subnet.cidr),
                    "tags": subnet.tags
                }
                vpc_data["vpc_subnets"].append(subnet_dict)
            
            with open(output_file, 'w') as f:
                json.dump(vpc_data, f, indent=2, default=str)
                
        finally:
            session.close()
    
    def _export_public_ips(self, output_file: Path):
        """Export public IP prefixes"""
        session = self.db_manager.get_session()
        try:
            # Get prefixes that are in public-vrf (assuming that's where public IPs are)
            public_prefixes = session.query(Prefix).filter(
                Prefix.vrf_id == 'public-vrf'
            ).all()
            
            public_ip_data = {
                "export_info": {
                    "type": "public_ips",
                    "timestamp": datetime.now().isoformat(),
                    "count": len(public_prefixes)
                },
                "public_ips": []
            }
            
            for prefix in public_prefixes:
                ip_dict = {
                    "cidr": str(prefix.cidr),
                    "tags": prefix.tags
                }
                
                # Add VPC info if available
                if prefix.vpc:
                    ip_dict["vpc_provider_vpc_id"] = prefix.vpc.provider_vpc_id
                
                public_ip_data["public_ips"].append(ip_dict)
            
            with open(output_file, 'w') as f:
                json.dump(public_ip_data, f, indent=2, default=str)
                
        finally:
            session.close()
    
    def _create_export_manifest(self, output_file: Path, exported_files: Dict[str, str], timestamp: str):
        """Create a manifest file describing the export"""
        session = self.db_manager.get_session()
        try:
            # Get counts for summary
            vrf_count = session.query(VRF).count()
            vpc_count = session.query(VPC).count()
            prefix_count = session.query(Prefix).count()
            manual_prefix_count = session.query(Prefix).filter(Prefix.source == 'manual').count()
            vpc_prefix_count = session.query(Prefix).filter(Prefix.source == 'vpc').count()
            association_count = session.query(VPCPrefixAssociation).count()
            
            manifest = {
                "export_info": {
                    "timestamp": timestamp,
                    "export_type": "complete_system_export",
                    "version": "1.0"
                },
                "summary": {
                    "total_vrfs": vrf_count,
                    "total_vpcs": vpc_count,
                    "total_prefixes": prefix_count,
                    "manual_prefixes": manual_prefix_count,
                    "vpc_prefixes": vpc_prefix_count,
                    "vpc_associations": association_count
                },
                "exported_files": exported_files,
                "import_instructions": {
                    "order": [
                        "1. Import VRFs first (if needed)",
                        "2. Import manual prefixes",
                        "3. Import VPC data (VPCs, associations, subnets)",
                        "4. Import public IPs"
                    ],
                    "note": "Use DataImporter class or existing JSONDataLoader for import"
                }
            }
            
            with open(output_file, 'w') as f:
                json.dump(manifest, f, indent=2, default=str)
                
        finally:
            session.close()


class DataImporter:
    """Imports data from exported JSON files"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.json_loader = JSONDataLoader()
    
    def import_from_manifest(self, manifest_file: str) -> Dict[str, Any]:
        """Import data using an export manifest file"""
        with open(manifest_file, 'r') as f:
            manifest = json.load(f)
        
        results = {
            "imported": {},
            "errors": [],
            "summary": {}
        }
        
        exported_files = manifest.get("exported_files", {})
        
        try:
            # Import VRFs if available
            if "vrfs" in exported_files:
                vrf_result = self.import_vrfs(exported_files["vrfs"])
                results["imported"]["vrfs"] = vrf_result
            
            # Import manual prefixes
            if "manual_prefixes" in exported_files:
                prefix_result = self.import_manual_prefixes(exported_files["manual_prefixes"])
                results["imported"]["manual_prefixes"] = prefix_result
            
            # Import VPC data
            if "vpc_data" in exported_files:
                vpc_result = self.import_vpc_data(exported_files["vpc_data"])
                results["imported"]["vpc_data"] = vpc_result
            
            # Import public IPs
            if "public_ips" in exported_files:
                public_ip_result = self.import_public_ips(exported_files["public_ips"])
                results["imported"]["public_ips"] = public_ip_result
            
            results["summary"] = {
                "status": "success",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            results["errors"].append(f"Import failed: {str(e)}")
            results["summary"] = {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        return results
    
    def import_vrfs(self, vrfs_file: str) -> Dict[str, Any]:
        """Import VRFs from exported file"""
        with open(vrfs_file, 'r') as f:
            vrf_data = json.load(f)
        
        session = self.db_manager.get_session()
        try:
            imported_count = 0
            skipped_count = 0
            
            for vrf_dict in vrf_data["vrfs"]:
                # Check if VRF already exists
                existing_vrf = session.query(VRF).filter(
                    VRF.vrf_id == vrf_dict["vrf_id"]
                ).first()
                
                if existing_vrf:
                    skipped_count += 1
                    continue
                
                # Create new VRF
                vrf = VRF(
                    vrf_id=vrf_dict["vrf_id"],
                    description=vrf_dict.get("description"),
                    tags=vrf_dict.get("tags", {}),
                    routable_flag=vrf_dict.get("routable_flag", True),
                    is_default=vrf_dict.get("is_default", False)
                )
                
                session.add(vrf)
                imported_count += 1
            
            session.commit()
            
            return {
                "status": "success",
                "imported": imported_count,
                "skipped": skipped_count,
                "total": len(vrf_data["vrfs"])
            }
            
        except Exception as e:
            session.rollback()
            return {
                "status": "error",
                "error": str(e)
            }
        finally:
            session.close()
    
    def import_manual_prefixes(self, prefixes_file: str) -> Dict[str, Any]:
        """Import manual prefixes using existing JSONDataLoader logic"""
        try:
            # Temporarily copy the file to the data directory for JSONDataLoader
            temp_filename = f"temp_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            temp_path = Path("data") / temp_filename
            
            # Copy file content to temp location
            with open(prefixes_file, 'r') as src, open(temp_path, 'w') as dst:
                data = json.load(src)
                json.dump(data, dst, indent=2)
            
            # Use existing JSONDataLoader
            from main import load_manual_prefixes_from_json, PrefixManager
            
            prefix_manager = PrefixManager(self.db_manager)
            data_loader = JSONDataLoader(data_dir='data')
            
            # Temporarily modify the loader to use our temp file
            original_load = data_loader.load_manual_prefixes
            data_loader.load_manual_prefixes = lambda: json.load(open(temp_path))["prefixes"]
            
            try:
                created_prefixes = load_manual_prefixes_from_json(prefix_manager, data_loader)
                
                return {
                    "status": "success",
                    "imported": len(created_prefixes),
                    "prefixes": list(created_prefixes.keys())
                }
            finally:
                # Restore original method and cleanup
                data_loader.load_manual_prefixes = original_load
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def import_vpc_data(self, vpc_file: str) -> Dict[str, Any]:
        """Import VPC data using existing JSONDataLoader logic"""
        try:
            # Similar approach as manual prefixes
            temp_filename = f"temp_vpc_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            temp_path = Path("data") / temp_filename
            
            with open(vpc_file, 'r') as src, open(temp_path, 'w') as dst:
                data = json.load(src)
                json.dump(data, dst, indent=2)
            
            from main import load_vpc_data_from_json, PrefixManager
            
            prefix_manager = PrefixManager(self.db_manager)
            data_loader = JSONDataLoader(data_dir='data')
            
            # Temporarily modify the loader
            original_load = data_loader.load_vpc_data
            data_loader.load_vpc_data = lambda: json.load(open(temp_path))
            
            try:
                created_vpcs = load_vpc_data_from_json(prefix_manager, data_loader)
                
                return {
                    "status": "success",
                    "imported": len(created_vpcs),
                    "vpcs": list(created_vpcs.keys())
                }
            finally:
                data_loader.load_vpc_data = original_load
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def import_public_ips(self, public_ips_file: str) -> Dict[str, Any]:
        """Import public IPs"""
        try:
            temp_filename = f"temp_public_ips_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            temp_path = Path("data") / temp_filename
            
            with open(public_ips_file, 'r') as src, open(temp_path, 'w') as dst:
                data = json.load(src)
                json.dump(data, dst, indent=2)
            
            from main import load_public_ips_from_json, PrefixManager
            
            prefix_manager = PrefixManager(self.db_manager)
            data_loader = JSONDataLoader(data_dir='data')
            
            # Get VPCs for the public IP loader
            session = self.db_manager.get_session()
            try:
                vpcs = session.query(VPC).all()
                vpc_lookup = {vpc.provider_vpc_id: vpc for vpc in vpcs}
            finally:
                session.close()
            
            # Temporarily modify the loader
            original_load = data_loader.load_public_ip_data
            data_loader.load_public_ip_data = lambda: json.load(open(temp_path))["public_ips"]
            
            try:
                load_public_ips_from_json(prefix_manager, data_loader, vpc_lookup)
                
                return {
                    "status": "success",
                    "message": "Public IPs imported successfully"
                }
            finally:
                data_loader.load_public_ip_data = original_load
                if temp_path.exists():
                    temp_path.unlink()
                    
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


def main():
    """CLI interface for export/import operations"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Export/Import IPAM data")
    parser.add_argument("action", choices=["export", "import"], help="Action to perform")
    parser.add_argument("--output-dir", default="exports", help="Output directory for exports")
    parser.add_argument("--manifest", help="Manifest file for import")
    parser.add_argument("--database-url", help="Database URL", 
                       default=os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management'))
    
    args = parser.parse_args()
    
    # Initialize database connection
    db_manager = DatabaseManager(args.database_url)
    
    if args.action == "export":
        print("🚀 Starting data export...")
        exporter = DataExporter(db_manager)
        exported_files = exporter.export_all_data(args.output_dir)
        
        print("\n✅ Export completed successfully!")
        print(f"📁 Files exported to: {args.output_dir}")
        for file_type, file_path in exported_files.items():
            print(f"   {file_type}: {file_path}")
        
        print(f"\n📋 Use the manifest file for import: {exported_files['manifest']}")
        
    elif args.action == "import":
        if not args.manifest:
            print("❌ Error: --manifest file is required for import")
            return 1
        
        print(f"🚀 Starting data import from: {args.manifest}")
        importer = DataImporter(db_manager)
        results = importer.import_from_manifest(args.manifest)
        
        if results["summary"]["status"] == "success":
            print("\n✅ Import completed successfully!")
            for data_type, result in results["imported"].items():
                if result.get("status") == "success":
                    print(f"   {data_type}: {result.get('imported', 0)} items imported")
                else:
                    print(f"   {data_type}: {result.get('error', 'Unknown error')}")
        else:
            print(f"\n❌ Import failed: {results['summary'].get('error')}")
            return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
