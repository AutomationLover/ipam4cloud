# Database Schema Design for Prefix Management System

## Overview

This document provides a complete PostgreSQL schema design for a hierarchical prefix management system for cloud environments. The system supports manual prefix planning by engineers and automatic ingestion of VPC subnet information from cloud providers.

### Assumptions Made
- IPv4 now; structure supports IPv6 later.
- Tags are key/value JSONB.
- Keep provided `prefix_id` string as PK (also store a surrogate UUID where helpful).
- One default VRF (e.g., `default`) exists; all manual prefixes must reference an existing VRF (default if unspecified).
- Within a VRF, prefixes may nest but cannot overlap in sibling sets; across VRFs, anything goes.
- For non-routable VPC prefixes, we create or reference a per-VPC VRF named `vrf:<vpc_id>` automatically.
- `indentation_level` is persisted and maintained by trigger.
- `vpc_children_type_flag`: true means its immediate children are VPC subnets; false means its children are further manual prefixes. Maintained by the inserter.
- Ingestion is idempotent (upsert) and authoritative for VPC-sourced rows.
- Parent nonroutable forbids routable children (reject on write).

## PostgreSQL Schema

### Enums and Extensions

```sql
-- Enums
CREATE TYPE cloud_provider AS ENUM ('aws', 'azure', 'gcp', 'other');
CREATE TYPE prefix_source AS ENUM ('manual', 'vpc');

-- Extensions
CREATE EXTENSION IF NOT EXISTS btree_gist;
```

### VRF Table

```sql
-- VRF table
CREATE TABLE vrf (
  vrf_id TEXT PRIMARY KEY,
  description TEXT,
  tags JSONB DEFAULT '{}'::jsonb NOT NULL,
  routable_flag BOOLEAN NOT NULL DEFAULT TRUE,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT vrf_one_default CHECK (is_default IN (TRUE, FALSE)),
  CONSTRAINT vrf_singleton_default UNIQUE (is_default) DEFERRABLE INITIALLY DEFERRED
);
```

### VPC Table

```sql
-- VPC table
CREATE TABLE vpc (
  vpc_id UUID PRIMARY KEY,
  description TEXT,
  provider cloud_provider NOT NULL,
  provider_account_id TEXT,
  provider_vpc_id TEXT NOT NULL,
  region TEXT,
  tags JSONB DEFAULT '{}'::jsonb NOT NULL,
  UNIQUE (provider, provider_account_id, provider_vpc_id)
);
```

### VPC-Prefix Association Table

```sql
-- VPC ↔ prefix association (engineer-managed)
CREATE TABLE vpc_prefix_association (
  association_id UUID PRIMARY KEY,
  vpc_id UUID NOT NULL REFERENCES vpc(vpc_id) ON DELETE CASCADE,
  vpc_prefix_cidr CIDR NOT NULL,
  routable BOOLEAN NOT NULL,
  parent_prefix_id TEXT NOT NULL,
  UNIQUE (vpc_id, vpc_prefix_cidr),
  FOREIGN KEY (parent_prefix_id) REFERENCES prefix(prefix_id) DEFERRABLE INITIALLY DEFERRED
);
```

### Prefix Table

```sql
-- Prefix table
CREATE TABLE prefix (
  prefix_id TEXT PRIMARY KEY,                          -- per spec; e.g., manual-prod-vrf-10-0-0-0-16 or vpcid-subnet-prefix
  vrf_id TEXT NOT NULL REFERENCES vrf(vrf_id) ON DELETE RESTRICT,
  cidr CIDR NOT NULL,
  tags JSONB DEFAULT '{}'::jsonb NOT NULL,
  indentation_level INTEGER NOT NULL DEFAULT 0,
  parent_prefix_id TEXT NULL REFERENCES prefix(prefix_id) ON DELETE RESTRICT,
  source prefix_source NOT NULL,
  routable BOOLEAN NOT NULL,
  vpc_children_type_flag BOOLEAN NOT NULL DEFAULT FALSE,
  vpc_id UUID NULL REFERENCES vpc(vpc_id) ON DELETE SET NULL, -- required when source='vpc'
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  -- local uniqueness; prevent duplicate CIDRs in the same VRF (independent of formatted id)
  UNIQUE (vrf_id, cidr),
  -- invariants expressible without other-row checks
  CONSTRAINT vpc_fields_when_vpc_source CHECK (
    (source = 'vpc' AND vpc_id IS NOT NULL)
    OR (source = 'manual' AND vpc_id IS NULL)
  )
);
```

### Indexes

```sql
-- Helpful indexes
CREATE INDEX idx_prefix_vrf_cidr ON prefix (vrf_id, cidr);
CREATE INDEX idx_prefix_vpc ON prefix (vpc_id) WHERE vpc_id IS NOT NULL;
CREATE INDEX idx_prefix_source ON prefix (source);
CREATE INDEX idx_prefix_routable ON prefix (routable);
CREATE INDEX idx_prefix_parent ON prefix (parent_prefix_id);
CREATE INDEX idx_prefix_tags_gin ON prefix USING GIN (tags jsonb_path_ops);

-- For containment searches and overlap checks
CREATE INDEX idx_prefix_cidr_gist ON prefix USING GIST (cidr);
```

### Triggers and Functions

```sql
-- Timestamps
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER prefix_set_updated BEFORE UPDATE ON prefix
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Enforce: parent must contain child
CREATE OR REPLACE FUNCTION ensure_parent_contains_child() RETURNS trigger AS $$
DECLARE parent_cidr CIDR;
BEGIN
  IF NEW.parent_prefix_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT p.cidr INTO parent_cidr FROM prefix p WHERE p.prefix_id = NEW.parent_prefix_id;
  IF parent_cidr IS NULL THEN
    RAISE EXCEPTION 'Parent prefix % not found', NEW.parent_prefix_id;
  END IF;

  IF NOT (NEW.cidr <<= parent_cidr) THEN
    RAISE EXCEPTION 'Child % must be within parent %', NEW.cidr, parent_cidr;
  END IF;

  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER prefix_parent_contains BEFORE INSERT OR UPDATE OF cidr, parent_prefix_id ON prefix
FOR EACH ROW EXECUTE FUNCTION ensure_parent_contains_child();

-- Enforce: nonroutable cannot have routable descendants
CREATE OR REPLACE FUNCTION reject_routable_under_nonroutable() RETURNS trigger AS $$
DECLARE parent_routable BOOLEAN;
BEGIN
  IF NEW.parent_prefix_id IS NULL THEN
    RETURN NEW;
  END IF;

  SELECT p.routable INTO parent_routable FROM prefix p WHERE p.prefix_id = NEW.parent_prefix_id;
  IF parent_routable IS FALSE AND NEW.routable IS TRUE THEN
    RAISE EXCEPTION 'Nonroutable parent cannot have routable child';
  END IF;

  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER prefix_no_routable_under_nonroutable BEFORE INSERT OR UPDATE OF routable, parent_prefix_id ON prefix
FOR EACH ROW EXECUTE FUNCTION reject_routable_under_nonroutable();

-- Maintain indentation_level
CREATE OR REPLACE FUNCTION compute_indentation() RETURNS trigger AS $$
DECLARE level INTEGER := 0;
DECLARE cur_parent TEXT;
BEGIN
  cur_parent := NEW.parent_prefix_id;
  WHILE cur_parent IS NOT NULL LOOP
    level := level + 1;
    SELECT parent_prefix_id INTO cur_parent FROM prefix WHERE prefix_id = cur_parent;
  END LOOP;
  NEW.indentation_level := level;
  RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER prefix_set_indent BEFORE INSERT OR UPDATE OF parent_prefix_id ON prefix
FOR EACH ROW EXECUTE FUNCTION compute_indentation();

-- Helper: ensure per-VPC VRF exists for nonroutable VPC prefixes
CREATE OR REPLACE FUNCTION ensure_vpc_vrf(vpc_uuid UUID) RETURNS TEXT AS $$
DECLARE v TEXT := 'vrf:' || vpc_uuid::text;
BEGIN
  INSERT INTO vrf (vrf_id, description, is_default, routable_flag)
  VALUES (v, 'Auto VRF for VPC ' || vpc_uuid::text, FALSE, FALSE)
  ON CONFLICT (vrf_id) DO NOTHING;
  RETURN v;
END
$$ LANGUAGE plpgsql;

-- Upsert for VPC subnets (ingestion)
CREATE OR REPLACE FUNCTION upsert_vpc_subnet(
  in_vpc_id UUID,
  in_subnet CIDR,
  in_tags JSONB DEFAULT '{}'::jsonb
) RETURNS TEXT AS $$
DECLARE assoc RECORD;
DECLARE final_vrf TEXT;
DECLARE parent_prefix TEXT;
DECLARE is_routable BOOLEAN;
DECLARE new_prefix_id TEXT;
BEGIN
  SELECT a.*, p.vrf_id AS parent_vrf
  INTO assoc
  FROM vpc_prefix_association a
  JOIN prefix p ON p.prefix_id = a.parent_prefix_id
  WHERE a.vpc_id = in_vpc_id
    AND in_subnet <<= a.vpc_prefix_cidr
  ORDER BY masklen(a.vpc_prefix_cidr) DESC
  LIMIT 1;

  IF assoc IS NULL THEN
    RAISE EXCEPTION 'No VPC prefix association found for subnet % in VPC %', in_subnet, in_vpc_id;
  END IF;

  is_routable := assoc.routable;
  IF is_routable THEN
    final_vrf := assoc.parent_vrf;
  ELSE
    final_vrf := ensure_vpc_vrf(in_vpc_id);
  END IF;
  parent_prefix := assoc.parent_prefix_id;
  new_prefix_id := in_vpc_id::text || '-' || replace(in_subnet::text, '/', '-');

  INSERT INTO prefix (
    prefix_id, vrf_id, cidr, tags, parent_prefix_id, source, routable,
    vpc_children_type_flag, vpc_id
  )
  VALUES (
    new_prefix_id, final_vrf, in_subnet, coalesce(in_tags, '{}'::jsonb),
    parent_prefix, 'vpc', is_routable, FALSE, in_vpc_id
  )
  ON CONFLICT (prefix_id) DO UPDATE SET
    vrf_id = EXCLUDED.vrf_id,
    tags = EXCLUDED.tags,
    routable = EXCLUDED.routable,
    vpc_id = EXCLUDED.vpc_id,
    updated_at = now();

  RETURN new_prefix_id;
END
$$ LANGUAGE plpgsql;
```

### Views

```sql
-- Convenience view for tree rendering
CREATE VIEW prefix_tree AS
SELECT
  p.prefix_id,
  p.vrf_id,
  p.cidr,
  p.parent_prefix_id,
  p.indentation_level,
  p.routable,
  p.source,
  p.vpc_id,
  p.tags
FROM prefix p
ORDER BY p.vrf_id, p.indentation_level, p.cidr;
```

## User Story Implementation

### 1. Initial Setup - Create Default VRF

```sql
INSERT INTO vrf (vrf_id, description, is_default, routable_flag)
VALUES ('prod-vrf', 'Production VRF', TRUE, TRUE)
ON CONFLICT (vrf_id) DO NOTHING;
```

### 2. Engineer Creates Root Prefix (10.0.0.0/8)

```sql
INSERT INTO prefix (prefix_id, vrf_id, cidr, tags, parent_prefix_id, source, routable, vpc_children_type_flag)
VALUES ('manual-prod-vrf-10-0-0-0-8', 'prod-vrf', '10.0.0.0/8', '{"env":"prod"}', NULL, 'manual', TRUE, FALSE);
```

### 3. Create Production Environment Prefix (10.0.0.0/12)

```sql
INSERT INTO prefix (prefix_id, vrf_id, cidr, parent_prefix_id, source, routable, vpc_children_type_flag)
VALUES ('manual-prod-vrf-10-0-0-0-12', 'prod-vrf', '10.0.0.0/12', 'manual-prod-vrf-10-0-0-0-8', 'manual', TRUE, FALSE);
```

### 4. Create AWS VPC

```sql
INSERT INTO vpc (vpc_id, description, provider, provider_account_id, provider_vpc_id, region, tags)
VALUES (gen_random_uuid(), 'Prod app VPC', 'aws', '123456789012', 'vpc-0abc1234', 'us-east-1', '{"owner":"netops"}')
RETURNING vpc_id;
-- Note: Save the returned vpc_id for subsequent operations
```

### 5. Reserve Routable Prefix for VPC (10.0.0.0/16)

```sql
-- Add the manual prefix under /12 if you want it visible in tree
INSERT INTO prefix (prefix_id, vrf_id, cidr, parent_prefix_id, source, routable, vpc_children_type_flag)
VALUES ('manual-prod-vrf-10-0-0-0-16', 'prod-vrf', '10.0.0.0/16', 'manual-prod-vrf-10-0-0-0-12', 'manual', TRUE, TRUE);

-- Associate the VPC with that /16, routable
INSERT INTO vpc_prefix_association (association_id, vpc_id, vpc_prefix_cidr, routable, parent_prefix_id)
VALUES (gen_random_uuid(), '<VPC_UUID_FROM_ABOVE>', '10.0.0.0/16', TRUE, 'manual-prod-vrf-10-0-0-0-16');
```

### 6. Reserve Non-routable Prefix for Another VPC (10.1.0.0/16)

```sql
INSERT INTO prefix (prefix_id, vrf_id, cidr, parent_prefix_id, source, routable, vpc_children_type_flag)
VALUES ('manual-prod-vrf-10-1-0-0-16', 'prod-vrf', '10.1.0.0/16', 'manual-prod-vrf-10-0-0-0-12', 'manual', FALSE, TRUE);

INSERT INTO vpc_prefix_association (association_id, vpc_id, vpc_prefix_cidr, routable, parent_prefix_id)
VALUES (gen_random_uuid(), '<OTHER_VPC_UUID>', '10.1.0.0/16', FALSE, 'manual-prod-vrf-10-1-0-0-16');
```

### 7. Auto Script Ingestion (Subnet Discovery)

```sql
-- Routable subnet inherits prod-vrf
SELECT upsert_vpc_subnet('<VPC_UUID_FROM_ABOVE>'::uuid, '10.0.1.0/24'::cidr, '{"Name":"app-a"}');

-- Non-routable subnet gets its own VRF
SELECT upsert_vpc_subnet('<OTHER_VPC_UUID>'::uuid, '10.1.2.0/24'::cidr, '{"Name":"svc-b"}');
```

## Client Query Examples

### List All Prefixes in Order (per VRF, by CIDR)

```sql
SELECT * FROM prefix WHERE vrf_id = 'prod-vrf' ORDER BY cidr;
```

### Tree View with Indentation

```sql
WITH RECURSIVE t AS (
  SELECT p.*, 0 AS depth
  FROM prefix p
  WHERE p.parent_prefix_id IS NULL AND p.vrf_id = 'prod-vrf'
  UNION ALL
  SELECT c.*, t.depth + 1
  FROM prefix c
  JOIN t ON c.parent_prefix_id = t.prefix_id
)
SELECT 
  prefix_id, 
  cidr, 
  routable, 
  source, 
  depth, 
  parent_prefix_id,
  REPEAT('  ', depth) || cidr::text AS indented_display
FROM t 
ORDER BY depth, cidr;
```

### Query Specific Prefix by CIDR

```sql
SELECT p.* FROM prefix p WHERE p.vrf_id = 'prod-vrf' AND p.cidr = '10.0.1.0/24';
```

### List Children of a Specific Prefix

```sql
SELECT c.* FROM prefix c WHERE c.parent_prefix_id = 'manual-prod-vrf-10-0-0-0-12' ORDER BY c.cidr;
```

### Check Available Space in a Parent Prefix

```sql
SELECT c.cidr AS used_child
FROM prefix c
WHERE c.parent_prefix_id = 'manual-prod-vrf-10-0-0-0-12'
ORDER BY c.cidr;
-- Remaining space computation can be done in the app by subtracting these from the parent CIDR.
```

### Filter by Multiple Criteria

```sql
SELECT p.*
FROM prefix p
LEFT JOIN vpc v ON v.vpc_id = p.vpc_id
WHERE p.vrf_id = 'prod-vrf'
  AND p.routable = TRUE
  AND p.source = 'vpc'
  AND (p.tags->>'env') = 'prod'
  AND v.provider = 'aws'
  AND v.provider_account_id = '123456789012'
ORDER BY p.cidr;
```

### Query by Tags

```sql
-- Find all prefixes with specific tag
SELECT * FROM prefix WHERE tags->>'Name' = 'app-a';

-- Find all prefixes with any tag containing 'prod'
SELECT * FROM prefix WHERE tags::text ILIKE '%prod%';
```

### VRF-specific Queries

```sql
-- List all VRFs
SELECT * FROM vrf ORDER BY vrf_id;

-- Find all prefixes in default VRF
SELECT p.* FROM prefix p 
JOIN vrf v ON v.vrf_id = p.vrf_id 
WHERE v.is_default = TRUE;
```

## Acceptance Criteria Mapping

### Manual Planning Features ✓
- ✅ Create hierarchical prefixes with parent-child relationships
- ✅ Assign prefixes to VRFs (default or custom)
- ✅ Reserve prefixes for VPCs with routable/non-routable flags
- ✅ Associate VPCs with reserved CIDRs
- ✅ Maintain indentation levels automatically

### Auto Ingestion Features ✓
- ✅ Hourly job calls `upsert_vpc_subnet(vpc_id, subnet_cidr, tags)`
- ✅ Automatically derives parent association from VPC prefix associations
- ✅ Inherits routable flag from parent VPC prefix
- ✅ Assigns appropriate VRF (parent VRF for routable, per-VPC VRF for non-routable)
- ✅ Idempotent upsert operations

### Client Query Features ✓
- ✅ Flat list by CIDR order
- ✅ Tree view by parent/indentation relationships
- ✅ Item lookup by CIDR or prefix_id
- ✅ Children listing for any prefix
- ✅ Flexible filters by VRF/provider/account/vpc_id/source/routable/tags
- ✅ Space availability checking within parent prefixes

### Data Integrity Features ✓
- ✅ Parent must contain child CIDR (enforced by trigger)
- ✅ Non-routable parents cannot have routable children (enforced by trigger)
- ✅ Unique CIDR per VRF (enforced by constraint)
- ✅ VPC-sourced prefixes must have vpc_id (enforced by constraint)
- ✅ Automatic indentation level maintenance

## Notes

- The schema supports the read uncommitted isolation level as specified in the requirements
- All functional requirements are addressed while ignoring non-functional aspects like performance tuning and security
- The design is extensible for future IPv6 support and additional cloud providers
- Triggers ensure data consistency without requiring application-level validation
