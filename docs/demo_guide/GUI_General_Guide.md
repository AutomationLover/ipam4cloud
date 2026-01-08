# Demo 1: Creating VRF, CIDRs, and AWS VPC Association

This demo guides you through creating a complete IPAM hierarchy: VRF → Parent CIDR → Child CIDR → AWS VPC → Association.

## Prerequisites

- Application running at `http://{deployment_location}:8080` (e.g., `http://localhost:8080`)
- Backend API accessible at `http://{deployment_location}:8000` (e.g., `http://localhost:8000`)

## Step-by-Step Guide

### Step 1: Create a VRF

A VRF (Virtual Routing and Forwarding) provides network isolation for your prefixes.

**Via Web Interface:**
1. Navigate to `http://{deployment_location}:8080`
2. Click on **"VRFs"** in the navigation menu
3. Click **"Create VRF"** button
4. Fill in the form:
   - **VRF ID**: `demo-vrf` (or any unique identifier)
   - **Description**: `Demo VRF for testing`
   - **Routable Flag**: `true` (checked)
   - **Is Default**: Leave unchecked (unless you want this as default)
   - **Tags**: Optional JSON tags, e.g., `{"env": "demo", "purpose": "testing"}`
5. Click **"Create"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/vrfs" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "description": "Demo VRF for testing",
    "routable_flag": true,
    "is_default": false,
    "tags": {"env": "demo", "purpose": "testing"}
  }'
```

**Expected Response:**
```json
{
  "vrf_id": "demo-vrf",
  "description": "Demo VRF for testing",
  "tags": {"env": "demo", "purpose": "testing"},
  "routable_flag": true,
  "is_default": false
}
```

### Step 2: Create Parent CIDR

Create a parent prefix that will contain child prefixes.

**Via Web Interface:**
1. Navigate to **"Prefixes"** in the navigation menu
2. Click **"Create Prefix"** button
3. Select the **"Manual CIDR"** tab
4. Fill in the form:
   - **VRF**: Select `demo-vrf` (created in Step 1)
   - **CIDR**: `10.0.0.0/16` (or any CIDR block)
   - **Parent Prefix**: Leave empty (this will be a root prefix)
   - **Routable**: `true` (checked)
   - **Tags**: Optional, e.g., `{"purpose": "parent", "env": "demo"}`
5. Click **"Create"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.0.0/16",
    "routable": true,
    "tags": {"purpose": "parent", "env": "demo"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-demo-vrf-10-0-0-0-16",
  "vrf_id": "demo-vrf",
  "cidr": "10.0.0.0/16",
  "tags": {"purpose": "parent", "env": "demo"},
  "indentation_level": 0,
  "parent_prefix_id": null,
  "source": "manual",
  "routable": true,
  "vpc_children_type_flag": false,
  "vpc_id": null,
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

**Note the `prefix_id`** - you'll need it for the next step (e.g., `manual-demo-vrf-10-0-0-0-16`).

### Step 3: Create Child CIDR

Create a child prefix under the parent prefix created in Step 2.

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Find the parent prefix created in Step 2
3. Click on the prefix row to view details
4. Click **"Create Child Prefix"** button (or use the main "Create Prefix" button)
5. Fill in the form:
   - **VRF**: Select `demo-vrf`
   - **CIDR**: `10.0.1.0/24` (must be within `10.0.0.0/16`)
   - **Parent Prefix**: Select `manual-demo-vrf-10-0-0-0-16` (or enter the prefix_id)
   - **Routable**: `true` (checked)
   - **Tags**: Optional, e.g., `{"purpose": "child", "subnet": "subnet-1"}`
6. Click **"Create"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.1.0/24",
    "parent_prefix_id": "manual-demo-vrf-10-0-0-0-16",
    "routable": true,
    "tags": {"purpose": "child", "subnet": "subnet-1"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-demo-vrf-10-0-1-0-24",
  "vrf_id": "demo-vrf",
  "cidr": "10.0.1.0/24",
  "tags": {"purpose": "child", "subnet": "subnet-1"},
  "indentation_level": 1,
  "parent_prefix_id": "manual-demo-vrf-10-0-0-0-16",
  "source": "manual",
  "routable": true,
  "vpc_children_type_flag": false,
  "vpc_id": null,
  "created_at": "2024-01-01T12:05:00Z",
  "updated_at": "2024-01-01T12:05:00Z"
}
```

**Note the child `prefix_id`** - you'll need it for Step 5 (e.g., `manual-demo-vrf-10-0-1-0-24`).

### Step 4: Create an AWS VPC

Register an AWS VPC in the IPAM system.

**Via Web Interface:**
1. Navigate to **"VPCs"** in the navigation menu
2. Click **"Create VPC"** button
3. Fill in the form:
   - **Description**: `Demo AWS VPC`
   - **Provider**: `aws`
   - **Provider Account ID**: Your AWS account ID (e.g., `123456789012`)
   - **Provider VPC ID**: Your AWS VPC ID (e.g., `vpc-0123456789abcdef0`)
   - **Region**: AWS region (e.g., `us-east-2`)
   - **Tags**: Optional, e.g., `{"Name": "demo-vpc", "env": "demo"}`
4. Click **"Create"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/vpcs" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Demo AWS VPC",
    "provider": "aws",
    "provider_account_id": "123456789012",
    "provider_vpc_id": "vpc-0123456789abcdef0",
    "region": "us-east-2",
    "tags": {"Name": "demo-vpc", "env": "demo"}
  }'
```

**Expected Response:**
```json
{
  "vpc_id": "550e8400-e29b-41d4-a716-446655440000",
  "description": "Demo AWS VPC",
  "provider": "aws",
  "provider_account_id": "123456789012",
  "provider_vpc_id": "vpc-0123456789abcdef0",
  "region": "us-east-2",
  "tags": {"Name": "demo-vpc", "env": "demo"}
}
```

**Note the `vpc_id`** (UUID) - you'll need it for Step 5.

### Step 5: Associate Child CIDR to AWS VPC

Associate the child prefix created in Step 3 with the AWS VPC created in Step 4.

**Important Rules:**
- Only manual prefixes (source = "manual") can be associated with VPCs
- Routable prefixes can only associate with one VPC
- Non-routable prefixes can associate with multiple VPCs

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Find the child prefix created in Step 3 (`10.0.1.0/24`)
3. Click on the prefix to view details
4. Look for **"VPC Associations"** section
5. Click **"Associate VPC"** button
6. Fill in the form:
   - **VPC**: Select the VPC created in Step 4
   - **VPC Prefix CIDR**: `10.0.1.0/24` (should match the prefix CIDR)
   - **Routable**: `true` (checked)
   - **Parent Prefix ID**: `manual-demo-vrf-10-0-1-0-24` (the child prefix ID)
7. Click **"Associate"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/vpc-associations" \
  -H "Content-Type: application/json" \
  -d '{
    "vpc_id": "550e8400-e29b-41d4-a716-446655440000",
    "vpc_prefix_cidr": "10.0.1.0/24",
    "routable": true,
    "parent_prefix_id": "manual-demo-vrf-10-0-1-0-24"
  }'
```

**Expected Response:**
```json
{
  "association_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "VPC associated successfully",
  "tags_updated": true
}
```

### Step 6: Verify the Association

Verify that everything is set up correctly.

**Check Prefix Details:**
```bash
curl "http://localhost:8000/api/prefixes/manual-demo-vrf-10-0-1-0-24"
```

The prefix should now have an `associated_vpc` tag with the VPC's provider_vpc_id.

**Check VPC Associations:**
```bash
curl "http://localhost:8000/api/vpcs/550e8400-e29b-41d4-a716-446655440000/associations"
```

**Via Web Interface:**
1. Navigate to **"VPCs"** page
2. Click on the VPC created in Step 4
3. View the **"Associations"** section to see the associated prefix

---

## Demo: Understanding `vpc_children_type_flag`

This section demonstrates how the `vpc_children_type_flag` controls whether a prefix can have manual child prefixes. This flag is crucial for managing IPAM hierarchies where some prefixes are meant for VPC subnets only.

### Step 7: Create Prefix with `vpc_children_type_flag = true` (VPC Children Enabled)

Create a prefix that is intended to have VPC subnets as children (not manual child prefixes).

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Click **"Create Prefix"** button
3. Select the **"Manual CIDR"** tab
4. Fill in the form:
   - **VRF**: Select `demo-vrf`
   - **CIDR**: `10.0.2.0/24` (or any CIDR block)
   - **Parent Prefix**: Leave empty (or select a parent)
   - **Routable**: `true` (checked)
   - **VPC Children**: **Enable** (toggle ON) - This sets `vpc_children_type_flag = true`
   - **Tags**: Optional, e.g., `{"purpose": "vpc-allocation", "env": "demo"}`
5. Click **"Create"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.2.0/24",
    "routable": true,
    "vpc_children_type_flag": true,
    "tags": {"purpose": "vpc-allocation", "env": "demo"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-demo-vrf-10-0-2-0-24",
  "vrf_id": "demo-vrf",
  "cidr": "10.0.2.0/24",
  "tags": {"purpose": "vpc-allocation", "env": "demo"},
  "indentation_level": 0,
  "parent_prefix_id": null,
  "source": "manual",
  "routable": true,
  "vpc_children_type_flag": true,
  "vpc_id": null,
  "created_at": "2024-01-01T12:10:00Z",
  "updated_at": "2024-01-01T12:10:00Z"
}
```

**Note the `prefix_id`** - you'll need it for the next steps (e.g., `manual-demo-vrf-10-0-2-0-24`).

### Step 8: Verify Child Prefix Creation is Blocked

Now verify that you **cannot** create manual child prefixes under this prefix.

**Check via API:**
```bash
curl "http://localhost:8000/api/prefixes/manual-demo-vrf-10-0-2-0-24/can-create-child"
```

**Expected Response:**
```json
{
  "can_create_child": false,
  "reason": "Prefix has vpc_children_type_flag=True, meaning its children are VPC subnets only. Cannot create manual child prefixes."
}
```

**Try to Create a Child Prefix (Should Fail):**

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Find the prefix `10.0.2.0/24` created in Step 7
3. Click on the prefix row
4. Notice that the **"Create Child Prefix"** button is **disabled** or not available
5. If you try to create a child prefix manually, you'll see an error

**Via API (Should Fail):**
```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.2.128/25",
    "parent_prefix_id": "manual-demo-vrf-10-0-2-0-24",
    "routable": true,
    "tags": {"purpose": "child"}
  }'
```

**Expected Error Response:**
```json
{
  "detail": "Cannot create child prefix: Prefix has vpc_children_type_flag=True, meaning its children are VPC subnets only. Cannot create manual child prefixes."
}
```

### Step 9: Create Prefix with `vpc_children_type_flag = false` (VPC Children Disabled)

Now create a prefix that **can** have manual child prefixes.

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Click **"Create Prefix"** button
3. Select the **"Manual CIDR"** tab
4. Fill in the form:
   - **VRF**: Select `demo-vrf`
   - **CIDR**: `10.0.3.0/24` (or any CIDR block)
   - **Parent Prefix**: Leave empty (or select a parent)
   - **Routable**: `true` (checked)
   - **VPC Children**: **Disable** (toggle OFF) - This sets `vpc_children_type_flag = false`
   - **Tags**: Optional, e.g., `{"purpose": "subdividable", "env": "demo"}`
5. Click **"Create"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.3.0/24",
    "routable": true,
    "vpc_children_type_flag": false,
    "tags": {"purpose": "subdividable", "env": "demo"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-demo-vrf-10-0-3-0-24",
  "vrf_id": "demo-vrf",
  "cidr": "10.0.3.0/24",
  "tags": {"purpose": "subdividable", "env": "demo"},
  "indentation_level": 0,
  "parent_prefix_id": null,
  "source": "manual",
  "routable": true,
  "vpc_children_type_flag": false,
  "vpc_id": null,
  "created_at": "2024-01-01T12:15:00Z",
  "updated_at": "2024-01-01T12:15:00Z"
}
```

### Step 10: Verify Child Prefix Creation is Allowed

Now verify that you **can** create manual child prefixes under this prefix.

**Check via API:**
```bash
curl "http://localhost:8000/api/prefixes/manual-demo-vrf-10-0-3-0-24/can-create-child"
```

**Expected Response:**
```json
{
  "can_create_child": true,
  "reason": "Manual prefix with vpc_children_type_flag=False can have child prefixes (allows subdivision)"
}
```

**Create a Child Prefix (Should Succeed):**

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Find the prefix `10.0.3.0/24` created in Step 9
3. Click on the prefix row
4. Click **"Create Child Prefix"** button (should be enabled)
5. Fill in the form:
   - **VRF**: Select `demo-vrf`
   - **CIDR**: `10.0.3.128/25` (must be within `10.0.3.0/24`)
   - **Parent Prefix**: `manual-demo-vrf-10-0-3-0-24`
   - **Routable**: `true` (checked)
   - **Tags**: Optional
6. Click **"Create"** - This should succeed!

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/prefixes" \
  -H "Content-Type: application/json" \
  -d '{
    "vrf_id": "demo-vrf",
    "cidr": "10.0.3.128/25",
    "parent_prefix_id": "manual-demo-vrf-10-0-3-0-24",
    "routable": true,
    "tags": {"purpose": "child"}
  }'
```

**Expected Response:**
```json
{
  "prefix_id": "manual-demo-vrf-10-0-3-128-25",
  "vrf_id": "demo-vrf",
  "cidr": "10.0.3.128/25",
  "tags": {"purpose": "child"},
  "indentation_level": 1,
  "parent_prefix_id": "manual-demo-vrf-10-0-3-0-24",
  "source": "manual",
  "routable": true,
  "vpc_children_type_flag": false,
  "vpc_id": null,
  "created_at": "2024-01-01T12:20:00Z",
  "updated_at": "2024-01-01T12:20:00Z"
}
```

### Step 11: Associate Prefix with `vpc_children_type_flag = true` to VPC

Now associate the prefix created in Step 7 (with `vpc_children_type_flag = true`) to a VPC. This demonstrates the typical use case: prefixes meant for VPC subnets should have this flag enabled.

**Important:** When a prefix is associated with a VPC, it's typically intended to have VPC subnets as children, not manual child prefixes. Setting `vpc_children_type_flag = true` enforces this behavior.

**Via Web Interface:**
1. Navigate to **"Prefixes"** page
2. Find the prefix `10.0.2.0/24` created in Step 7 (with `vpc_children_type_flag = true`)
3. Click on the prefix to view details
4. Look for **"VPC Associations"** section
5. Click **"Associate VPC"** button
6. Fill in the form:
   - **VPC**: Select the VPC created in Step 4 (or create a new one)
   - **VPC Prefix CIDR**: `10.0.2.0/24` (should match the prefix CIDR)
   - **Routable**: `true` (checked)
   - **Parent Prefix ID**: `manual-demo-vrf-10-0-2-0-24` (the prefix ID)
7. Click **"Associate"**

**Via API:**
```bash
curl -X POST "http://localhost:8000/api/vpc-associations" \
  -H "Content-Type: application/json" \
  -d '{
    "vpc_id": "550e8400-e29b-41d4-a716-446655440000",
    "vpc_prefix_cidr": "10.0.2.0/24",
    "routable": true,
    "parent_prefix_id": "manual-demo-vrf-10-0-2-0-24"
  }'
```

**Expected Response:**
```json
{
  "association_id": "770e8400-e29b-41d4-a716-446655440002",
  "message": "VPC associated successfully",
  "tags_updated": true
}
```

**Verify the Association:**
```bash
curl "http://localhost:8000/api/prefixes/manual-demo-vrf-10-0-2-0-24"
```

The prefix should now have:
- `vpc_children_type_flag: true` (VPC Children Enabled)
- An `associated_vpc` tag with the VPC's provider_vpc_id
- Cannot have manual child prefixes (only VPC subnets)

### Summary of `vpc_children_type_flag` Behavior

| Flag Value | GUI Display | Can Create Manual Child Prefixes? | Intended Use |
|------------|-------------|-----------------------------------|--------------|
| `true` | **VPC Children: Enabled** | ❌ No | Prefix is allocated for VPC subnets only. Children will be VPC subnets (created via VPC sync). |
| `false` | **VPC Children: Disabled** | ✅ Yes | Prefix can be subdivided into manual child prefixes. Useful for further IPAM planning. |

**Best Practice:** When associating a prefix with a VPC, set `vpc_children_type_flag = true` to indicate that this prefix's children are VPC subnets only, preventing accidental manual subdivisions.

---

## Summary

You have successfully:
- ✅ Created a VRF (`demo-vrf`)
- ✅ Created a parent CIDR (`10.0.0.0/16`)
- ✅ Created a child CIDR (`10.0.1.0/24`)
- ✅ Created an AWS VPC registration
- ✅ Associated the child CIDR with the AWS VPC
- ✅ Demonstrated `vpc_children_type_flag = true` (cannot create manual child prefixes)
- ✅ Demonstrated `vpc_children_type_flag = false` (can create manual child prefixes)
- ✅ Associated a prefix with `vpc_children_type_flag = true` to a VPC

## Troubleshooting

**Error: "VRF with ID already exists"**
- Choose a different VRF ID or delete the existing one

**Error: "CIDR overlaps with existing prefix"**
- Choose a different CIDR block that doesn't conflict

**Error: "Parent prefix not found"**
- Verify the parent_prefix_id is correct

**Error: "Prefixes whose source is cloud VPC cannot associate to VPC"**
- Only manual prefixes can be associated. VPC-sourced prefixes are automatically managed.

**Error: "Routable prefixes can only associate to one VPC ID"**
- If the prefix is routable and already associated, you cannot associate it to another VPC

**Error: "Prefix has vpc_children_type_flag=True, meaning its children are VPC subnets only. Cannot create manual child prefixes."**
- This prefix is configured to have VPC subnets as children only. If you need to create manual child prefixes, either:
  - Update the prefix to set `vpc_children_type_flag = false` (via Edit Prefix)
  - Use a different prefix that allows manual child prefixes

## Next Steps

- View the hierarchical structure in the **"Prefixes"** tree view
- Create additional child prefixes
- Explore the VPC details page to see all associations

