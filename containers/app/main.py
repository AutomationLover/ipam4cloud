#!/usr/bin/env python3
"""
Prefix Management System Demo
Implements the user stories from the database design document.
"""

import os
import time
import uuid
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

def safe_create_prefix(prefix_manager: PrefixManager, **kwargs):
    """Create prefix with duplicate handling"""
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
        
        # Step 5: Run demonstration queries (using VPCs by provider ID for compatibility)
        vpc1 = created_vpcs.get('vpc-0abc1234')
        vpc2 = created_vpcs.get('vpc-0def5678')
        
        if vpc1 and vpc2:
            demo_user_story_client_queries(prefix_manager, vpc1, vpc2)
            demo_space_analysis(prefix_manager)
        else:
            print("⚠️  Skipping client queries demo - VPCs not found")
        
        # Step 6: Demonstrate IPv6 support
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
