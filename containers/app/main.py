#!/usr/bin/env python3
"""
Prefix Management System Demo
Implements the user stories from the database design document.
"""

import os
import time
import uuid
import csv
import ast
import json
import ipaddress
from pathlib import Path
from typing import Optional
from sqlalchemy import text
from models import DatabaseManager, PrefixManager, VRF, VPC, Prefix
from json_loader import JSONDataLoader

def wait_for_db(db_manager: DatabaseManager, max_retries: int = 30):
    """Wait for database to be ready"""
    for i in range(max_retries):
        try:
            session = db_manager.get_session()
            session.execute(text("SELECT 1"))
            session.close()
            print("✓ Database connection established")
            return True
        except Exception as e:
            print(f"Waiting for database... ({i+1}/{max_retries}) - {str(e)[:50]}")
            time.sleep(3)
    
    raise Exception("Could not connect to database after maximum retries")

def find_parent_prefix(prefix_manager: PrefixManager, vrf_id: str, cidr: str) -> Optional[str]:
    """
    Automatically find the parent prefix for a given CIDR in the same VRF.
    Returns the most specific parent prefix that contains this CIDR.
    """
    try:
        child_network = ipaddress.ip_network(cidr, strict=False)
    except (ValueError, ipaddress.AddressValueError):
        return None
    
    with prefix_manager.db_manager.get_session() as session:
        from models import Prefix
        
        # Find all prefixes in the same VRF that could be parents
        potential_parents = session.query(Prefix).filter(
            Prefix.vrf_id == vrf_id,
            Prefix.source == 'manual'  # Only manual prefixes can be parents
        ).all()
        
        # Filter to find prefixes that contain this CIDR
        containing_parents = []
        for prefix in potential_parents:
            try:
                parent_network = ipaddress.ip_network(str(prefix.cidr), strict=False)
                # Only compare networks of the same IP version (IPv4 vs IPv6)
                if parent_network.version != child_network.version:
                    continue
                # Check if child is a subnet of parent (parent contains child)
                if child_network.subnet_of(parent_network):
                    containing_parents.append(prefix)
            except (ValueError, ipaddress.AddressValueError, TypeError):
                continue
        
        if not containing_parents:
            return None
        
        # Sort by prefix length (most specific/longest mask first)
        # This ensures we get the closest parent
        containing_parents.sort(
            key=lambda p: ipaddress.ip_network(str(p.cidr), strict=False).prefixlen,
            reverse=True
        )
        
        # Return the most specific parent
        return containing_parents[0].prefix_id

def safe_create_prefix(prefix_manager: PrefixManager, **kwargs):
    """Create prefix with duplicate handling and automatic parent detection"""
    # If parent_prefix_id is not provided, try to find it automatically
    if kwargs.get('parent_prefix_id') is None:
        vrf_id = kwargs.get('vrf_id')
        cidr = kwargs.get('cidr')
        if vrf_id and cidr:
            auto_parent = find_parent_prefix(prefix_manager, vrf_id, cidr)
            if auto_parent:
                kwargs['parent_prefix_id'] = auto_parent
    
    try:
        return prefix_manager.create_manual_prefix(**kwargs)
    except Exception as e:
        if "already exists" in str(e) or "duplicate key" in str(e):
            return prefix_manager.query_prefix_by_cidr(kwargs['vrf_id'], kwargs['cidr'])
        else:
            raise e

def safe_create_vpc(prefix_manager: PrefixManager, **kwargs):
    """Create VPC with duplicate handling"""
    try:
        return prefix_manager.create_vpc(**kwargs)
    except Exception as e:
        if "already exists" in str(e) or "duplicate key" in str(e):
            # Find existing VPC by provider details
            session = prefix_manager.db_manager.get_session()
            try:
                from models import VPC
                vpc = session.query(VPC).filter(
                    VPC.provider == kwargs['provider'],
                    VPC.provider_account_id == kwargs['provider_account_id'],
                    VPC.provider_vpc_id == kwargs['provider_vpc_id']
                ).first()
                return vpc
            finally:
                session.close()
        else:
            raise e

def safe_associate_vpc(prefix_manager: PrefixManager, **kwargs):
    """Associate VPC with duplicate handling"""
    try:
        return prefix_manager.associate_vpc_with_prefix(**kwargs)
    except Exception as e:
        if "already exists" in str(e) or "duplicate key" in str(e):
            # Find existing association
            session = prefix_manager.db_manager.get_session()
            try:
                from models import VPCPrefixAssociation
                association = session.query(VPCPrefixAssociation).filter(
                    VPCPrefixAssociation.vpc_id == kwargs['vpc_id'],
                    VPCPrefixAssociation.vpc_prefix_cidr == kwargs['vpc_prefix_cidr']
                ).first()
                return association
            finally:
                session.close()
        else:
            raise e

def safe_create_public_ip(prefix_manager: PrefixManager, vpc_id: uuid.UUID, cidr: str, tags: dict):
    """Create public IP with duplicate handling"""
    try:
        return prefix_manager.create_public_ip_prefix(vpc_id, cidr, tags)
    except Exception as e:
        if "already exists" in str(e) or "duplicate key" in str(e):
            return prefix_manager.query_prefix_by_cidr('public-vrf', cidr)
        else:
            raise e

def safe_create_standalone_public_ip(prefix_manager: PrefixManager, cidr: str, tags: dict):
    """Create standalone public IP with duplicate handling"""
    try:
        return prefix_manager.create_standalone_public_ip_prefix(cidr, tags)
    except Exception as e:
        if "already exists" in str(e) or "duplicate key" in str(e):
            return prefix_manager.query_prefix_by_cidr('public-vrf', cidr)
        else:
            raise e

def load_manual_prefixes_from_json(prefix_manager: PrefixManager, data_loader: JSONDataLoader):
    """
    Load manual prefix planning from JSON configuration
    """
    print("\n" + "="*60)
    print("LOADING: Manual Prefix Configuration from JSON")
    print("="*60)
    
    try:
        manual_prefixes = data_loader.load_manual_prefixes()
        created_prefixes = {}
        
        print(f"\nLoading {len(manual_prefixes)} manual prefixes...")
        
        # First pass: Validate all prefixes (structure and CIDR format)
        print("\n📋 Validating prefix data...")
        for prefix_data in manual_prefixes:
            # Basic validation (structure and CIDR format)
            data_loader.validate_manual_prefix(prefix_data)
        
        # Second pass: Create prefixes and validate parent-child relationships
        for prefix_data in manual_prefixes:
            print(f"\nCreating prefix: {prefix_data['cidr']} in VRF {prefix_data['vrf_id']}")
            
            # Resolve parent_prefix_id if it's a reference to another prefix
            parent_prefix_id = prefix_data.get('parent_prefix_id')
            if parent_prefix_id and parent_prefix_id.startswith('manual-'):
                # It's already a prefix ID
                pass
            elif parent_prefix_id in created_prefixes:
                # It's a reference to a previously created prefix
                parent_prefix_id = created_prefixes[parent_prefix_id].prefix_id
            
            # Validate parent-child relationship if parent exists
            if parent_prefix_id:
                # Find parent in created_prefixes
                parent_prefix = None
                # Check by prefix_id first
                for created_prefix in created_prefixes.values():
                    if created_prefix.prefix_id == parent_prefix_id:
                        parent_prefix = created_prefix
                        break
                # If not found, check if parent_prefix_id is a CIDR that was created
                if not parent_prefix and parent_prefix_id in created_prefixes:
                    parent_prefix = created_prefixes[parent_prefix_id]
                
                if parent_prefix:
                    # Validate parent-child relationship
                    try:
                        import ipaddress
                        child_network = ipaddress.ip_network(prefix_data['cidr'], strict=False)
                        parent_network = ipaddress.ip_network(str(parent_prefix.cidr), strict=False)
                        
                        if not child_network.subnet_of(parent_network):
                            raise ValueError(
                                f"❌ Validation Error: Child prefix {prefix_data['cidr']} is NOT within parent {parent_prefix.cidr}.\n"
                                f"   Parent {parent_prefix.cidr} covers: {parent_network.network_address} to {parent_network.broadcast_address}\n"
                                f"   Child {prefix_data['cidr']} starts at: {child_network.network_address}\n"
                                f"   This will fail at database level. Please fix the JSON file."
                            )
                    except ValueError as e:
                        # Re-raise validation errors
                        raise e
                    except Exception as e:
                        # Log but don't fail on other errors during validation
                        print(f"   ⚠️  Warning: Could not validate parent-child relationship: {e}")
            
            prefix = safe_create_prefix(
                prefix_manager,
                vrf_id=prefix_data['vrf_id'],
                cidr=prefix_data['cidr'],
                parent_prefix_id=parent_prefix_id,
                tags=prefix_data.get('tags', {}),
                routable=prefix_data.get('routable', True),
                vpc_children_type_flag=prefix_data.get('vpc_children_type_flag', False)
            )
            
            # Store prefix for reference by other prefixes
            created_prefixes[prefix_data['cidr']] = prefix
            print(f"   ✓ Created: {prefix.prefix_id}")
        
        print(f"\n✅ Successfully loaded {len(created_prefixes)} manual prefixes")
        return created_prefixes
        
    except Exception as e:
        print(f"❌ Error loading manual prefixes: {e}")
        raise

def load_vpc_data_from_json(prefix_manager: PrefixManager, data_loader: JSONDataLoader):
    """
    Load VPC configuration from JSON
    """
    print("\n" + "="*60)
    print("LOADING: VPC Configuration from JSON")
    print("="*60)
    
    try:
        vpc_data = data_loader.load_vpc_data()
        created_vpcs = {}
        vpc_lookup = {}  # Map provider_vpc_id to VPC object
        
        # Step 1: Create VPCs
        print(f"\n1. Creating {len(vpc_data['vpcs'])} VPCs...")
        for vpc_config in vpc_data['vpcs']:
            data_loader.validate_vpc_data(vpc_config)
            
            print(f"   Creating VPC: {vpc_config['provider_vpc_id']} ({vpc_config['description']})")
            
            vpc = safe_create_vpc(
                prefix_manager,
                description=vpc_config['description'],
                provider=vpc_config['provider'],
                provider_account_id=vpc_config['provider_account_id'],
                provider_vpc_id=vpc_config['provider_vpc_id'],
                region=vpc_config['region'],
                tags=vpc_config.get('tags', {})
            )
            
            created_vpcs[vpc_config['provider_vpc_id']] = vpc
            vpc_lookup[vpc_config['provider_vpc_id']] = vpc
            print(f"      ✓ Created VPC: {vpc.vpc_id}")
        
        # Step 2: Create VPC associations
        print(f"\n2. Creating {len(vpc_data['vpc_associations'])} VPC associations...")
        for assoc_config in vpc_data['vpc_associations']:
            data_loader.validate_vpc_association(assoc_config)
            
            vpc_id = vpc_lookup[assoc_config['vpc_provider_vpc_id']].vpc_id
            
            print(f"   Associating VPC {assoc_config['vpc_provider_vpc_id']} with prefix {assoc_config['vpc_prefix_cidr']}")
            
            association = safe_associate_vpc(
                prefix_manager,
                vpc_id=vpc_id,
                vpc_prefix_cidr=assoc_config['vpc_prefix_cidr'],
                routable=assoc_config['routable'],
                parent_prefix_id=assoc_config['parent_prefix_id']
            )
            print(f"      ✓ Created association: {association.association_id}")
        
        print(f"\n✅ Successfully loaded VPC configuration")
        return created_vpcs
        
    except Exception as e:
        print(f"❌ Error loading VPC data: {e}")
        raise

def load_vpc_subnets_from_json(prefix_manager: PrefixManager, data_loader: JSONDataLoader, vpcs_lookup: dict):
    """
    Load VPC subnets from JSON configuration
    """
    print("\n" + "="*60)
    print("LOADING: VPC Subnets from JSON")
    print("="*60)
    
    try:
        vpc_data = data_loader.load_vpc_data()
        
        print(f"\nLoading {len(vpc_data['vpc_subnets'])} VPC subnets...")
        
        for subnet_config in vpc_data['vpc_subnets']:
            data_loader.validate_vpc_subnet(subnet_config)
            
            vpc_provider_id = subnet_config['vpc_provider_vpc_id']
            if vpc_provider_id not in vpcs_lookup:
                print(f"   ⚠️  Skipping subnet {subnet_config['subnet_cidr']} - VPC {vpc_provider_id} not found")
                continue
            
            vpc = vpcs_lookup[vpc_provider_id]
            
            print(f"   Ingesting subnet: {subnet_config['subnet_cidr']} in VPC {vpc_provider_id}")
            prefix_id = prefix_manager.upsert_vpc_subnet(
                vpc.vpc_id,
                subnet_config['subnet_cidr'],
                subnet_config.get('tags', {})
            )
            print(f"      ✓ Created: {prefix_id}")
        
        print(f"\n✅ Successfully loaded VPC subnets")
        
    except Exception as e:
        print(f"❌ Error loading VPC subnets: {e}")
        raise

def demo_user_story_client_queries(prefix_manager: PrefixManager, vpc1: VPC, vpc2: VPC):
    """
    User Story: Client queries
    - List all prefixes in order
    - Tree view with hierarchy
    - Query specific prefixes
    - Filter by various criteria
    """
    print("\n" + "="*60)
    print("DEMO: Client Query Operations")
    print("="*60)
    
    # 1. Tree view
    print("\n1. Tree view of all prefixes:")
    prefix_manager.print_tree_view()
    
    # 2. Query specific prefix
    print("\n2. Querying specific prefix 10.0.1.0/24:")
    specific_prefix = prefix_manager.query_prefix_by_cidr('prod-vrf', '10.0.1.0/24')
    if specific_prefix:
        print(f"   Found: {specific_prefix.prefix_id}")
        print(f"   CIDR: {specific_prefix.cidr}")
        print(f"   Routable: {specific_prefix.routable}")
        print(f"   Source: {specific_prefix.source}")
        print(f"   Tags: {specific_prefix.tags}")
    else:
        print("   Not found")
    
    # 3. List children of a prefix
    print("\n3. Children of 10.0.0.0/12:")
    children = prefix_manager.get_children_prefixes('manual-prod-vrf-10-0-0-0-12')
    for child in children:
        print(f"   - {child.cidr} ({child.prefix_id}) - Routable: {child.routable}")
    
    # 4. Filter by routable flag
    print("\n4. All routable prefixes:")
    routable_prefixes = prefix_manager.filter_prefixes(routable=True)
    for prefix in routable_prefixes[:5]:  # Show first 5
        print(f"   - {prefix.cidr} (VRF: {prefix.vrf_id}) - {prefix.source}")
    
    # 5. Filter by source
    print("\n5. All VPC-sourced prefixes:")
    vpc_prefixes = prefix_manager.filter_prefixes(source='vpc')
    for prefix in vpc_prefixes:
        print(f"   - {prefix.cidr} (VPC: {prefix.vpc_id}) - Tags: {prefix.tags}")
    
    # 6. Filter by cloud provider
    print("\n6. All AWS prefixes:")
    aws_prefixes = prefix_manager.filter_prefixes(provider='aws')
    for prefix in aws_prefixes:
        print(f"   - {prefix.cidr} (Source: {prefix.source})")

def load_public_ips_from_json(prefix_manager: PrefixManager, data_loader: JSONDataLoader, vpcs_lookup: dict):
    """
    Load public IP addresses from JSON configuration
    """
    print("\n" + "="*60)
    print("LOADING: Public IP Addresses from JSON")
    print("="*60)
    
    try:
        # Load VPC-associated public IPs
        vpc_data = data_loader.load_vpc_data()
        
        print(f"\n1. Loading {len(vpc_data['public_ips'])} VPC-associated public IPs...")
        
        for ip_config in vpc_data['public_ips']:
            data_loader.validate_public_ip(ip_config)
            
            vpc_provider_id = ip_config['vpc_provider_vpc_id']
            if vpc_provider_id not in vpcs_lookup:
                print(f"   ⚠️  Skipping public IP {ip_config['cidr']} - VPC {vpc_provider_id} not found")
                continue
            
            vpc = vpcs_lookup[vpc_provider_id]
            tags = ip_config.get('tags', {})
            tags['vpc_id'] = str(vpc.vpc_id)  # Add VPC ID to tags
            
            print(f"   Creating public IP: {ip_config['cidr']} for VPC {vpc_provider_id}")
            
            public_ip_prefix = safe_create_public_ip(
                prefix_manager,
                vpc_id=vpc.vpc_id,
                cidr=ip_config['cidr'],
                tags=tags
            )
            print(f"      ✓ Created: {public_ip_prefix.prefix_id}")
        
        # Load standalone public IPs
        standalone_ips = data_loader.load_public_ip_data()
        if standalone_ips:
            print(f"\n2. Loading {len(standalone_ips)} standalone public IPs...")
            
            for ip_config in standalone_ips:
                data_loader.validate_public_ip(ip_config)
                
                print(f"   Creating standalone public IP: {ip_config['cidr']}")
                
                public_ip_prefix = safe_create_standalone_public_ip(
                    prefix_manager,
                    cidr=ip_config['cidr'],
                    tags=ip_config.get('tags', {})
                )
                print(f"      ✓ Created: {public_ip_prefix.prefix_id}")
        
        print(f"\n✅ Successfully loaded public IP addresses")
        
    except Exception as e:
        print(f"❌ Error loading public IPs: {e}")
        raise

def demo_space_analysis(prefix_manager: PrefixManager):
    """
    Demonstrate space analysis within parent prefixes
    """
    print("\n" + "="*60)
    print("DEMO: Space Analysis")
    print("="*60)
    
    print("\n1. Analyzing space usage in 10.0.0.0/12:")
    parent_prefix_id = 'manual-prod-vrf-10-0-0-0-12'
    children = prefix_manager.get_children_prefixes(parent_prefix_id)
    
    print(f"   Parent: 10.0.0.0/12")
    print(f"   Allocated children:")
    for child in children:
        print(f"     - {child.cidr} ({'Routable' if child.routable else 'Non-routable'})")
    
    print(f"   Total children: {len(children)}")
    print("   Note: Remaining space calculation would be done by application logic")
    
    print("\n2. Analyzing public IP addresses in public-vrf:")
    public_prefixes = prefix_manager.filter_prefixes(vrf_id='public-vrf')
    print(f"   Total public IP addresses: {len(public_prefixes)}")
    for prefix in public_prefixes:
        service = prefix.tags.get('service', 'unknown')
        name = prefix.tags.get('Name', 'unnamed')
        print(f"     - {prefix.cidr} ({name}) - Service: {service}")

def is_aws_vpc_record(notes_field: str) -> bool:
    """
    Check if a Device42 Notes field contains AWS VPC metadata.
    AWS VPC records can have Notes in two formats:
    1. List format: [{'Key': 'subnet-creator', 'Value': '...'}, {'Key': 'SubnetId', 'Value': '...'}, ...]
    2. Dict format: {'account': '...', 'environment': '...', 'customer': '...', 'subnet-type': '...'}
    
    Args:
        notes_field: The Notes field from Device42 CSV
        
    Returns:
        True if this appears to be an AWS VPC record, False otherwise
    """
    if not notes_field or notes_field == 'None' or notes_field.strip() == '':
        return False
    
    try:
        # Try to parse as Python literal (dict or list)
        parsed = ast.literal_eval(notes_field)
        
        if isinstance(parsed, list):
            # Check if it's a list of Key-Value dictionaries (AWS VPC format)
            aws_vpc_keys = {'SubnetId', 'VpcId', 'subnet-creator', 'region', 'az_id'}
            eip_keys = {'eip-allowlist', 'eip-type', 'service_uuid'}
            found_keys = set()
            service_name_value = None
            
            for item in parsed:
                if isinstance(item, dict) and 'Key' in item and 'Value' in item:
                    key = item['Key']
                    value = item['Value']
                    found_keys.add(key)
                    
                    # If we find AWS VPC-specific keys, it's an AWS VPC record
                    if key in aws_vpc_keys:
                        return True
                    
                    # Track service_name value for EIP detection
                    if key == 'service_name':
                        service_name_value = str(value).lower()
            
            # Check for EIP records: has eip-related keys or service_uuid with cloud network service
            if any(key in found_keys for key in eip_keys):
                return True
            if 'service_uuid' in found_keys and service_name_value and 'cloud network' in service_name_value:
                return True
        
        elif isinstance(parsed, dict):
            # Check if it's a dictionary with AWS VPC metadata keys
            # AWS VPC records in dict format can have various AWS-related keys:
            # - account + subnet-type (original format)
            # - aws:cloudformation:* keys (CloudFormation resources)
            # - environment + service_name + resource_owner (AWS managed resources)
            dict_keys = set(parsed.keys())
            
            # Check for account + subnet-type pattern
            if 'account' in dict_keys and 'subnet-type' in dict_keys:
                return True
            
            # Check for AWS CloudFormation keys (any key starting with 'aws:' or containing 'cloudformation')
            aws_cloudformation_indicators = ['aws:', 'cloudformation', 'stack']
            for key in dict_keys:
                key_lower = str(key).lower()
                if any(indicator in key_lower for indicator in aws_cloudformation_indicators):
                    return True
            
            # Check for AWS managed resource pattern (environment + service_name + resource_owner)
            aws_managed_indicators = {'environment', 'service_name', 'resource_owner', 'business_unit'}
            if len(aws_managed_indicators.intersection(dict_keys)) >= 3:
                return True
        
    except (ValueError, SyntaxError):
        # If parsing fails, try JSON parsing
        try:
            parsed = json.loads(notes_field)
            if isinstance(parsed, list):
                aws_vpc_keys = {'SubnetId', 'VpcId', 'subnet-creator', 'region', 'az_id'}
                eip_keys = {'eip-allowlist', 'eip-type', 'service_uuid'}
                found_keys = set()
                service_name_value = None
                
                for item in parsed:
                    if isinstance(item, dict) and 'Key' in item and 'Value' in item:
                        key = item['Key']
                        value = item['Value']
                        found_keys.add(key)
                        
                        if key in aws_vpc_keys:
                            return True
                        
                        if key == 'service_name':
                            service_name_value = str(value).lower()
                
                # Check for EIP records
                if any(key in found_keys for key in eip_keys):
                    return True
                if 'service_uuid' in found_keys and service_name_value and 'cloud network' in service_name_value:
                    return True
            elif isinstance(parsed, dict):
                # Check if it's a dictionary with AWS VPC metadata keys
                dict_keys = set(parsed.keys())
                
                # Check for account + subnet-type pattern
                if 'account' in dict_keys and 'subnet-type' in dict_keys:
                    return True
                
                # Check for AWS CloudFormation keys
                aws_cloudformation_indicators = ['aws:', 'cloudformation', 'stack']
                for key in dict_keys:
                    key_lower = str(key).lower()
                    if any(indicator in key_lower for indicator in aws_cloudformation_indicators):
                        return True
                
                # Check for AWS managed resource pattern
                aws_managed_indicators = {'environment', 'service_name', 'resource_owner', 'business_unit'}
                if len(aws_managed_indicators.intersection(dict_keys)) >= 3:
                    return True
        except (json.JSONDecodeError, ValueError):
            pass
    
    return False

def parse_device42_tags(notes_field: str) -> dict:
    """
    Parse tags from Device42 Notes field.
    Handles both formats:
    1. Dictionary format: "{'key': 'value', ...}"
    2. List of Key-Value dicts: "[{'Key': 'key', 'Value': 'value'}, ...]"
    """
    if not notes_field or notes_field == 'None' or notes_field.strip() == '':
        return {}
    
    tags = {}
    
    try:
        # Try to parse as Python literal (dict or list)
        parsed = ast.literal_eval(notes_field)
        
        if isinstance(parsed, dict):
            # Direct dictionary format
            tags = parsed
        elif isinstance(parsed, list):
            # List of Key-Value dictionaries
            for item in parsed:
                if isinstance(item, dict) and 'Key' in item and 'Value' in item:
                    tags[item['Key']] = item['Value']
        
    except (ValueError, SyntaxError) as e:
        # If parsing fails, try JSON parsing
        try:
            parsed = json.loads(notes_field)
            if isinstance(parsed, dict):
                tags = parsed
            elif isinstance(parsed, list):
                for item in parsed:
                    if isinstance(item, dict) and 'Key' in item and 'Value' in item:
                        tags[item['Key']] = item['Value']
        except (json.JSONDecodeError, ValueError):
            # If both fail, return empty tags
            print(f"   ⚠️  Warning: Could not parse tags from Notes field: {notes_field[:50]}...")
            return {}
    
    return tags

def ensure_device42_vrf(prefix_manager: PrefixManager, vrf_name: str) -> str:
    """
    Ensure Device42 VRF exists. Adds 'd42-' prefix to avoid conflicts.
    If vrf_name is empty or None, creates a default Device42 VRF.
    """
    if not vrf_name or vrf_name.strip() == '' or vrf_name == 'None':
        vrf_id = 'd42-default-vrf'
        description = 'Default VRF for Device42 imported subnets'
    else:
        # Sanitize VRF name and add prefix
        sanitized_name = vrf_name.strip().replace(' ', '-').lower()
        vrf_id = f'd42-{sanitized_name}'
        description = f'Device42 VRF: {vrf_name}'
    
    with prefix_manager.db_manager.get_session() as session:
        # Check if VRF already exists
        existing_vrf = session.query(VRF).filter(VRF.vrf_id == vrf_id).first()
        if existing_vrf:
            return vrf_id
        
        # Create new VRF
        vrf = VRF(
            vrf_id=vrf_id,
            description=description,
            tags={'source': 'device42', 'original_name': vrf_name},
            is_default=False,
            routable_flag=True  # Default to routable, can be adjusted per prefix
        )
        
        session.add(vrf)
        session.commit()
        print(f"   ✓ Created VRF: {vrf_id}")
        return vrf_id

def load_device42_subnets_from_csv(prefix_manager: PrefixManager, csv_file: str = "data/device42_subnet.csv", limit: Optional[int] = None):
    """
    Load Device42 subnet data from CSV file.
    
    Args:
        prefix_manager: PrefixManager instance
        csv_file: Path to Device42 CSV file
        limit: Number of records to process (None for all records)
    """
    print("\n" + "="*60)
    print("LOADING: Device42 Subnets from CSV")
    print("="*60)
    
    csv_path = Path(csv_file)
    
    # If the specified file doesn't exist or is too small (only header), try subnet.csv as fallback
    if not csv_path.exists() or (csv_path.exists() and csv_path.stat().st_size < 1000):
        fallback_path = Path("data/subnet.csv")
        if fallback_path.exists() and fallback_path.stat().st_size > 1000:
            print(f"⚠️  {csv_file} not found or empty, using fallback: {fallback_path}")
            csv_path = fallback_path
        else:
            if not csv_path.exists():
                print(f"❌ Device42 CSV file not found: {csv_path}")
            else:
                print(f"⚠️  {csv_file} appears to be empty (only header)")
            if not fallback_path.exists() or fallback_path.stat().st_size < 1000:
                print(f"❌ Fallback file {fallback_path} also not found or empty")
                return
    
    print(f"📄 Using CSV file: {csv_path}")
    
    try:
        created_prefixes = {}
        vrf_cache = {}  # Cache VRF IDs to avoid repeated lookups
        
        if limit:
            print(f"\nReading Device42 subnet CSV (processing first {limit} records)...")
        else:
            print(f"\nReading Device42 subnet CSV (processing all records)...")
        
        # First pass: collect all valid records
        records_to_process = []
        record_count = 0
        skipped_count = 0
        aws_vpc_filtered_count = 0
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if limit and record_count >= limit:
                    break
                
                record_count += 1
                
                # Extract subnet information
                network = row.get('Network', '').strip()
                mask_bits = row.get('Mask_Bits', '').strip()
                vrf_group = row.get('VRF_Group', '').strip()
                notes = row.get('Notes', '').strip()
                name = row.get('Name', '').strip()
                description = row.get('Description', '').strip()
                
                # Filter out AWS VPC records (they will be loaded from VPC sync instead)
                if is_aws_vpc_record(notes):
                    aws_vpc_filtered_count += 1
                    if record_count <= 10 or record_count % 1000 == 0:  # Show first 10 and every 1000th
                        print(f"   ⏭️  Filtering AWS VPC record #{record_count}: {network}/{mask_bits}")
                    continue
                
                # Skip if network or mask_bits is missing
                if not network or not mask_bits or network == 'None' or mask_bits == 'None':
                    skipped_count += 1
                    if record_count <= 10 or record_count % 100 == 0:  # Show first 10 and every 100th
                        print(f"   ⚠️  Skipping record #{record_count}: Missing network or mask_bits")
                    continue
                
                # Construct CIDR and validate
                try:
                    cidr = f"{network}/{mask_bits}"
                    # Validate CIDR format
                    ip_network = ipaddress.ip_network(cidr, strict=False)
                    mask_length = ip_network.prefixlen
                except (ValueError, ipaddress.AddressValueError) as e:
                    skipped_count += 1
                    if record_count <= 10 or record_count % 100 == 0:  # Show first 10 and every 100th
                        print(f"   ⚠️  Skipping record #{record_count}: Invalid CIDR {cidr}: {e}")
                    continue
                
                # Store record for processing (with mask length for sorting)
                records_to_process.append({
                    'row': row,
                    'cidr': cidr,
                    'network': network,
                    'mask_bits': mask_bits,
                    'mask_length': mask_length,
                    'vrf_group': vrf_group,
                    'notes': notes,
                    'name': name,
                    'description': description
                })
        
        # Sort records by mask length (ascending) so parent CIDRs (shorter masks) load before children (longer masks)
        # Also sort by network address for consistent ordering within same mask length
        print(f"\n📊 Collected {len(records_to_process)} records to process")
        print(f"   Sorting by mask length (parents first)...")
        records_to_process.sort(key=lambda r: (r['mask_length'], str(ipaddress.ip_network(r['cidr'], strict=False).network_address)))
        
        # Second pass: process sorted records
        processed_count = 0
        for record_data in records_to_process:
            processed_count += 1
            row = record_data['row']
            cidr = record_data['cidr']
            vrf_group = record_data['vrf_group']
            notes = record_data['notes']
            name = record_data['name']
            description = record_data['description']
            
            # Ensure VRF exists
            if vrf_group not in vrf_cache:
                vrf_id = ensure_device42_vrf(prefix_manager, vrf_group)
                vrf_cache[vrf_group] = vrf_id
            else:
                vrf_id = vrf_cache[vrf_group]
            
            # Parse tags from Notes field
            tags = parse_device42_tags(notes)
            
            # Add additional metadata
            tags['source'] = 'device42'
            tags['device42_id'] = row.get('id', '')
            if name:
                tags['Name'] = name
            if description:
                tags['description'] = description
            
            # Create prefix
            try:
                if processed_count <= 10 or processed_count % 100 == 0:  # Show progress for first 10 and every 100th
                    print(f"   Processing record #{processed_count}/{len(records_to_process)}: {cidr} (/{record_data['mask_length']}) in VRF {vrf_id}")
                
                prefix = safe_create_prefix(
                    prefix_manager,
                    vrf_id=vrf_id,
                    cidr=cidr,
                    parent_prefix_id=None,  # No parent for Device42 subnets initially
                    tags=tags,
                    routable=True,  # Default to routable
                    vpc_children_type_flag=False
                )
                
                created_prefixes[cidr] = prefix
                if processed_count <= 10 or processed_count % 100 == 0:  # Show progress
                    print(f"      ✓ Created: {prefix.prefix_id}")
                
            except Exception as e:
                skipped_count += 1
                if "already exists" in str(e) or "duplicate key" in str(e):
                    if processed_count <= 10 or processed_count % 100 == 0:
                        print(f"      ⚠️  Prefix {cidr} already exists, skipping")
                else:
                    print(f"      ❌ Error creating prefix {cidr}: {e}")
                    raise
        
        print(f"\n✅ Successfully processed {record_count} records")
        print(f"   ✓ Created: {len(created_prefixes)} Device42 subnets")
        print(f"   ⏭️  Filtered AWS VPC records: {aws_vpc_filtered_count} (will be loaded from VPC sync)")
        if skipped_count > 0:
            print(f"   ⚠️  Skipped: {skipped_count} records (missing data or duplicates)")
        print(f"\n📊 Summary:")
        print(f"   Total records in CSV: {record_count}")
        print(f"   AWS VPC records filtered: {aws_vpc_filtered_count} ({aws_vpc_filtered_count*100/max(record_count,1):.1f}%)")
        print(f"   Manual records to load: {record_count - aws_vpc_filtered_count - skipped_count}")
        print(f"   Actually loaded: {len(created_prefixes)}")
        return created_prefixes
        
    except Exception as e:
        print(f"❌ Error loading Device42 subnets: {e}")
        import traceback
        traceback.print_exc()
        raise

def demo_ipv6_support(prefix_manager: PrefixManager):
    """
    Demonstrate IPv6 support functionality
    """
    print("\n" + "="*60)
    print("DEMO: IPv6 Support")
    print("="*60)
    
    # Query IPv6 prefixes
    print("\n1. Querying IPv6 prefixes:")
    all_prefixes = prefix_manager.filter_prefixes(vrf_id='prod-vrf')
    ipv6_prefixes = [p for p in all_prefixes if ':' in str(p.cidr)]
    
    if ipv6_prefixes:
        print(f"   Found {len(ipv6_prefixes)} IPv6 prefixes:")
        for prefix in ipv6_prefixes:
            ip_version = prefix.tags.get('ip_version', '6')
            print(f"     - {prefix.cidr} (IPv{ip_version}) - {prefix.prefix_id}")
            print(f"       Tags: {prefix.tags}")
    else:
        print("   No IPv6 prefixes found")
    
    # Test IPv6 subnet allocation
    print("\n2. Testing IPv6 subnet allocation:")
    ipv6_parent = prefix_manager.query_prefix_by_cidr('prod-vrf', '2001:db8::/32')
    if ipv6_parent:
        print(f"   Parent prefix: {ipv6_parent.cidr}")
        try:
            # Calculate available /48 subnets
            available_subnets = prefix_manager.calculate_available_subnets(ipv6_parent, 48)
            print(f"   Available /48 subnets: {len(available_subnets)}")
            if available_subnets:
                print(f"   Example available subnet: {available_subnets[0]}")
        except Exception as e:
            print(f"   Error calculating IPv6 subnets: {e}")
    else:
        print("   IPv6 parent prefix not found")
    
    # Show IPv6 public IPs
    print("\n3. IPv6 Public IP addresses:")
    public_prefixes = prefix_manager.filter_prefixes(vrf_id='public-vrf')
    ipv6_public_ips = [p for p in public_prefixes if ':' in str(p.cidr)]
    if ipv6_public_ips:
        print(f"   Found {len(ipv6_public_ips)} IPv6 public IPs:")
        for prefix in ipv6_public_ips:
            name = prefix.tags.get('Name', 'unnamed')
            print(f"     - {prefix.cidr} ({name})")
    else:
        print("   No IPv6 public IPs found")

def main():
    """Main demo function implementing all user stories with JSON configuration"""
    print("🚀 Starting Prefix Management System with JSON Configuration")
    print("=" * 60)
    
    # Initialize database connection
    database_url = os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management')
    print(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    
    db_manager = DatabaseManager(database_url)
    
    # Wait for database to be ready
    wait_for_db(db_manager)
    
    # Initialize prefix manager and JSON data loader
    prefix_manager = PrefixManager(db_manager)
    data_loader = JSONDataLoader(data_dir='data')
    
    try:
        # Load configuration from JSON files
        print("\n📄 Loading configuration from JSON files...")
        
        # Step 1: Load manual prefixes
        created_prefixes = load_manual_prefixes_from_json(prefix_manager, data_loader)
        
        # Step 2: Load VPCs and associations
        created_vpcs = load_vpc_data_from_json(prefix_manager, data_loader)
        
        # Step 3: Load VPC subnets
        load_vpc_subnets_from_json(prefix_manager, data_loader, created_vpcs)
        
        # Step 4: Load public IP addresses
        load_public_ips_from_json(prefix_manager, data_loader, created_vpcs)
        
        # Step 5: Load Device42 subnets (all records)
        load_device42_subnets_from_csv(prefix_manager, csv_file="data/device42_subnet.csv", limit=None)
        
        # Step 6: Run demonstration queries (using VPCs by provider ID for compatibility)
        vpc1 = created_vpcs.get('vpc-0abc1234')
        vpc2 = created_vpcs.get('vpc-0def5678')
        
        if vpc1 and vpc2:
            demo_user_story_client_queries(prefix_manager, vpc1, vpc2)
            demo_space_analysis(prefix_manager)
        else:
            print("⚠️  Skipping client queries demo - VPCs not found")
        
        # Step 7: Demonstrate IPv6 support
        demo_ipv6_support(prefix_manager)
        
        print("\n" + "="*60)
        print("✅ JSON Configuration Loading completed successfully!")
        print("="*60)
        
        # Final tree view
        print("\n🌳 Final Prefix Tree:")
        prefix_manager.print_tree_view('prod-vrf')
        
        print("\n🌐 Public IP Addresses:")
        prefix_manager.print_tree_view('public-vrf')
        
    except Exception as e:
        print(f"\n❌ Configuration loading failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
