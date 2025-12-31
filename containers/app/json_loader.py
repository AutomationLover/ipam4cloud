#!/usr/bin/env python3
"""
JSON Data Loader for Prefix Management System
Loads configuration data from human-friendly JSON files
"""

import json
import os
import ipaddress
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
    
    def validate_manual_prefix(self, prefix_data: Dict[str, Any], parent_prefixes: Optional[Dict[str, Any]] = None) -> bool:
        """
        Validate manual prefix data structure and CIDR relationships.
        
        Args:
            prefix_data: The prefix data to validate
            parent_prefixes: Optional dict mapping CIDR or prefix_id to prefix objects for parent validation
        
        Raises:
            ValueError: If validation fails
        """
        required_fields = ['vrf_id', 'cidr']
        optional_fields = ['parent_prefix_id', 'tags', 'routable', 'vpc_children_type_flag']
        
        for field in required_fields:
            if field not in prefix_data:
                raise ValueError(f"Manual prefix missing required field: {field}")
        
        # Validate CIDR format
        try:
            child_network = ipaddress.ip_network(prefix_data['cidr'], strict=False)
        except (ValueError, ipaddress.AddressValueError) as e:
            raise ValueError(f"Invalid CIDR format '{prefix_data['cidr']}': {e}")
        
        # Validate parent-child relationship if parent is specified
        parent_prefix_id = prefix_data.get('parent_prefix_id')
        if parent_prefix_id and parent_prefixes:
            # Try to find parent by CIDR or prefix_id
            parent_prefix = None
            if parent_prefix_id in parent_prefixes:
                parent_prefix = parent_prefixes[parent_prefix_id]
            else:
                # Check if any prefix has this as its prefix_id
                for prefix_obj in parent_prefixes.values():
                    if hasattr(prefix_obj, 'prefix_id') and prefix_obj.prefix_id == parent_prefix_id:
                        parent_prefix = prefix_obj
                        break
                    elif isinstance(prefix_obj, dict) and prefix_obj.get('prefix_id') == parent_prefix_id:
                        parent_prefix = prefix_obj
                        break
            
            if parent_prefix:
                # Get parent CIDR
                if hasattr(parent_prefix, 'cidr'):
                    parent_cidr = str(parent_prefix.cidr)
                elif isinstance(parent_prefix, dict):
                    parent_cidr = parent_prefix.get('cidr')
                else:
                    parent_cidr = str(parent_prefix)
                
                try:
                    parent_network = ipaddress.ip_network(parent_cidr, strict=False)
                    
                    # Validate that child is within parent
                    if not child_network.subnet_of(parent_network):
                        raise ValueError(
                            f"Child prefix {prefix_data['cidr']} is not within parent {parent_cidr}. "
                            f"Parent covers {parent_network.network_address} to {parent_network.broadcast_address}, "
                            f"but child starts at {child_network.network_address}"
                        )
                except (ValueError, ipaddress.AddressValueError) as e:
                    raise ValueError(f"Invalid parent CIDR '{parent_cidr}': {e}")
        
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
    
    def validate_all_prefixes(self, prefixes: List[Dict[str, Any]]) -> List[str]:
        """
        Validate all prefixes and their parent-child relationships.
        Returns a list of validation errors (empty if all valid).
        
        This performs a two-pass validation:
        1. First pass: Validate structure and CIDR format
        2. Second pass: Validate parent-child relationships (after building prefix map)
        """
        errors = []
        prefix_map = {}  # Map CIDR -> prefix_data for parent lookup
        
        # First pass: Basic validation and build prefix map
        for idx, prefix_data in enumerate(prefixes, 1):
            try:
                # Basic structure validation
                self.validate_manual_prefix(prefix_data)
                
                # Validate CIDR format
                try:
                    ipaddress.ip_network(prefix_data['cidr'], strict=False)
                except (ValueError, ipaddress.AddressValueError) as e:
                    errors.append(f"Prefix #{idx} ({prefix_data.get('cidr', 'unknown')}): Invalid CIDR format - {e}")
                    continue
                
                # Store in map for parent validation
                prefix_map[prefix_data['cidr']] = prefix_data
                
            except ValueError as e:
                errors.append(f"Prefix #{idx} ({prefix_data.get('cidr', 'unknown')}): {e}")
        
        # Second pass: Validate parent-child relationships
        for idx, prefix_data in enumerate(prefixes, 1):
            parent_prefix_id = prefix_data.get('parent_prefix_id')
            if not parent_prefix_id:
                continue
            
            # Find parent prefix
            parent_prefix = None
            
            # Check if parent_prefix_id is a CIDR in our map
            if parent_prefix_id in prefix_map:
                parent_prefix = prefix_map[parent_prefix_id]
            else:
                # Check if it's a prefix_id format (manual-vrf-cidr)
                # Try to extract CIDR from prefix_id or find by matching
                for other_prefix in prefix_map.values():
                    # This is a simplified check - in real scenario, we'd need prefix_id
                    # For now, we'll validate when we have the actual prefix objects
                    pass
            
            if parent_prefix:
                try:
                    child_network = ipaddress.ip_network(prefix_data['cidr'], strict=False)
                    parent_network = ipaddress.ip_network(parent_prefix['cidr'], strict=False)
                    
                    if not child_network.subnet_of(parent_network):
                        errors.append(
                            f"Prefix #{idx} ({prefix_data['cidr']}): "
                            f"Child is NOT within parent {parent_prefix['cidr']}. "
                            f"Parent covers {parent_network.network_address} to {parent_network.broadcast_address}, "
                            f"but child starts at {child_network.network_address}"
                        )
                except Exception as e:
                    errors.append(f"Prefix #{idx} ({prefix_data['cidr']}): Error validating parent-child: {e}")
        
        return errors
    
    def load_all_data(self) -> Dict[str, Any]:
        """Load all configuration data from JSON files"""
        return {
            'manual_prefixes': self.load_manual_prefixes(),
            'vpc_data': self.load_vpc_data(),
            'standalone_public_ips': self.load_public_ip_data()
        }
