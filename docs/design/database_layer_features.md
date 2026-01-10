# Database Layer Features and Logic

## Overview

This document describes what the database layer provides beyond simple table creation. It explains the special logic, constraints, and features that would be lost if replaced with simple JSON storage.

## Core Database Features

### 1. Data Integrity Enforcement

#### Foreign Key Constraints
- **Referential Integrity**: Ensures VRF, VPC, and parent prefix relationships are valid
- **Cascade Rules**: 
  - `ON DELETE RESTRICT` prevents deleting VRFs/prefixes with children
  - `ON DELETE SET NULL` for VPC relationships
  - `ON DELETE CASCADE` for VPC associations. When a VPC is deleted from the `vpc` table, all associated VPC prefix associations are automatically deleted from the `vpc_prefix_association` table.
- **Prevents Orphaned Records**: Cannot create prefixes with invalid parent references

#### Unique Constraints
- `(vrf_id, cidr)` - Prevents duplicate CIDRs within the same VRF
- `(provider, provider_account_id, provider_vpc_id)` - Prevents duplicate VPCs
- `(vpc_id, vpc_prefix_cidr)` - Prevents duplicate VPC associations

#### Check Constraints
- VPC source validation: `(source = 'vpc' AND vpc_id IS NOT NULL) OR (source = 'manual' AND vpc_id IS NULL)`
- Ensures data consistency at the database level

### 2. Database Triggers (Automatic Logic)

#### Automatic Timestamp Updates
```sql
CREATE TRIGGER prefix_set_updated BEFORE UPDATE ON prefix
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```
- Automatically updates `updated_at` on every row modification
- No application code needed

#### CIDR Containment Validation
```sql
CREATE TRIGGER prefix_parent_contains BEFORE INSERT OR UPDATE
FOR EACH ROW EXECUTE FUNCTION ensure_parent_contains_child();
```
- **Enforces**: Child CIDR must be contained within parent CIDR
- **Uses PostgreSQL native**: `<<=` (contained by or equals) operator
- **Prevents**: Invalid network hierarchies at database level
- **Cannot be bypassed**: Even direct SQL inserts are validated

#### Routable Hierarchy Enforcement
```sql
CREATE TRIGGER prefix_no_routable_under_nonroutable BEFORE INSERT OR UPDATE
FOR EACH ROW EXECUTE FUNCTION reject_routable_under_nonroutable();
```
- **Enforces**: Non-routable parents cannot have routable children
- **Business Rule**: Maintains network routing consistency
- **Automatic**: No application-level validation needed

#### Automatic Indentation Level Calculation
```sql
CREATE TRIGGER prefix_set_indent BEFORE INSERT OR UPDATE OF parent_prefix_id
FOR EACH ROW EXECUTE FUNCTION compute_indentation();
```
- **Calculates**: Hierarchical depth automatically
- **Traverses**: Parent chain to compute level
- **Maintains**: Tree structure consistency

### 3. Advanced Database Functions

#### VPC Subnet Upsert Function
```sql
CREATE OR REPLACE FUNCTION upsert_vpc_subnet(
  in_vpc_id UUID,
  in_subnet CIDR,
  in_tags JSONB DEFAULT '{}'::jsonb
) RETURNS TEXT
```

**Purpose**: Automatically ingests VPC subnets discovered from cloud providers (AWS, Azure, GCP) and creates prefix records with proper VRF assignment and parent relationships.

**Step-by-Step Logic:**

1. **Find Matching VPC Prefix Association**
   ```sql
   SELECT a.*, p.vrf_id AS parent_vrf
   FROM vpc_prefix_association a
   JOIN prefix p ON p.prefix_id = a.parent_prefix_id
   WHERE a.vpc_id = in_vpc_id
     AND in_subnet <<= a.vpc_prefix_cidr
   ORDER BY masklen(a.vpc_prefix_cidr) DESC
   LIMIT 1;
   ```
   - Uses CIDR containment operator (`<<=`) to find associations where the subnet is contained within the VPC prefix CIDR
   - Orders by mask length (most specific first) to find the closest parent
   - **Critical**: Requires GiST index for efficient containment queries

2. **Validate Association Exists**
   - Raises exception if no matching association found
   - Ensures all VPC subnets have been pre-allocated by engineers

3. **Determine Routable Flag**
   - Inherits routable flag from the VPC prefix association
   - Routable subnets go to parent VRF
   - Non-routable subnets get per-VPC VRF

4. **Select Appropriate VRF**
   ```sql
   IF is_routable THEN
     final_vrf := assoc.parent_vrf;  -- Use parent prefix's VRF
   ELSE
     final_vrf := ensure_vpc_vrf(in_vpc_id);  -- Auto-create per-VPC VRF
   END IF;
   ```
   - **Routable**: Uses parent prefix's VRF (e.g., `prod-vrf`)
   - **Non-routable**: Calls `ensure_vpc_vrf()` to create/retrieve per-VPC VRF (e.g., `aws_123456789_vpc-abc123`)

5. **Generate Prefix ID**
   ```sql
   new_prefix_id := in_vpc_id::text || '-subnet-' || replace(in_subnet::text, '/', '-');
   ```
   - Format: `{vpc_id}-subnet-{cidr}` (e.g., `550e8400-e29b-41d4-a716-446655440000-subnet-10-0-1-0-24`)
   - Ensures unique prefix IDs for VPC-sourced subnets

6. **Insert or Update Prefix**
   ```sql
   INSERT INTO prefix (...) VALUES (...)
   ON CONFLICT (prefix_id) DO UPDATE SET
     vrf_id = EXCLUDED.vrf_id,
     tags = EXCLUDED.tags,
     routable = EXCLUDED.routable,
     vpc_id = EXCLUDED.vpc_id,
     updated_at = now();
   ```
   - **Idempotent**: If prefix already exists, updates it instead of failing
   - Updates tags, VRF, and routable flag (handles VPC changes)
   - Sets `source = 'vpc'` to mark as cloud-sourced

**Use Cases:**

1. **AWS VPC Sync**: Hourly job discovers new subnets and calls this function
2. **Multi-Cloud Ingestion**: Works with AWS, Azure, GCP VPCs
3. **Subnet Updates**: Updates existing subnets when tags or configuration changes
4. **Bulk Import**: Processes thousands of subnets efficiently

**Example Usage:**
```sql
-- Routable subnet: inherits parent VRF
SELECT upsert_vpc_subnet(
  '550e8400-e29b-41d4-a716-446655440000'::uuid,
  '10.0.1.0/24'::cidr,
  '{"Name": "app-subnet", "AZ": "us-east-1a"}'::jsonb
);
-- Result: Creates prefix in 'prod-vrf' (parent's VRF)

-- Non-routable subnet: gets per-VPC VRF
SELECT upsert_vpc_subnet(
  '660e8400-e29b-41d4-a716-446655440001'::uuid,
  '10.1.2.0/24'::cidr,
  '{"Name": "private-subnet"}'::jsonb
);
-- Result: Creates prefix in 'aws_123456789_vpc-abc123' (auto-created VRF)
```

**Why JSON Can't Replace:**

1. **Complex CIDR Containment Queries**
   - Requires efficient `<<=` (contained by) operator
   - Needs GiST index for O(log n) performance
   - JSON would require O(n) full scans

2. **Transactional Consistency**
   - Must atomically: find association, determine VRF, create/update prefix
   - JSON file operations can't guarantee atomicity

3. **Concurrent Updates**
   - Multiple VPC sync jobs may run simultaneously
   - Database handles concurrent upserts safely
   - JSON would require file locking and manual conflict resolution

4. **Join Operations**
   - Joins `vpc_prefix_association` with `prefix` table
   - Efficient database joins vs. manual nested loops in JSON

5. **Automatic VRF Creation**
   - Calls `ensure_vpc_vrf()` function atomically
   - Ensures VRF exists before creating prefix
   - JSON would require separate validation steps

6. **Idempotency**
   - `ON CONFLICT` clause handles duplicates gracefully
   - Updates existing records instead of failing
   - JSON would require manual duplicate checking

**Performance Characteristics:**
- **Single Function Call**: All logic in one database operation
- **Index-Optimized**: Uses GiST index for containment queries
- **Efficient**: Processes thousands of subnets per minute
- **Scalable**: Performance doesn't degrade with data size

#### Auto VRF Creation Function
```sql
CREATE FUNCTION ensure_vpc_vrf(vpc_uuid)
```
- **Creates**: Per-VPC VRFs automatically for non-routable prefixes
- **Naming**: Generates meaningful VRF names from VPC metadata
- **Idempotent**: Uses `ON CONFLICT DO NOTHING`
- **Prevents**: Duplicate VRF creation

### 4. Specialized Indexes

#### GiST Index for Network Operations
```sql
CREATE INDEX idx_prefix_cidr_gist ON prefix USING GIST (cidr);
```
**Enables Fast:**
- Containment queries (`<<`, `>>`, `<<=`, `>>=`)
- Overlap detection (`&&`)
- Network range searches
- Hierarchical queries

**Performance Impact:**
- Without: O(n) full table scans
- With: O(log n) logarithmic lookups
- **Critical**: For systems with thousands of prefixes

#### GIN Index for JSONB Tag Searches
```sql
CREATE INDEX idx_prefix_tags_gin ON prefix USING GIN (tags jsonb_path_ops);
```
**Enables Fast:**
- Tag-based filtering
- JSONB path queries
- Complex tag searches

**Example Queries:**
```sql
-- Find prefixes with specific tag
SELECT * FROM prefix WHERE tags @> '{"Environment": "prod"}'::jsonb;

-- Find prefixes with tag key containing "AZ"
SELECT * FROM prefix WHERE tags ? 'AZ';
```

#### Standard Indexes
- `idx_prefix_vrf_cidr` - Fast VRF + CIDR lookups
- `idx_prefix_parent` - Fast parent-child queries
- `idx_prefix_vpc` - Fast VPC-related queries
- `idx_prefix_source` - Fast source filtering
- `idx_prefix_routable` - Fast routable filtering

### 5. Complex Queries and Operations

#### CIDR Containment Queries
```sql
-- Find all children of a prefix
SELECT * FROM prefix WHERE cidr <<= '10.0.0.0/8'::cidr;

-- Find parent of a prefix
SELECT * FROM prefix WHERE cidr >>= '10.1.0.0/16'::cidr;

-- Check for overlaps
SELECT * FROM prefix WHERE cidr && '10.1.5.0/24'::cidr;
```
**PostgreSQL Native**: Uses optimized network operators
**JSON Alternative**: Would require loading all data and manual calculation

#### Subnet Allocation Logic
```python
def calculate_available_subnets(parent_prefix, subnet_size):
    # 1. Get all existing children from database
    # 2. Calculate all possible subnets of given size
    # 3. Filter out overlapping subnets
    # 4. Return available subnets
```
**Requires:**
- Efficient querying of child prefixes
- Network address calculations
- Overlap detection
- **For IPv6**: Can have millions of potential subnets

#### Tree Structure Queries
```sql
-- Get prefixes in tree order
SELECT * FROM prefix 
ORDER BY vrf_id, indentation_level, cidr;
```
**Uses**: Pre-calculated `indentation_level` from trigger
**JSON Alternative**: Would require recursive traversal

#### Join Operations
```sql
-- Filter prefixes by VPC provider
SELECT p.* FROM prefix p
JOIN vpc v ON p.vpc_id = v.vpc_id
WHERE v.provider = 'aws';
```
**Efficient**: Database-optimized joins
**JSON Alternative**: Manual nested loops

### 6. ACID Transactions

#### Transactional Consistency
- **Atomicity**: All-or-nothing operations
- **Consistency**: Constraints enforced during transactions
- **Isolation**: Concurrent access handled safely
- **Durability**: Committed changes are permanent

**Example Scenario:**
```python
# Creating prefix with parent relationship
with session.begin():
    parent = create_prefix(...)
    child = create_prefix(parent_id=parent.id, ...)
    # If child creation fails, parent is rolled back
```

**JSON Alternative**: Would require manual transaction management and file locking

### 7. Concurrent Access Handling

#### Database Locks
- **Row-level locking**: Multiple users can work simultaneously
- **Deadlock detection**: Automatic resolution
- **Isolation levels**: Configurable consistency guarantees

**JSON Alternative**: Would require manual file locking, risk of data corruption

### 8. Data Types and Validation

#### Native CIDR Type
- **PostgreSQL CIDR**: Validates network format automatically
- **Network Operations**: Built-in containment, overlap operators
- **IPv4/IPv6 Support**: Handles both address families

**JSON Alternative**: Would require manual validation and parsing

#### JSONB Type
- **Efficient Storage**: Binary JSON format
- **Indexed Queries**: GIN indexes for fast searches
- **Operators**: `@>`, `?`, `?&`, `?|` for complex queries

**JSON Alternative**: Would require manual parsing and searching

#### UUID Type
- **Guaranteed Uniqueness**: Database-generated UUIDs
- **Efficient Storage**: Binary format
- **Index Performance**: Optimized for UUID lookups

### 9. Query Optimization

#### Query Planner
- **Cost-based optimization**: Chooses best execution plan
- **Index usage**: Automatically uses appropriate indexes
- **Join strategies**: Selects optimal join algorithms

**Example:**
```sql
-- Database automatically uses:
-- - idx_prefix_vrf_cidr for VRF filter
-- - idx_prefix_tags_gin for tag filter
-- - idx_prefix_cidr_gist for CIDR operations
SELECT * FROM prefix 
WHERE vrf_id = 'prod-vrf' 
  AND tags @> '{"Environment": "prod"}'::jsonb
  AND cidr <<= '10.0.0.0/8'::cidr;
```

### 10. Idempotency Support

#### Idempotency Records Table
- **Request Tracking**: Stores request IDs and parameters
- **Duplicate Prevention**: Prevents duplicate operations
- **TTL Support**: Automatic expiration of old records
- **Hash-based Matching**: Efficient duplicate detection

**Features:**
- Request hash generation
- Response caching
- Expiration management
- Concurrent request handling

## What Would Be Lost with JSON Storage

### 1. Data Integrity
- ❌ No automatic constraint enforcement
- ❌ No referential integrity
- ❌ No unique constraint checking
- ❌ Manual validation required everywhere

### 2. Automatic Logic
- ❌ No triggers for timestamp updates
- ❌ No automatic indentation calculation
- ❌ No CIDR containment validation
- ❌ Manual business rule enforcement needed

### 3. Performance
- ❌ No indexes for fast lookups
- ❌ Full file scans for every query
- ❌ O(n) complexity for network operations
- ❌ No query optimization

### 4. Concurrent Access
- ❌ File locking required
- ❌ Risk of data corruption
- ❌ No transaction support
- ❌ Manual conflict resolution

### 5. Complex Queries
- ❌ No efficient CIDR containment queries
- ❌ No optimized joins
- ❌ Manual tree traversal
- ❌ No network operator support

### 6. Scalability
- ❌ Loading entire file into memory
- ❌ No pagination support
- ❌ No efficient filtering
- ❌ Performance degrades with data size

### 7. Reliability
- ❌ No ACID guarantees
- ❌ Risk of partial writes
- ❌ No automatic recovery
- ❌ Manual backup/restore needed

## Conclusion

The database layer provides:

1. **Data Integrity**: Constraints, foreign keys, unique constraints
2. **Automatic Logic**: Triggers for timestamps, validation, calculations
3. **Performance**: Specialized indexes (GiST, GIN) for network operations
4. **Complex Queries**: Native CIDR operations, joins, aggregations
5. **ACID Transactions**: Reliable, consistent operations
6. **Concurrent Access**: Safe multi-user operations
7. **Scalability**: Efficient queries even with large datasets
8. **Specialized Functions**: VPC subnet upsert, auto VRF creation

**Replacing with JSON storage would require:**
- Manual implementation of all validation logic
- Custom indexing and search mechanisms
- File locking and transaction management
- Network address calculation libraries
- Significant performance degradation
- Loss of data integrity guarantees

The database layer is **essential** for this IPAM system's reliability, performance, and correctness.

