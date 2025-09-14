# PostgreSQL GIN Index for JSONB Operations

## Index Statement Explanation

```sql
CREATE INDEX prefix_tags_gin ON prefix USING gin (tags jsonb_path_ops);
```

This creates a **GIN (Generalized Inverted Index)** on the `tags` column using the `jsonb_path_ops` operator class, which is optimized for JSONB containment queries.

## What is GIN?

**GIN indexes** are perfect for JSONB because they:
- **Index individual keys and values** within the JSON structure
- Support **containment operations** (`@>`, `<@`)
- Enable **fast searches** within nested JSON data
- **Compress similar values** efficiently

## GIN vs B-tree for JSONB

| Aspect | B-tree | GIN |
|--------|--------|-----|
| **Equality** | Fast (`tags = '{...}'`) | Fast |
| **Containment** | Slow (full scan) | **Very Fast** (`tags @> '{...}'`) |
| **Key existence** | Slow | **Very Fast** (`tags ? 'key'`) |
| **Index size** | Larger | **Smaller** (compressed) |
| **Insert speed** | Fast | Slower (but acceptable) |

## The `jsonb_path_ops` Operator Class

Two options for JSONB GIN indexes:

### `jsonb_ops` (default)
- Indexes **keys AND values** separately
- Supports more operators (`?`, `?&`, `?|`)
- **Larger index size**
- Better for key existence queries

### `jsonb_path_ops` (our choice)
- Indexes **paths to values** only
- **Smaller index size** (30-50% reduction)
- **Faster containment queries**
- Only supports `@>`, `<@`, `=`

## Supported Operations

With `jsonb_path_ops`, you get efficient:

```sql
-- Containment (most common)
tags @> '{"environment": "prod"}'

-- Contained by
tags <@ '{"environment": "prod", "team": "network", "region": "us-east-1"}'

-- Equality
tags = '{"environment": "prod"}'
```

## Example Use Cases in Your System

### 1. Filter by Environment
```sql
-- Find all production prefixes
SELECT * FROM prefix 
WHERE tags @> '{"environment": "prod"}';
```

### 2. Multi-tag Filtering
```sql
-- Find prefixes with specific team and region
SELECT * FROM prefix 
WHERE tags @> '{"team": "network", "region": "us-east-1"}';
```

### 3. Complex Tag Queries
```sql
-- Find prefixes with any of multiple environments
SELECT * FROM prefix 
WHERE tags @> '{"environment": "prod"}' 
   OR tags @> '{"environment": "staging"}';

-- More efficient with array containment
SELECT * FROM prefix 
WHERE tags->'environment' IN ('"prod"', '"staging"');
```

### 4. VPC Association with Tags
```sql
-- Find VPC prefixes with specific cost center
SELECT p.*, vpa.vpcid 
FROM prefix p
JOIN vpc_prefix_association vpa ON p.prefix_id = vpa.vpc_prefix_id
WHERE p.tags @> '{"cost_center": "engineering"}';
```

### 5. Hierarchical Tag Inheritance
```sql
-- Find all children of a parent that inherit certain tags
WITH RECURSIVE prefix_tree AS (
  -- Base case: parent prefix
  SELECT prefix_id, prefix, tags, 0 as level
  FROM prefix 
  WHERE prefix_id = 'manual-vrf1-10.0.0.0/8'
  
  UNION ALL
  
  -- Recursive case: children
  SELECT p.prefix_id, p.prefix, p.tags, pt.level + 1
  FROM prefix p
  JOIN prefix_tree pt ON p.parent_prefix_id = pt.prefix_id
)
SELECT * FROM prefix_tree 
WHERE tags @> '{"inherited": "true"}';
```

## Performance Impact

### Without GIN Index
```sql
-- This would be SLOW (sequential scan)
SELECT * FROM prefix WHERE tags @> '{"environment": "prod"}';
-- Cost: O(n) - scans every row
```

### With GIN Index
```sql
-- This is FAST (index lookup)
SELECT * FROM prefix WHERE tags @> '{"environment": "prod"}';
-- Cost: O(log n) - uses index
```

## Real-world Tag Examples

```sql
-- Sample tag structures for your system
INSERT INTO prefix (prefix_id, vrfid, prefix, tags, source) VALUES 
('manual-vrf1-10.0.0.0/8', 'vrf1', '10.0.0.0/8', 
 '{"environment": "all", "purpose": "root", "owner": "network-team"}', 'manual'),

('manual-vrf1-10.0.0.0/12', 'vrf1', '10.0.0.0/12', 
 '{"environment": "prod", "purpose": "vpc-pool", "region": "us-east-1"}', 'manual'),

('vpc1-10.0.1.0/24', 'vrf1', '10.0.1.0/24', 
 '{"environment": "prod", "service": "web", "cost_center": "engineering"}', 'vpc');
```

## Query Optimization Tips

### 1. Use Containment Efficiently
```sql
-- GOOD: Uses index
WHERE tags @> '{"environment": "prod"}'

-- BAD: Cannot use jsonb_path_ops index
WHERE tags ? 'environment'  -- key existence
WHERE tags ?& array['env', 'region']  -- multiple key existence
```

### 2. Combine with Other Filters
```sql
-- Efficient: Use indexed columns first
SELECT * FROM prefix 
WHERE source = 'vpc'  -- B-tree index first
  AND tags @> '{"environment": "prod"}';  -- Then GIN index
```

### 3. Avoid JSON Path Queries
```sql
-- SLOW: Cannot use index efficiently
WHERE tags->'metadata'->>'created_by' = 'automation'

-- BETTER: Flatten structure or use containment
WHERE tags @> '{"created_by": "automation"}'
```

## Common Tag Patterns for Prefix Management

### Environment Classification
```json
{
  "environment": "prod|staging|dev|test",
  "criticality": "high|medium|low"
}
```

### Organizational Tags
```json
{
  "team": "network|security|platform",
  "cost_center": "engineering|operations|research",
  "project": "project-alpha|migration-2024"
}
```

### Technical Metadata
```json
{
  "purpose": "vpc-pool|reserved|transit|dmz",
  "region": "us-east-1|us-west-2|eu-west-1",
  "availability_zone": "a|b|c"
}
```

### Automation Tags
```json
{
  "managed_by": "terraform|ansible|manual",
  "auto_created": "true|false",
  "last_scanned": "2024-01-15T10:30:00Z"
}
```

## Advanced Query Patterns

### Tag-based Reporting
```sql
-- Generate environment summary
SELECT 
  tags->>'environment' as environment,
  COUNT(*) as prefix_count,
  SUM(CASE WHEN source = 'vpc' THEN 1 ELSE 0 END) as vpc_prefixes,
  SUM(CASE WHEN source = 'manual' THEN 1 ELSE 0 END) as manual_prefixes
FROM prefix 
WHERE tags ? 'environment'
GROUP BY tags->>'environment';
```

### Multi-dimensional Filtering
```sql
-- Complex business logic filtering
SELECT * FROM prefix 
WHERE tags @> '{"environment": "prod"}'
  AND tags @> '{"criticality": "high"}'
  AND (tags @> '{"team": "network"}' OR tags @> '{"team": "security"}')
  AND source = 'manual';
```

### Tag Validation Queries
```sql
-- Find prefixes missing required tags
SELECT prefix_id, prefix, tags
FROM prefix 
WHERE NOT (tags ? 'environment' AND tags ? 'team' AND tags ? 'purpose');

-- Find inconsistent tag values
SELECT prefix_id, tags->>'environment' as env
FROM prefix 
WHERE tags->>'environment' NOT IN ('prod', 'staging', 'dev', 'test');
```

## Index Maintenance

### Monitor Index Usage
```sql
-- Check if index is being used
SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes 
WHERE indexname = 'prefix_tags_gin';
```

### Index Size Monitoring
```sql
-- Check index size
SELECT pg_size_pretty(pg_relation_size('prefix_tags_gin')) as index_size;

-- Compare with table size
SELECT 
  pg_size_pretty(pg_relation_size('prefix')) as table_size,
  pg_size_pretty(pg_relation_size('prefix_tags_gin')) as index_size,
  round(100.0 * pg_relation_size('prefix_tags_gin') / pg_relation_size('prefix'), 1) as index_ratio_pct;
```

### Index Maintenance Commands
```sql
-- Rebuild index if needed (rare)
REINDEX INDEX prefix_tags_gin;

-- Update table statistics
ANALYZE prefix;

-- Check index bloat
SELECT 
  schemaname, tablename, indexname,
  pg_size_pretty(pg_relation_size(indexrelid)) as index_size,
  round(100 * (pg_relation_size(indexrelid)::numeric / 
    NULLIF(pg_relation_size(pg_class.oid), 0)), 2) as bloat_ratio
FROM pg_stat_user_indexes 
JOIN pg_class ON pg_class.oid = indexrelid
WHERE indexname = 'prefix_tags_gin';
```

## Why This Index is Essential

For your prefix management system, this index enables:

1. **Fast Tag-based Filtering**: Quickly find prefixes by environment, team, purpose
2. **Multi-dimensional Queries**: Combine multiple tag criteria efficiently  
3. **Reporting and Analytics**: Generate reports grouped by tag attributes
4. **Automation Integration**: Let scripts quickly identify prefixes by metadata
5. **User Experience**: Responsive UI filtering and search
6. **Compliance and Governance**: Enforce tagging policies and find non-compliant resources

## Performance Characteristics

### Query Performance
- **Tag containment**: ~1-5ms for typical queries
- **Multi-tag filters**: ~5-20ms depending on selectivity
- **Complex OR conditions**: May require query optimization

### Index Overhead
- **Storage**: ~20-40% of table size for typical tag structures
- **Insert performance**: ~10-20% slower due to index maintenance
- **Update performance**: Depends on whether tags are modified

Without this index, any tag-based query would require scanning the entire `prefix` table, making the system unusable at scale with thousands of prefixes across multiple environments and teams.

