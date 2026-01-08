# Demo: IP Address Allocation (IPv4 Public & IPv6 Private/Public)

This demo shows how to allocate IP address blocks for IPv4 public IPs and IPv6 private/public IPs using automatic next-available allocation.

## Prerequisites

- Backend API running at `http://localhost:8000` (or your deployment URL)
- `curl` command available (or any HTTP client)
- Parent prefixes created in the IPAM system (for subnet allocation)

## Overview

This demo covers three allocation scenarios:
1. **IPv4 Public IP Allocation**: Allocate public IP blocks from a /24 parent pool
2. **IPv6 Private IP Allocation**: Allocate private IPv6 blocks (ULA range)
3. **IPv6 Public IP Allocation**: Allocate public IPv6 blocks

## Part A: IPv4 Public IP Allocation

### Step 1: Create Public VRF (if not exists)

```bash
curl -X POST "http://localhost:8000/api/vrfs" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "description": "Public IP Address VRF",
    "routable_flag": true
  }'
```

### Step 2: Create IPv4 Public IP Parent Prefix (/24)

Create a /24 parent prefix for public IP allocation (256 IPs):

```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "cidr": "198.51.100.0/24",
    "routable": true,
    "tags": {"purpose": "public-ip-pool", "ip_version": "4", "type": "public"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-public-vrf-198-51-100-0-24",
  "vrf_id": "public-vrf",
  "cidr": "198.51.100.0/24",
  ...
}
```

**Note the `prefix_id`** - you'll need it for allocation (e.g., `manual-public-vrf-198-51-100-0-24`).

**Important:** For IPv6 addresses, the `prefix_id` uses the **expanded format** (all zeros written out), not the compressed format. Always copy the exact `prefix_id` from the API response when making allocation requests.

### Step 3: Allocate First /28 Public IP Block

Allocate a /28 block (16 public IPs):

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 28,
    "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
    "routable": true,
    "description": "Public IP block for web servers"
  }'
```

**Note:** When `parent_prefix_id` is specified, tags are optional. If you include tags, they must match the parent prefix tags exactly (strict matching). For simplicity, we omit tags here since we're specifying the parent directly.

**Expected Response:**
```json
{
  "allocated_cidr": "198.51.100.0/28",
  "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
  "prefix_id": "manual-public-vrf-198-51-100-0-28",
  "available_count": 15,
  "parent_cidr": "198.51.100.0/24",
  "tags": {},
  "routable": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Key Points:**
- `allocated_cidr`: The automatically allocated CIDR (`198.51.100.0/28`)
- `available_count`: Remaining available /28 blocks (15 more)
- Each /28 block contains 16 IP addresses

### Step 4: Allocate Second /28 Public IP Block

Allocate another /28 block - it should get the next available:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 28,
    "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
    "routable": true,
    "description": "Public IP block for API servers"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "198.51.100.16/28",
  "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
  "prefix_id": "manual-public-vrf-198-51-100-16-28",
  "available_count": 14,
  ...
}
```

Notice it allocated `198.51.100.16/28` (the next available after `198.51.100.0/28`).

### Step 5: Allocate /29 Public IP Block (Different Size)

Allocate a smaller /29 block (8 public IPs) to show size flexibility:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 29,
    "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
    "routable": true,
    "description": "Small public IP block for NAT gateways"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "198.51.100.32/29",
  ...
  "available_count": 30,
  ...
}
```

The system finds available space even with mixed subnet sizes.

## Part B: IPv6 Private IP Allocation (ULA)

### Step 1: Create Private IPv6 VRF (if not exists)

```bash
curl -X POST "http://localhost:8000/api/vrfs" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "description": "IPv6 Private IP Address VRF (ULA)",
    "routable_flag": true
  }'
```

### Step 2: Create IPv6 Private IP Parent Prefix (/40)

Create a /40 parent prefix for private IPv6 allocation using ULA (Unique Local Address) range:

```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "cidr": "fd00:1234:5600::/40",
    "routable": true,
    "tags": {"purpose": "private-ip-pool", "ip_version": "6", "type": "private", "range": "ULA"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40",
  "vrf_id": "ipv6-private-vrf",
  "cidr": "fd00:1234:5600::/40",
  ...
}
```

**Note:** A /40 prefix can allocate 256 /48 blocks. The prefix_id uses the expanded IPv6 format (all zeros are written out). The CIDR `fd00:1234:5600::/40` is valid because bits beyond the /40 mask are zero.

### Step 3: Allocate First /48 Private IPv6 Block

Allocate a /48 block (standard site allocation):

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "subnet_size": 48,
    "parent_prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40",
    "routable": true,
    "description": "Private IPv6 block for production site"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "fd00:1234:5600::/48",
  "parent_prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40",
  "prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-48",
  "available_count": 255,
  "parent_cidr": "fd00:1234:5600::/40",
  "tags": {},
  "routable": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Key Points:**
- `allocated_cidr`: The automatically allocated CIDR (`fd00:1234:5600::/48`)
- `available_count`: Remaining available /48 blocks (255 more)
- A /48 block is the standard allocation size for a site

### Step 4: Allocate Second /48 Private IPv6 Block

Allocate another /48 block:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "subnet_size": 48,
    "parent_prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40",
    "routable": true,
    "description": "Private IPv6 block for development site"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "fd00:1234:5601::/48",
  "parent_prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40",
  "prefix_id": "manual-ipv6-private-vrf-fd00-1234-5601-0000-0000-0000-0000-0000-48",
  "available_count": 254,
  ...
}
```

Notice it allocated `fd00:1234:5601::/48` (the next available after `fd00:1234:5600::/48`).

### Step 5: Allocate /56 Private IPv6 Block (Different Size)

Allocate a smaller /56 block to show size flexibility:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "subnet_size": 56,
    "parent_prefix_id": "manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40",
    "routable": true,
    "description": "Smaller private IPv6 block for test environment"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "fd00:1234:5602::/56",
  ...
  "available_count": 254,
  ...
}
```

The system finds available space even with mixed subnet sizes.

## Part C: IPv6 Public IP Allocation

### Step 1: Create Public IPv6 VRF (if not exists)

```bash
curl -X POST "http://localhost:8000/api/vrfs" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "description": "IPv6 Public IP Address VRF",
    "routable_flag": true
  }'
```

### Step 2: Create IPv6 Public IP Parent Prefix (/32)

Create a /32 parent prefix for public IPv6 allocation:

```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "cidr": "2001:db8::/32",
    "routable": true,
    "tags": {"purpose": "public-ip-pool", "ip_version": "6", "type": "public"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-32",
  "vrf_id": "ipv6-public-vrf",
  "cidr": "2001:db8::/32",
  ...
}
```

**Note:** A /32 prefix can allocate 65536 /48 blocks. The prefix_id uses the expanded IPv6 format (all zeros are written out).

### Step 3: Allocate First /48 Public IPv6 Block

Allocate a /48 block (standard site allocation):

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "subnet_size": 48,
    "parent_prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-32",
    "routable": true,
    "description": "Public IPv6 block for production site"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "2001:db8::/48",
  "parent_prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-32",
  "prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-48",
  "available_count": 65535,
  "parent_cidr": "2001:db8::/32",
  "tags": {},
  "routable": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Key Points:**
- `allocated_cidr`: The automatically allocated CIDR (`2001:db8::/48`)
- `available_count`: Remaining available /48 blocks (65535 more)
- A /48 block is the standard allocation size for a site

### Step 4: Allocate Second /48 Public IPv6 Block

Allocate another /48 block:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "subnet_size": 48,
    "parent_prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-32",
    "routable": true,
    "description": "Public IPv6 block for development site"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "2001:db8:1::/48",
  "parent_prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-32",
  "prefix_id": "manual-ipv6-public-vrf-2001-0db8-0001-0000-0000-0000-0000-0000-48",
  "available_count": 65534,
  ...
}
```

Notice it allocated `2001:db8:1::/48` (the next available after `2001:db8::/48`).

### Step 5: Allocate /56 Public IPv6 Block (Different Size)

Allocate a smaller /56 block to show size flexibility:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "subnet_size": 56,
    "parent_prefix_id": "manual-ipv6-public-vrf-2001-0db8-0000-0000-0000-0000-0000-0000-32",
    "routable": true,
    "description": "Smaller public IPv6 block for test environment"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "2001:db8:2::/56",
  ...
  "available_count": 65534,
  ...
}
```

The system finds available space even with mixed subnet sizes.

## Complete Example Script

Here's a complete bash script demonstrating all scenarios:

```bash
#!/bin/bash

API_URL="http://localhost:8000"

echo "=== IPv4 Public IP Allocation ==="

# Create IPv4 public parent prefix
echo "Creating IPv4 public parent prefix..."
PARENT_V4_RESPONSE=$(curl -s -X POST "$API_URL/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "cidr": "198.51.100.0/24",
    "routable": true,
    "tags": {"purpose": "public-ip-pool", "ip_version": "4"}
  }')

PARENT_V4_ID=$(echo $PARENT_V4_RESPONSE | jq -r '.prefix_id')
echo "Parent Prefix ID: $PARENT_V4_ID"

# Allocate /28 block
echo -e "\n1. Allocating /28 IPv4 public IP block..."
RESPONSE1=$(curl -s -X POST "$API_URL/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 28,
    "parent_prefix_id": "'$PARENT_V4_ID'",
    "routable": true,
    "description": "Public IP block for web servers"
  }')

CIDR1=$(echo $RESPONSE1 | jq -r '.allocated_cidr')
echo "Allocated CIDR: $CIDR1"

# Allocate /29 block (different size)
echo -e "\n2. Allocating /29 IPv4 public IP block..."
RESPONSE2=$(curl -s -X POST "$API_URL/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 29,
    "parent_prefix_id": "'$PARENT_V4_ID'",
    "routable": true,
    "description": "Public IP block for NAT gateways"
  }')

CIDR2=$(echo $RESPONSE2 | jq -r '.allocated_cidr')
echo "Allocated CIDR: $CIDR2"

echo -e "\n=== IPv6 Private IP Allocation ==="

# Create IPv6 private parent prefix
echo "Creating IPv6 private parent prefix..."
PARENT_V6_PRIVATE_RESPONSE=$(curl -s -X POST "$API_URL/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "cidr": "fd00:1234:5600::/40",
    "routable": true,
    "tags": {"purpose": "private-ip-pool", "ip_version": "6", "type": "private"}
  }')

PARENT_V6_PRIVATE_ID=$(echo $PARENT_V6_PRIVATE_RESPONSE | jq -r '.prefix_id')
echo "Parent Prefix ID: $PARENT_V6_PRIVATE_ID"

# Allocate /48 block
echo -e "\n3. Allocating /48 IPv6 private block..."
RESPONSE3=$(curl -s -X POST "$API_URL/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "subnet_size": 48,
    "parent_prefix_id": "'$PARENT_V6_PRIVATE_ID'",
    "routable": true,
    "description": "Private IPv6 block for production"
  }')

CIDR3=$(echo $RESPONSE3 | jq -r '.allocated_cidr')
echo "Allocated CIDR: $CIDR3"

# Allocate /56 block (different size)
echo -e "\n4. Allocating /56 IPv6 private block..."
RESPONSE4=$(curl -s -X POST "$API_URL/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-private-vrf",
    "subnet_size": 56,
    "parent_prefix_id": "'$PARENT_V6_PRIVATE_ID'",
    "routable": true,
    "description": "Private IPv6 block for test"
  }')

CIDR4=$(echo $RESPONSE4 | jq -r '.allocated_cidr')
echo "Allocated CIDR: $CIDR4"

echo -e "\n=== IPv6 Public IP Allocation ==="

# Create IPv6 public parent prefix
echo "Creating IPv6 public parent prefix..."
PARENT_V6_PUBLIC_RESPONSE=$(curl -s -X POST "$API_URL/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "cidr": "2001:db8::/32",
    "routable": true,
    "tags": {"purpose": "public-ip-pool", "ip_version": "6", "type": "public"}
  }')

PARENT_V6_PUBLIC_ID=$(echo $PARENT_V6_PUBLIC_RESPONSE | jq -r '.prefix_id')
echo "Parent Prefix ID: $PARENT_V6_PUBLIC_ID"

# Allocate /48 block
echo -e "\n5. Allocating /48 IPv6 public block..."
RESPONSE5=$(curl -s -X POST "$API_URL/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "subnet_size": 48,
    "parent_prefix_id": "'$PARENT_V6_PUBLIC_ID'",
    "routable": true,
    "description": "Public IPv6 block for production"
  }')

CIDR5=$(echo $RESPONSE5 | jq -r '.allocated_cidr')
echo "Allocated CIDR: $CIDR5"

# Allocate /56 block (different size)
echo -e "\n6. Allocating /56 IPv6 public block..."
RESPONSE6=$(curl -s -X POST "$API_URL/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "ipv6-public-vrf",
    "subnet_size": 56,
    "parent_prefix_id": "'$PARENT_V6_PUBLIC_ID'",
    "routable": true,
    "description": "Public IPv6 block for test"
  }')

CIDR6=$(echo $RESPONSE6 | jq -r '.allocated_cidr')
echo "Allocated CIDR: $CIDR6"

echo -e "\n=== Summary ==="
echo "IPv4 Public IPs:"
echo "  /28: $CIDR1"
echo "  /29: $CIDR2"
echo "IPv6 Private IPs:"
echo "  /48: $CIDR3"
echo "  /56: $CIDR4"
echo "IPv6 Public IPs:"
echo "  /48: $CIDR5"
echo "  /56: $CIDR6"
```

## API Endpoints Summary

### Allocate Subnet
```
POST /api/prefixes/allocate-subnet
Headers:
  Content-Type: application/json
Body:
  {
    "vrf_id": "string",
    "subnet_size": <number>,  // 28-29 for IPv4, 48-56 for IPv6
    "parent_prefix_id": "string" (optional),
    "tags": {} (optional),
    "routable": true (optional),
    "description": "string" (optional)
  }
```

### Create Prefix (Manual)
```
POST /api/prefixes
Headers:
  Content-Type: application/json
Body:
  {
    "vrf_id": "string",
    "cidr": "198.51.100.0/24" or "2001:db8::/32" or "fd00:1234:5600::/40",
    "parent_prefix_id": "string" (optional),
    "tags": {} (optional),
    "routable": true (optional)
  }
```

## CIDR Size Reference

### IPv4 Public IP Allocation
- **Parent /24**: 256 IP addresses (can allocate 16 /28 blocks or 32 /29 blocks)
- **Child /28**: 16 IP addresses (common for small services)
- **Child /29**: 8 IP addresses (common for NAT gateways, load balancers)

### IPv6 Private IP Allocation (ULA)
- **Parent /40**: Can allocate 256 /48 blocks or 65536 /56 blocks
- **Child /48**: Standard site allocation (65536 /64 subnets)
- **Child /56**: Smaller site allocation (256 /64 subnets)

### IPv6 Public IP Allocation
- **Parent /32**: Can allocate 65536 /48 blocks or 16777216 /56 blocks
- **Child /48**: Standard site allocation (65536 /64 subnets)
- **Child /56**: Smaller site allocation (256 /64 subnets)

## Troubleshooting

### Error: "No available subnet found"
- Check parent prefix has available space
- Verify subnet_size is valid (must fit within parent)
- Check for overlapping prefixes

### Error: "Parent prefix not found"
- Verify parent_prefix_id is correct
- Ensure parent prefix exists in the system
- **For IPv6**: The prefix_id uses expanded format (all zeros written out). For example:
  - CIDR: `fd00:1234:5600::/40`
  - prefix_id: `manual-ipv6-private-vrf-fd00-1234-5600-0000-0000-0000-0000-0000-40`
  - Always copy the exact prefix_id from the API response when creating the parent prefix

### Error: "VRF not found"
- Create the VRF first
- Verify vrf_id spelling

### IPv6 Address Format
- Use compressed format: `2001:db8::/32` (double colon for zeros)
- Use ULA range for private: `fd00:1234:5600::/40` (ensure bits beyond mask are zero)
- Ensure proper CIDR notation with `/` prefix length

## Part D: Tag Mismatch Failure Case

This section demonstrates what happens when you provide tags that don't match the parent prefix tags.

### Step 1: Attempt Allocation with Non-Matching Tags

Try to allocate a subnet with tags that don't match the parent prefix:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 28,
    "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
    "routable": true,
    "description": "This should fail due to tag mismatch",
    "tags": {"purpose": "web-servers", "ip_version": "4", "env": "production"}
  }'
```

**Expected Response (Error):**
```json
{
  "detail": "Parent prefix manual-public-vrf-198-51-100-0-24 not found or doesn't match criteria"
}
```

**Status Code:** `400 Bad Request` or `404 Not Found`

**Key Points:**
- ❌ Request failed because tags don't match parent prefix tags
- ❌ Parent prefix has tags: `{"purpose": "public-ip-pool", "ip_version": "4", "type": "public"}`
- ❌ Request has tags: `{"purpose": "web-servers", "ip_version": "4", "env": "production"}`
- ✅ The system uses **strict tag matching** - all tags in the request must match tags in the parent prefix
- ✅ When `parent_prefix_id` is specified, you can omit tags entirely (empty tags `{}` will match any parent)

### Step 2: Exact Tag Match Case (Success)

When tags match exactly with the parent prefix tags, the allocation succeeds:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 28,
    "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
    "routable": true,
    "description": "This will succeed - tags match exactly",
    "tags": {"purpose": "public-ip-pool", "ip_version": "4", "type": "public"}
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "198.51.100.48/28",
  "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
  "prefix_id": "manual-public-vrf-198-51-100-48-28",
  "available_count": 13,
  "parent_cidr": "198.51.100.0/24",
  "tags": {"purpose": "public-ip-pool", "ip_version": "4", "type": "public"},
  "routable": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Key Points:**
- ✅ Request succeeds because tags match exactly with parent prefix tags
- ✅ Parent prefix has tags: `{"purpose": "public-ip-pool", "ip_version": "4", "type": "public"}`
- ✅ Request has tags: `{"purpose": "public-ip-pool", "ip_version": "4", "type": "public"}`
- ✅ All tags in the request must match tags in the parent prefix (strict matching)
- ✅ The allocated prefix will inherit the tags from the request

### Step 3: Correct Approach - Omit Tags When Parent is Specified

When you specify `parent_prefix_id` directly, you don't need to provide tags:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "public-vrf",
    "subnet_size": 28,
    "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
    "routable": true,
    "description": "This will succeed - no tags provided"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "198.51.100.64/28",
  "parent_prefix_id": "manual-public-vrf-198-51-100-0-24",
  "prefix_id": "manual-public-vrf-198-51-100-64-28",
  "available_count": 12,
  ...
}
```

**Key Points:**
- ✅ Request succeeds because no tags are provided
- ✅ When `parent_prefix_id` is specified, tags are optional
- ✅ Tags are mainly used for automatic parent discovery when `parent_prefix_id` is not provided
- ✅ Empty tags `{}` will match any parent when `parent_prefix_id` is specified

## Summary

You have successfully demonstrated:
- ✅ IPv4 public IP allocation with /28 and /29 blocks
- ✅ IPv6 private IP allocation (ULA) with /48 and /56 blocks
- ✅ IPv6 public IP allocation with /48 and /56 blocks
- ✅ Automatic next-available allocation for different CIDR sizes
- ✅ Mixed subnet size allocation within the same parent
- ✅ Tag mismatch behavior (strict tag matching requirement)

## Best Practices

1. **Use appropriate parent sizes** for your allocation needs
2. **Tag allocations** with purpose, IP version, and type for easy filtering
3. **Use descriptive descriptions** to document allocation purpose
4. **Monitor available_count** to track remaining capacity
5. **Follow IPv6 allocation standards**: /48 for sites, /56 for smaller allocations
6. **Use ULA range (fd00::/8)** for private IPv6 addresses

## Next Steps

- Explore tag-based parent prefix matching
- Set up automated allocation workflows
- Integrate with your infrastructure provisioning tools
- Monitor allocation patterns and capacity planning
- Set up alerts for low available capacity

