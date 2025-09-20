#!/usr/bin/env python3
"""
JSON Data Loader for Prefix Management System
Loads configuration data from human-friendly JSON files
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path

class JSONDataLoader:
    """Loads prefix and VPC data from JSON configuration files"""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize loader with data directory path"""
        self.data_dir = Path(data_dir)
        
    def load_manual_prefixes(self, filename: str = "manual_prefixes.gen.json") -> List[Dict[str, Any]]:
        """Load manual prefix configuration from JSON file"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Manual prefixes file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Validate required structure
        if 'prefixes' not in data:
            raise ValueError(f"Invalid manual prefixes file: missing 'prefixes' key")
        
        return data['prefixes']
    
    def load_vpc_data(self, filename: str = "vpc_data.gen.json") -> Dict[str, Any]:
        """Load VPC configuration from JSON file"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            raise FileNotFoundError(f"VPC data file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Validate required structure
        required_keys = ['vpcs', 'vpc_associations', 'vpc_subnets', 'public_ips']
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Invalid VPC data file: missing '{key}' key")
        
        return data
    
    def load_public_ip_data(self, filename: str = "public_ips.gen.json") -> List[Dict[str, Any]]:
        """Load standalone public IP configuration from JSON file"""
        filepath = self.data_dir / filename
        if not filepath.exists():
            # If file doesn't exist, return empty list (optional file)
            return []
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Validate required structure
        if 'public_ips' not in data:
            raise ValueError(f"Invalid public IPs file: missing 'public_ips' key")
        
        return data['public_ips']
    
    def validate_manual_prefix(self, prefix_data: Dict[str, Any]) -> bool:
        """Validate manual prefix data structure"""
        required_fields = ['vrf_id', 'cidr']
        optional_fields = ['parent_prefix_id', 'tags', 'routable', 'vpc_children_type_flag']
        
        for field in required_fields:
            if field not in prefix_data:
                raise ValueError(f"Manual prefix missing required field: {field}")
        
        return True
    
    def validate_vpc_data(self, vpc_data: Dict[str, Any]) -> bool:
        """Validate VPC data structure"""
        required_fields = ['description', 'provider', 'provider_account_id', 'provider_vpc_id', 'region']
        optional_fields = ['tags']
        
        for field in required_fields:
            if field not in vpc_data:
                raise ValueError(f"VPC data missing required field: {field}")
        
        return True
    
    def validate_vpc_association(self, association_data: Dict[str, Any]) -> bool:
        """Validate VPC association data structure"""
        required_fields = ['vpc_provider_vpc_id', 'vpc_prefix_cidr', 'routable', 'parent_prefix_id']
        
        for field in required_fields:
            if field not in association_data:
                raise ValueError(f"VPC association missing required field: {field}")
        
        return True
    
    def validate_vpc_subnet(self, subnet_data: Dict[str, Any]) -> bool:
        """Validate VPC subnet data structure"""
        required_fields = ['vpc_provider_vpc_id', 'subnet_cidr']
        optional_fields = ['tags']
        
        for field in required_fields:
            if field not in subnet_data:
                raise ValueError(f"VPC subnet missing required field: {field}")
        
        return True
    
    def validate_public_ip(self, ip_data: Dict[str, Any]) -> bool:
        """Validate public IP data structure"""
        required_fields = ['cidr']
        optional_fields = ['tags', 'vpc_provider_vpc_id']
        
        for field in required_fields:
            if field not in ip_data:
                raise ValueError(f"Public IP missing required field: {field}")
        
        return True
    
    def load_all_data(self) -> Dict[str, Any]:
        """Load all configuration data from JSON files"""
        return {
            'manual_prefixes': self.load_manual_prefixes(),
            'vpc_data': self.load_vpc_data(),
            'standalone_public_ips': self.load_public_ip_data()
        }
