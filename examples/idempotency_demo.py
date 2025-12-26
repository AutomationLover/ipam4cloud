#!/usr/bin/env python3
"""
Idempotency Demo for IPAM4Cloud API

This script demonstrates how to use the idempotency features of the IPAM4Cloud API
to ensure that operations are not duplicated even if requests are retried.
"""

import requests
import uuid
import json
import time
from typing import Optional


class IPAM4CloudClient:
    """Simple client for IPAM4Cloud API with idempotency support"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def create_prefix(
        self,
        vrf_id: str,
        cidr: str,
        parent_prefix_id: Optional[str] = None,
        tags: Optional[dict] = None,
        routable: bool = True,
        request_id: Optional[str] = None
    ) -> dict:
        """
        Create a prefix with optional idempotency
        
        Args:
            vrf_id: VRF identifier
            cidr: CIDR block (e.g., "10.0.0.0/24")
            parent_prefix_id: Optional parent prefix ID
            tags: Optional tags dictionary
            routable: Whether the prefix is routable
            request_id: Optional request ID for idempotency
            
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/prefixes"
        
        payload = {
            "vrf_id": vrf_id,
            "cidr": cidr,
            "parent_prefix_id": parent_prefix_id,
            "tags": tags or {},
            "routable": routable,
            "vpc_children_type_flag": False
        }
        
        # Add request_id if provided
        if request_id:
            payload["request_id"] = request_id
        
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id
        
        response = self.session.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "data": response.json(),
                "request_id": response.headers.get("X-Request-ID"),
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "error": response.json() if response.content else {"message": "Unknown error"},
                "status_code": response.status_code
            }
    
    def allocate_subnet(
        self,
        vrf_id: str,
        subnet_size: int,
        tags: Optional[dict] = None,
        routable: bool = True,
        parent_prefix_id: Optional[str] = None,
        description: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> dict:
        """
        Allocate a subnet with optional idempotency
        
        Args:
            vrf_id: VRF identifier
            subnet_size: Subnet mask length (e.g., 24 for /24)
            tags: Optional tags for parent matching
            routable: Whether the subnet should be routable
            parent_prefix_id: Optional specific parent prefix
            description: Optional description
            request_id: Optional request ID for idempotency
            
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/prefixes/allocate-subnet"
        
        payload = {
            "vrf_id": vrf_id,
            "subnet_size": subnet_size,
            "tags": tags or {},
            "routable": routable,
            "parent_prefix_id": parent_prefix_id,
            "description": description
        }
        
        # Add request_id if provided
        if request_id:
            payload["request_id"] = request_id
        
        headers = {}
        if request_id:
            headers["X-Request-ID"] = request_id
        
        response = self.session.post(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            return {
                "success": True,
                "data": response.json(),
                "request_id": response.headers.get("X-Request-ID"),
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "error": response.json() if response.content else {"message": "Unknown error"},
                "status_code": response.status_code
            }
    
    def get_idempotency_stats(self) -> dict:
        """Get idempotency statistics"""
        url = f"{self.base_url}/api/idempotency/stats"
        response = self.session.get(url)
        return response.json()
    
    def cleanup_expired_records(self) -> dict:
        """Trigger cleanup of expired idempotency records"""
        url = f"{self.base_url}/api/idempotency/cleanup"
        response = self.session.post(url)
        return response.json()


def demo_basic_idempotency():
    """Demonstrate basic idempotency functionality"""
    print("=== Basic Idempotency Demo ===")
    
    client = IPAM4CloudClient()
    
    # Generate a request ID
    request_id = str(uuid.uuid4())
    print(f"Using request ID: {request_id}")
    
    # First request - should create new prefix
    print("\n1. Creating prefix with request ID...")
    result1 = client.create_prefix(
        vrf_id="demo-vrf",
        cidr="192.168.100.0/24",
        tags={"purpose": "demo", "env": "test"},
        request_id=request_id
    )
    
    if result1["success"]:
        print(f"   ✓ Created prefix: {result1['data']['prefix_id']}")
        print(f"   ✓ CIDR: {result1['data']['cidr']}")
        print(f"   ✓ Request ID: {result1['request_id']}")
    else:
        print(f"   ✗ Failed: {result1['error']}")
        return
    
    # Second request with same request ID and parameters - should return cached result
    print("\n2. Repeating same request (should return cached result)...")
    result2 = client.create_prefix(
        vrf_id="demo-vrf",
        cidr="192.168.100.0/24",
        tags={"purpose": "demo", "env": "test"},
        request_id=request_id
    )
    
    if result2["success"]:
        print(f"   ✓ Returned cached prefix: {result2['data']['prefix_id']}")
        print(f"   ✓ Same prefix ID: {result1['data']['prefix_id'] == result2['data']['prefix_id']}")
        print(f"   ✓ Request ID: {result2['request_id']}")
    else:
        print(f"   ✗ Failed: {result2['error']}")
    
    # Third request with same request ID but different parameters - should fail
    print("\n3. Same request ID with different parameters (should fail)...")
    result3 = client.create_prefix(
        vrf_id="demo-vrf",
        cidr="192.168.101.0/24",  # Different CIDR
        tags={"purpose": "demo", "env": "test"},
        request_id=request_id
    )
    
    if not result3["success"] and result3["status_code"] == 409:
        print(f"   ✓ Correctly rejected with conflict: {result3['error']['detail']['error']}")
    else:
        print(f"   ✗ Unexpected result: {result3}")


def demo_subnet_allocation_idempotency():
    """Demonstrate subnet allocation idempotency"""
    print("\n=== Subnet Allocation Idempotency Demo ===")
    
    client = IPAM4CloudClient()
    
    # First, create a parent prefix
    parent_request_id = str(uuid.uuid4())
    print(f"Creating parent prefix with request ID: {parent_request_id}")
    
    parent_result = client.create_prefix(
        vrf_id="demo-vrf",
        cidr="10.100.0.0/16",
        tags={"purpose": "parent", "env": "test"},
        request_id=parent_request_id
    )
    
    if not parent_result["success"]:
        print(f"Failed to create parent prefix: {parent_result['error']}")
        return
    
    parent_prefix_id = parent_result["data"]["prefix_id"]
    print(f"   ✓ Created parent prefix: {parent_prefix_id}")
    
    # Now allocate a subnet with idempotency
    allocation_request_id = str(uuid.uuid4())
    print(f"\nAllocating subnet with request ID: {allocation_request_id}")
    
    # First allocation
    result1 = client.allocate_subnet(
        vrf_id="demo-vrf",
        subnet_size=24,
        parent_prefix_id=parent_prefix_id,
        description="Demo subnet allocation",
        request_id=allocation_request_id
    )
    
    if result1["success"]:
        print(f"   ✓ Allocated subnet: {result1['data']['allocated_cidr']}")
        print(f"   ✓ Prefix ID: {result1['data']['prefix_id']}")
    else:
        print(f"   ✗ Failed: {result1['error']}")
        return
    
    # Repeat allocation with same request ID
    print("\nRepeating subnet allocation (should return same subnet)...")
    result2 = client.allocate_subnet(
        vrf_id="demo-vrf",
        subnet_size=24,
        parent_prefix_id=parent_prefix_id,
        description="Demo subnet allocation",
        request_id=allocation_request_id
    )
    
    if result2["success"]:
        print(f"   ✓ Returned same subnet: {result2['data']['allocated_cidr']}")
        print(f"   ✓ Same allocation: {result1['data']['allocated_cidr'] == result2['data']['allocated_cidr']}")
        print(f"   ✓ Same prefix ID: {result1['data']['prefix_id'] == result2['data']['prefix_id']}")
    else:
        print(f"   ✗ Failed: {result2['error']}")


def demo_auto_request_id():
    """Demonstrate automatic request ID generation"""
    print("\n=== Auto Request ID Generation Demo ===")
    
    client = IPAM4CloudClient()
    
    # Create prefix without providing request ID
    print("Creating prefix without request ID (should auto-generate)...")
    result = client.create_prefix(
        vrf_id="demo-vrf",
        cidr="172.16.0.0/24",
        tags={"purpose": "auto-id-demo"}
    )
    
    if result["success"]:
        print(f"   ✓ Created prefix: {result['data']['prefix_id']}")
        print(f"   ✓ Auto-generated request ID: {result['request_id']}")
        
        # Verify it's a valid UUID
        try:
            uuid.UUID(result['request_id'])
            print(f"   ✓ Request ID is valid UUID format")
        except ValueError:
            print(f"   ✗ Request ID is not valid UUID format")
    else:
        print(f"   ✗ Failed: {result['error']}")


def demo_idempotency_management():
    """Demonstrate idempotency management features"""
    print("\n=== Idempotency Management Demo ===")
    
    client = IPAM4CloudClient()
    
    # Get initial stats
    print("Getting idempotency statistics...")
    stats = client.get_idempotency_stats()
    if "stats" in stats:
        print(f"   Total records: {stats['stats']['total_records']}")
        print(f"   Active records: {stats['stats']['active_records']}")
        print(f"   Expired records: {stats['stats']['expired_records']}")
    
    # Create some requests to generate records
    print("\nCreating some requests to generate idempotency records...")
    for i in range(3):
        request_id = str(uuid.uuid4())
        result = client.create_prefix(
            vrf_id="demo-vrf",
            cidr=f"192.168.{200+i}.0/24",
            tags={"batch": "demo"},
            request_id=request_id
        )
        if result["success"]:
            print(f"   ✓ Created prefix {i+1}")
    
    # Get updated stats
    print("\nUpdated statistics...")
    stats = client.get_idempotency_stats()
    if "stats" in stats:
        print(f"   Total records: {stats['stats']['total_records']}")
        print(f"   Active records: {stats['stats']['active_records']}")
    
    # Cleanup expired records
    print("\nCleaning up expired records...")
    cleanup_result = client.cleanup_expired_records()
    if "deleted_count" in cleanup_result:
        print(f"   ✓ Cleaned up {cleanup_result['deleted_count']} expired records")


def main():
    """Run all demos"""
    print("IPAM4Cloud Idempotency Feature Demo")
    print("=" * 50)
    
    try:
        demo_basic_idempotency()
        demo_subnet_allocation_idempotency()
        demo_auto_request_id()
        demo_idempotency_management()
        
        print("\n" + "=" * 50)
        print("Demo completed successfully!")
        print("\nKey takeaways:")
        print("1. Use request_id for idempotent operations")
        print("2. Same request_id + same parameters = cached response")
        print("3. Same request_id + different parameters = error")
        print("4. No request_id = auto-generated UUID")
        print("5. Monitor and cleanup idempotency records as needed")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Could not connect to IPAM4Cloud API")
        print("  Make sure the backend is running on http://localhost:8000")
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")


if __name__ == "__main__":
    main()


