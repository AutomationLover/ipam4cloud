#!/usr/bin/env python3
"""
Test script to validate JSON data loading functionality
Tests the JSON loader without requiring database connection
"""

import sys
import os
from pathlib import Path

# Add current directory to path so we can import json_loader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from json_loader import JSONDataLoader

def test_json_data_loading():
    """Test the JSON data loading functionality"""
    print("🧪 Testing JSON Data Loader")
    print("=" * 50)
    
    try:
        # Initialize data loader
        data_loader = JSONDataLoader(data_dir='data')
        
        # Test 1: Load manual prefixes
        print("\n1. Testing manual prefixes loading...")
        manual_prefixes = data_loader.load_manual_prefixes()
        print(f"   ✓ Loaded {len(manual_prefixes)} manual prefixes")
        
        # Validate each prefix
        for i, prefix_data in enumerate(manual_prefixes):
            try:
                data_loader.validate_manual_prefix(prefix_data)
                print(f"   ✓ Prefix {i+1}: {prefix_data['cidr']} - valid")
            except Exception as e:
                print(f"   ❌ Prefix {i+1}: {prefix_data.get('cidr', 'unknown')} - {e}")
        
        # Test 2: Load VPC data
        print("\n2. Testing VPC data loading...")
        vpc_data = data_loader.load_vpc_data()
        print(f"   ✓ Loaded VPC data with {len(vpc_data['vpcs'])} VPCs")
        print(f"   ✓ Loaded {len(vpc_data['vpc_associations'])} VPC associations")
        print(f"   ✓ Loaded {len(vpc_data['vpc_subnets'])} VPC subnets")
        print(f"   ✓ Loaded {len(vpc_data['public_ips'])} VPC public IPs")
        
        # Validate VPCs
        for i, vpc_config in enumerate(vpc_data['vpcs']):
            try:
                data_loader.validate_vpc_data(vpc_config)
                print(f"   ✓ VPC {i+1}: {vpc_config['provider_vpc_id']} - valid")
            except Exception as e:
                print(f"   ❌ VPC {i+1}: {vpc_config.get('provider_vpc_id', 'unknown')} - {e}")
        
        # Validate VPC associations
        for i, assoc_config in enumerate(vpc_data['vpc_associations']):
            try:
                data_loader.validate_vpc_association(assoc_config)
                print(f"   ✓ Association {i+1}: {assoc_config['vpc_provider_vpc_id']} -> {assoc_config['vpc_prefix_cidr']} - valid")
            except Exception as e:
                print(f"   ❌ Association {i+1}: {e}")
        
        # Validate VPC subnets
        for i, subnet_config in enumerate(vpc_data['vpc_subnets']):
            try:
                data_loader.validate_vpc_subnet(subnet_config)
                print(f"   ✓ Subnet {i+1}: {subnet_config['subnet_cidr']} in {subnet_config['vpc_provider_vpc_id']} - valid")
            except Exception as e:
                print(f"   ❌ Subnet {i+1}: {e}")
        
        # Test 3: Load standalone public IPs
        print("\n3. Testing standalone public IPs loading...")
        standalone_ips = data_loader.load_public_ip_data()
        print(f"   ✓ Loaded {len(standalone_ips)} standalone public IPs")
        
        # Validate standalone IPs
        for i, ip_config in enumerate(standalone_ips):
            try:
                data_loader.validate_public_ip(ip_config)
                print(f"   ✓ Public IP {i+1}: {ip_config['cidr']} - valid")
            except Exception as e:
                print(f"   ❌ Public IP {i+1}: {e}")
        
        # Test 4: Load all data at once
        print("\n4. Testing load_all_data()...")
        all_data = data_loader.load_all_data()
        print(f"   ✓ All data loaded successfully")
        print(f"      - Manual prefixes: {len(all_data['manual_prefixes'])}")
        print(f"      - VPCs: {len(all_data['vpc_data']['vpcs'])}")
        print(f"      - Standalone public IPs: {len(all_data['standalone_public_ips'])}")
        
        print("\n" + "=" * 50)
        print("✅ All JSON data loading tests passed!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ JSON data loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def display_data_summary():
    """Display a summary of the loaded data"""
    print("\n📋 Data Summary")
    print("=" * 50)
    
    try:
        data_loader = JSONDataLoader(data_dir='data')
        
        # Manual prefixes
        manual_prefixes = data_loader.load_manual_prefixes()
        print(f"\n📁 Manual Prefixes ({len(manual_prefixes)}):")
        for prefix in manual_prefixes:
            parent = f" (parent: {prefix.get('parent_prefix_id', 'none')})" if prefix.get('parent_prefix_id') else ""
            routable = "✓" if prefix.get('routable', True) else "✗"
            print(f"   {routable} {prefix['cidr']} in {prefix['vrf_id']}{parent}")
        
        # VPC data
        vpc_data = data_loader.load_vpc_data()
        print(f"\n🏢 VPCs ({len(vpc_data['vpcs'])}):")
        for vpc in vpc_data['vpcs']:
            print(f"   {vpc['provider_vpc_id']} - {vpc['description']} ({vpc['provider']}/{vpc['region']})")
        
        print(f"\n🔗 VPC Associations ({len(vpc_data['vpc_associations'])}):")
        for assoc in vpc_data['vpc_associations']:
            routable = "✓" if assoc['routable'] else "✗"
            print(f"   {routable} {assoc['vpc_provider_vpc_id']} -> {assoc['vpc_prefix_cidr']}")
        
        print(f"\n🌐 VPC Subnets ({len(vpc_data['vpc_subnets'])}):")
        for subnet in vpc_data['vpc_subnets']:
            name = subnet.get('tags', {}).get('Name', 'unnamed')
            print(f"   {subnet['subnet_cidr']} in {subnet['vpc_provider_vpc_id']} ({name})")
        
        print(f"\n🌍 VPC Public IPs ({len(vpc_data['public_ips'])}):")
        for ip in vpc_data['public_ips']:
            name = ip.get('tags', {}).get('Name', 'unnamed')
            print(f"   {ip['cidr']} in {ip['vpc_provider_vpc_id']} ({name})")
        
        # Standalone public IPs
        standalone_ips = data_loader.load_public_ip_data()
        if standalone_ips:
            print(f"\n🔓 Standalone Public IPs ({len(standalone_ips)}):")
            for ip in standalone_ips:
                name = ip.get('tags', {}).get('Name', 'unnamed')
                print(f"   {ip['cidr']} ({name})")
        
    except Exception as e:
        print(f"❌ Error displaying data summary: {e}")

if __name__ == "__main__":
    print("🚀 Starting JSON Data Loader Tests")
    print("=" * 60)
    
    # Test if data directory exists
    data_dir = Path('data')
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir.absolute()}")
        sys.exit(1)
    
    # Run tests
    success = test_json_data_loading()
    
    if success:
        display_data_summary()
        print("\n🎉 All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Tests failed!")
        sys.exit(1)
