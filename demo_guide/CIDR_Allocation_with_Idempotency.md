# Demo 3: CLI CIDR Allocation with Idempotency

This demo shows how to allocate CIDR blocks using the CLI with automatic next-available subnet allocation and idempotency support.

## Prerequisites

- Backend API running at `http://localhost:8000` (or your deployment URL)
- `curl` command available (or any HTTP client)
- A parent prefix created in the IPAM system (for subnet allocation)

## Overview

This demo covers two main features:
1. **Automatic Subnet Allocation**: Request a subnet by size, and the system finds the next available CIDR automatically
2. **Idempotency**: Use request IDs to ensure duplicate requests return the same result

## Part A: Allocate Next Available Child CIDR

### Step 1: Create a Parent Prefix (if not exists)

First, ensure you have a parent prefix to allocate from:

```bash
# Create a VRF (if needed)
curl -X POST "http://localhost:8000/api/vrfs" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "description": "Demo VRF for allocation",
    "routable_flag": true
  }'

# Create a parent prefix
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.0.0/13",
    "routable": true,
    "tags": {"purpose": "allocation-pool", "env": "demo"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-demo-vrf-10-0-0-0-13",
  "vrf_id": "demo-vrf",
  "cidr": "10.0.0.0/13",
  ...
}
```

**Note the `prefix_id`** - you'll need it for allocation (e.g., `manual-demo-vrf-10-0-0-0-13`).

### Step 2: Allocate First Subnet (No Request ID)

Allocate a `/16` subnet without idempotency:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 16,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "First allocated subnet"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "10.0.0.0/16",
  "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
  "prefix_id": "manual-demo-vrf-10-0-0-0-16",
  "available_count": 7,
  "parent_cidr": "10.0.0.0/13",
  "tags": {},
  "routable": true,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Key Points:**
- `allocated_cidr`: The automatically allocated CIDR (`10.0.0.0/16`)
- `available_count`: Remaining available subnets of this size (7 more `/16` subnets)
- The system automatically found the first available `/16` subnet

### Step 3: Allocate Second Subnet

Allocate another `/16` subnet - it should get the next available:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 16,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "Second allocated subnet"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "10.1.0.0/16",
  "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
  "prefix_id": "manual-demo-vrf-10-1-0-0-16",
  "available_count": 6,
  ...
}
```

Notice it allocated `10.1.0.0/16` (the next available after `10.0.0.0/16`).

### Step 4: Allocate Different Size Subnet

Allocate a `/17` subnet to show size flexibility:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 17,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "Smaller subnet allocation"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "10.0.0.0/17",
  ...
  "available_count": 15,
  ...
}
```

The system finds available space even with mixed subnet sizes.

## Part B: Idempotency Mode Demonstration

Idempotency ensures that if you retry a request with the same parameters and request ID, you get the same result instead of creating duplicates.

**Tip:** Use `curl -v` or `curl -i` to see HTTP status codes in response headers. The `-v` flag shows verbose output including headers, while `-i` shows headers and body.

### Step 1: Generate a Request ID

Generate a unique request ID (UUID format):

```bash
# On Linux/Mac
REQUEST_ID=$(uuidgen)

# Or use Python
REQUEST_ID=$(python3 -c "import uuid; print(uuid.uuid4())")

# Or manually create one
REQUEST_ID="550e8400-e29b-41d4-a716-446655440000"

echo "Request ID: $REQUEST_ID"
```

### Step 2: First Allocation with Request ID

Allocate a subnet with a request ID:

```bash
curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $REQUEST_ID" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 16,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "Idempotent allocation test",
    "request_id": "'$REQUEST_ID'"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "10.2.0.0/16",
  "prefix_id": "manual-demo-vrf-10-2-0-0-16",
  ...
}
```

**Note:**
- Response includes `X-Request-ID` header with your request ID
- Status code: `201` (created) for first request

**Save the allocated CIDR** for verification (e.g., `10.2.0.0/16`).

### Step 3: Repeat with Same Request ID and Parameters

Repeat the exact same request with the same request ID:

```bash
curl -v -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $REQUEST_ID" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 16,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "Idempotent allocation test",
    "request_id": "'$REQUEST_ID'"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "10.2.0.0/16",
  "prefix_id": "manual-demo-vrf-10-2-0-0-16",
  ...
}
```

**Status Code:** `200 OK`

You should see in the response headers:
```
< HTTP/1.1 200 OK
```

**Key Points:**
- ✅ Same CIDR returned (`10.2.0.0/16`)
- ✅ Same prefix_id returned
- ✅ Status code: `200` (OK) instead of `201` (created) - indicates cached/idempotent response
- ✅ No duplicate prefix created
- ✅ Response header `X-Request-ID` confirms idempotency

### Step 4: Different Parameters with Same Request ID (Should Fail)

Try to use the same request ID but with different parameters:

```bash
curl -v -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $REQUEST_ID" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 17,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "Different parameters",
    "request_id": "'$REQUEST_ID'"
  }'
```

**Note:** Use `-v` flag with curl to see the HTTP status code in the response headers.

**Expected Response (Error):**
```json
{
  "detail": {
    "error": "parameter_mismatch",
    "message": "Request ID 550e8400-e29b-41d4-a716-446655440000 was previously used with different parameters. Original request: {...}. Current request: {...}",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

**Status Code:** `409 Conflict`

You should see in the response headers:
```
< HTTP/1.1 409 Conflict
```

**Key Points:**
- ❌ Request rejected due to parameter mismatch
- ✅ Idempotency protection prevents inconsistent allocations
- ✅ Error message explains the conflict with original and current parameters
- ✅ Status code `409 Conflict` indicates the request conflicts with existing idempotency record

### Step 5: Same Parameters with Different Request ID (Should Get Different CIDR)

Use the same parameters but with a different request ID:

```bash
# Generate a new request ID
NEW_REQUEST_ID=$(uuidgen)
echo "New Request ID: $NEW_REQUEST_ID"

curl -X POST "http://localhost:8000/api/prefixes/allocate-subnet" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: $NEW_REQUEST_ID" \
  -d '{
    "vrf_id": "demo-vrf",
    "subnet_size": 16,
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-13",
    "routable": true,
    "description": "Idempotent allocation test",
    "request_id": "'$NEW_REQUEST_ID'"
  }'
```

**Expected Response:**
```json
{
  "allocated_cidr": "10.3.0.0/16",
  "prefix_id": "manual-demo-vrf-10-3-0-0-16",
  ...
}
```

**Key Points:**
- ✅ Different CIDR allocated (`10.3.0.0/16` vs `10.2.0.0/16`)
- ✅ Different prefix_id created
- ✅ Status code: `201` (created)
- ✅ New allocation because request ID is different


