-- Enums and Extensions
CREATE TYPE cloud_provider AS ENUM ('aws', 'azure', 'gcp', 'other');
CREATE TYPE prefix_source AS ENUM ('manual', 'vpc');
CREATE EXTENSION IF NOT EXISTS btree_gist;

-- VRF table
CREATE TABLE vrf (
  vrf_id TEXT PRIMARY KEY,
  description TEXT,
  tags JSONB DEFAULT '{}'::jsonb NOT NULL,
  routable_flag BOOLEAN NOT NULL DEFAULT TRUE,
  is_default BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT vrf_one_default CHECK (is_default IN (TRUE, FALSE))
);

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

-- Prefix table
CREATE TABLE prefix (
  prefix_id TEXT PRIMARY KEY,
  vrf_id TEXT NOT NULL REFERENCES vrf(vrf_id) ON DELETE RESTRICT,
  cidr CIDR NOT NULL,
  tags JSONB DEFAULT '{}'::jsonb NOT NULL,
  indentation_level INTEGER NOT NULL DEFAULT 0,
  parent_prefix_id TEXT NULL REFERENCES prefix(prefix_id) ON DELETE RESTRICT,
  source prefix_source NOT NULL,
  routable BOOLEAN NOT NULL,
  vpc_children_type_flag BOOLEAN NOT NULL DEFAULT FALSE,
  vpc_id UUID NULL REFERENCES vpc(vpc_id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (vrf_id, cidr),
  CONSTRAINT vpc_fields_when_vpc_source CHECK (
    (source = 'vpc' AND vpc_id IS NOT NULL)
    OR (source = 'manual' AND vpc_id IS NULL)
  )
);

-- VPC ↔ prefix association (engineer-managed)
CREATE TABLE vpc_prefix_association (
  association_id UUID PRIMARY KEY,
  vpc_id UUID NOT NULL REFERENCES vpc(vpc_id) ON DELETE CASCADE,
  vpc_prefix_cidr CIDR NOT NULL,
  routable BOOLEAN NOT NULL,
  parent_prefix_id TEXT NOT NULL REFERENCES prefix(prefix_id),
  UNIQUE (vpc_id, vpc_prefix_cidr)
);

-- Indexes
CREATE INDEX idx_prefix_vrf_cidr ON prefix (vrf_id, cidr);
CREATE INDEX idx_prefix_vpc ON prefix (vpc_id) WHERE vpc_id IS NOT NULL;
CREATE INDEX idx_prefix_source ON prefix (source);
CREATE INDEX idx_prefix_routable ON prefix (routable);
CREATE INDEX idx_prefix_parent ON prefix (parent_prefix_id);
CREATE INDEX idx_prefix_tags_gin ON prefix USING GIN (tags jsonb_path_ops);
CREATE INDEX idx_prefix_cidr_gist ON prefix USING GIST (cidr);

-- Timestamps trigger
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
DECLARE 
  vpc_info RECORD;
  vrf_name TEXT;
BEGIN
  -- Get VPC information to create meaningful VRF name
  SELECT provider, provider_account_id, provider_vpc_id 
  INTO vpc_info 
  FROM vpc 
  WHERE vpc_id = vpc_uuid;
  
  IF NOT FOUND THEN
    -- Fallback to old format if VPC not found
    vrf_name := 'vrf:' || vpc_uuid::text;
  ELSE
    -- Create meaningful VRF name: provider_account_providerVPCID
    vrf_name := vpc_info.provider::text || '_' || 
                COALESCE(vpc_info.provider_account_id, 'unknown') || '_' || 
                vpc_info.provider_vpc_id;
  END IF;
  
  INSERT INTO vrf (vrf_id, description, is_default, routable_flag)
  VALUES (
    vrf_name, 
    'Auto VRF for ' || vpc_info.provider::text || ' VPC ' || vpc_info.provider_vpc_id || 
    CASE WHEN vpc_info.provider_account_id IS NOT NULL 
         THEN ' (Account: ' || vpc_info.provider_account_id || ')' 
         ELSE '' 
    END,
    FALSE, 
    FALSE
  )
  ON CONFLICT (vrf_id) DO NOTHING;
  
  RETURN vrf_name;
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
  new_prefix_id := in_vpc_id::text || '-subnet-' || replace(in_subnet::text, '/', '-');

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
