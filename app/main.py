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

def demo_user_story_manual_planning(prefix_manager: PrefixManager):
    """
    User Story: Engineer does prefix planning
    - Create 10.0.0.0/8 as root prefix for prod-vrf
    - Create 10.0.0.0/12 as prod environment reservation
    - Create VPCs and associate with prefixes
    """
    print("\n" + "="*60)
    print("DEMO: Manual Prefix Planning")
    print("="*60)
    
    # Step 1: Create root prefix 10.0.0.0/8 (or get existing)
    print("\n1. Creating root prefix 10.0.0.0/8 for prod-vrf...")
    root_prefix = safe_create_prefix(
        prefix_manager,
        vrf_id='prod-vrf',
        cidr='10.0.0.0/8',
        tags={'env': 'prod', 'managed_by': 'engineer'},
        routable=True
    )
    print(f"   ✓ Ready: {root_prefix.prefix_id}")
    
    # Step 2: Create 10.0.0.0/12 for prod environment (or get existing)
    print("\n2. Creating 10.0.0.0/12 reservation for prod environment...")
    prod_prefix = safe_create_prefix(
        prefix_manager,
        vrf_id='prod-vrf',
        cidr='10.0.0.0/12',
        parent_prefix_id=root_prefix.prefix_id,
        tags={'env': 'prod', 'purpose': 'prod_reservation'},
        routable=True
    )
    print(f"   ✓ Ready: {prod_prefix.prefix_id}")
    
    # Step 3: Create AWS VPC (or get existing)
    print("\n3. Creating AWS VPC for prod environment...")
    vpc1 = safe_create_vpc(
        prefix_manager,
        description='Production Application VPC',
        provider='aws',
        provider_account_id='123456789012',
        provider_vpc_id='vpc-0abc1234',
        region='us-east-1',
        tags={'owner': 'netops', 'env': 'prod'}
    )
    print(f"   ✓ Ready VPC: {vpc1.vpc_id}")
    
    # Step 4: Reserve 10.0.0.0/16 for this VPC (routable)
    print("\n4. Reserving 10.0.0.0/16 for VPC (routable)...")
    vpc_prefix_routable = safe_create_prefix(
        prefix_manager,
        vrf_id='prod-vrf',
        cidr='10.0.0.0/16',
        parent_prefix_id=prod_prefix.prefix_id,
        tags={'vpc_id': str(vpc1.vpc_id), 'purpose': 'vpc_reservation'},
        routable=True,
        vpc_children_type_flag=True
    )
    print(f"   ✓ Ready: {vpc_prefix_routable.prefix_id}")
    
    # Step 5: Associate VPC with the routable prefix
    print("\n5. Associating VPC with routable prefix...")
    association1 = safe_associate_vpc(
        prefix_manager,
        vpc_id=vpc1.vpc_id,
        vpc_prefix_cidr='10.0.0.0/16',
        routable=True,
        parent_prefix_id=vpc_prefix_routable.prefix_id
    )
    print(f"   ✓ Ready association: {association1.association_id}")
    
    # Step 6: Create another VPC for non-routable prefix
    print("\n6. Creating second VPC for non-routable prefix...")
    vpc2 = safe_create_vpc(
        prefix_manager,
        description='Development/Test VPC',
        provider='aws',
        provider_account_id='123456789012',
        provider_vpc_id='vpc-0def5678',
        region='us-east-1',
        tags={'owner': 'devops', 'env': 'dev'}
    )
    print(f"   ✓ Ready VPC: {vpc2.vpc_id}")
    
    # Step 7: Reserve 10.1.0.0/16 for non-routable VPC
    print("\n7. Reserving 10.1.0.0/16 for VPC (non-routable)...")
    vpc_prefix_nonroutable = safe_create_prefix(
        prefix_manager,
        vrf_id='prod-vrf',
        cidr='10.1.0.0/16',
        parent_prefix_id=prod_prefix.prefix_id,
        tags={'vpc_id': str(vpc2.vpc_id), 'purpose': 'vpc_reservation'},
        routable=False,
        vpc_children_type_flag=True
    )
    print(f"   ✓ Ready: {vpc_prefix_nonroutable.prefix_id}")
    
    # Step 8: Associate VPC with the non-routable prefix
    print("\n8. Associating VPC with non-routable prefix...")
    association2 = safe_associate_vpc(
        prefix_manager,
        vpc_id=vpc2.vpc_id,
        vpc_prefix_cidr='10.1.0.0/16',
        routable=False,
        parent_prefix_id=vpc_prefix_nonroutable.prefix_id
    )
    print(f"   ✓ Ready association: {association2.association_id}")
    
    return vpc1, vpc2

def demo_user_story_auto_ingestion(prefix_manager: PrefixManager, vpc1: VPC, vpc2: VPC):
    """
    User Story: Auto script ingestion
    - Simulate hourly cron job fetching VPC subnets
    - Insert subnet prefixes with proper inheritance
    """
    print("\n" + "="*60)
    print("DEMO: Auto Script Ingestion (Simulated)")
    print("="*60)
    
    print("\n1. Simulating auto discovery of subnets in routable VPC...")
    
    # Routable VPC subnets - should inherit prod-vrf and be routable
    routable_subnets = [
        ('10.0.1.0/24', {'Name': 'prod-app-subnet-1a', 'AZ': 'us-east-1a'}),
        ('10.0.2.0/24', {'Name': 'prod-app-subnet-1b', 'AZ': 'us-east-1b'}),
        ('10.0.10.0/24', {'Name': 'prod-db-subnet-1a', 'AZ': 'us-east-1a'}),
    ]
    
    for subnet_cidr, tags in routable_subnets:
        print(f"   Ingesting subnet: {subnet_cidr}")
        prefix_id = prefix_manager.upsert_vpc_subnet(vpc1.vpc_id, subnet_cidr, tags)
        print(f"   ✓ Created: {prefix_id}")
    
    print("\n2. Simulating auto discovery of subnets in non-routable VPC...")
    
    # Non-routable VPC subnets - should get their own VRF and be non-routable
    nonroutable_subnets = [
        ('10.1.1.0/24', {'Name': 'dev-app-subnet-1a', 'AZ': 'us-east-1a'}),
        ('10.1.2.0/24', {'Name': 'dev-test-subnet-1b', 'AZ': 'us-east-1b'}),
    ]
    
    for subnet_cidr, tags in nonroutable_subnets:
        print(f"   Ingesting subnet: {subnet_cidr}")
        prefix_id = prefix_manager.upsert_vpc_subnet(vpc2.vpc_id, subnet_cidr, tags)
        print(f"   ✓ Created: {prefix_id}")

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

def demo_public_ip_addresses(prefix_manager: PrefixManager, vpc1: VPC, vpc2: VPC):
    """
    Demo: Create public IP addresses for VPCs
    - Create public IP addresses as /32 prefixes in public-vrf
    - Associate them with VPCs using the vpc-subnet-prefix format
    """
    print("\n" + "="*60)
    print("DEMO: Public IP Address Management")
    print("="*60)
    
    # Public IP addresses for VPC1 (Production VPC)
    print("\n1. Creating public IP addresses for Production VPC...")
    vpc1_public_ips = [
        {
            'ip': '52.23.45.67/32',
            'tags': {
                'Name': 'prod-app-lb-ip',
                'service': 'load-balancer',
                'env': 'prod',
                'vpc_id': str(vpc1.vpc_id)
            }
        },
        {
            'ip': '54.123.78.90/32', 
            'tags': {
                'Name': 'prod-nat-gateway-ip',
                'service': 'nat-gateway',
                'env': 'prod',
                'vpc_id': str(vpc1.vpc_id)
            }
        },
        {
            'ip': '3.45.67.89/32',
            'tags': {
                'Name': 'prod-api-gateway-ip',
                'service': 'api-gateway', 
                'env': 'prod',
                'vpc_id': str(vpc1.vpc_id)
            }
        }
    ]
    
    for ip_data in vpc1_public_ips:
        print(f"   Creating public IP: {ip_data['ip']}")
        
        public_ip_prefix = safe_create_public_ip(
            prefix_manager,
            vpc_id=vpc1.vpc_id,
            cidr=ip_data['ip'],
            tags=ip_data['tags']
        )
        print(f"   ✓ Created: {public_ip_prefix.prefix_id}")
    
    # Public IP addresses for VPC2 (Development VPC)  
    print("\n2. Creating public IP addresses for Development VPC...")
    vpc2_public_ips = [
        {
            'ip': '18.45.123.45/32',
            'tags': {
                'Name': 'dev-test-lb-ip',
                'service': 'load-balancer',
                'env': 'dev',
                'vpc_id': str(vpc2.vpc_id)
            }
        },
        {
            'ip': '34.67.89.12/32',
            'tags': {
                'Name': 'dev-nat-gateway-ip', 
                'service': 'nat-gateway',
                'env': 'dev',
                'vpc_id': str(vpc2.vpc_id)
            }
        }
    ]
    
    for ip_data in vpc2_public_ips:
        print(f"   Creating public IP: {ip_data['ip']}")
        
        public_ip_prefix = safe_create_public_ip(
            prefix_manager,
            vpc_id=vpc2.vpc_id,
            cidr=ip_data['ip'],
            tags=ip_data['tags']
        )
        print(f"   ✓ Created: {public_ip_prefix.prefix_id}")
    
    # Additional standalone public IPs (not tied to specific VPCs)
    print("\n3. Creating standalone public IP addresses...")
    standalone_public_ips = [
        {
            'ip': '203.0.113.10/32',
            'tags': {
                'Name': 'company-website-ip',
                'service': 'website',
                'owner': 'marketing'
            }
        },
        {
            'ip': '198.51.100.25/32',
            'tags': {
                'Name': 'backup-service-ip',
                'service': 'backup',
                'owner': 'ops'
            }
        }
    ]
    
    for ip_data in standalone_public_ips:
        print(f"   Creating standalone public IP: {ip_data['ip']}")
        
        public_ip_prefix = safe_create_standalone_public_ip(
            prefix_manager,
            cidr=ip_data['ip'],
            tags=ip_data['tags']
        )
        print(f"   ✓ Created: {public_ip_prefix.prefix_id}")

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

def main():
    """Main demo function implementing all user stories"""
    print("🚀 Starting Prefix Management System Demo")
    print("=" * 60)
    
    # Initialize database connection
    database_url = os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management')
    print(f"Connecting to database: {database_url.split('@')[1] if '@' in database_url else database_url}")
    
    db_manager = DatabaseManager(database_url)
    
    # Wait for database to be ready
    wait_for_db(db_manager)
    
    # Initialize prefix manager
    prefix_manager = PrefixManager(db_manager)
    
    try:
        # Run user story demos
        vpc1, vpc2 = demo_user_story_manual_planning(prefix_manager)
        demo_user_story_auto_ingestion(prefix_manager, vpc1, vpc2)
        demo_public_ip_addresses(prefix_manager, vpc1, vpc2)
        demo_user_story_client_queries(prefix_manager, vpc1, vpc2)
        demo_space_analysis(prefix_manager)
        
        print("\n" + "="*60)
        print("✅ Demo completed successfully!")
        print("="*60)
        
        # Final tree view
        print("\n🌳 Final Prefix Tree:")
        prefix_manager.print_tree_view('prod-vrf')
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
