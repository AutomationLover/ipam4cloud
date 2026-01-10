# CIDR Hierarchy Implementation

This document explains how the repository implements CIDR (Classless Inter-Domain Routing) hierarchy management at both the database and frontend levels.

## Overview

The system manages network prefixes in a hierarchical tree structure where:
- **Parent prefixes** must contain all their **child prefixes**
- **CIDR containment** is enforced to maintain valid network topology
- **Multi-level validation** ensures data integrity from UI to database

## Database Level Implementation

### 1. Schema Design

#### Core Tables
```sql
-- Prefix table with self-referential hierarchy
CREATE TABLE prefix (
  prefix_id TEXT PRIMARY KEY,
  vrf_id TEXT NOT NULL REFERENCES vrf(vrf_id),
  cidr CIDR NOT NULL,
  parent_prefix_id TEXT NULL REFERENCES prefix(prefix_id),
  indentation_level INTEGER NOT NULL DEFAULT 0,
  -- ... other fields
);
```

#### Key Constraints
- **Self-referential foreign key**: `parent_prefix_id` → `prefix_id`
- **Unique constraint**: `(vrf_id, cidr)` prevents duplicate CIDRs in same VRF
- **Cascade protection**: `ON DELETE RESTRICT` prevents orphaning children

### 2. CIDR Containment Validation

#### Primary Validation Trigger
```sql
CREATE OR REPLACE FUNCTION ensure_parent_contains_child() RETURNS trigger AS $$
DECLARE parent_cidr CIDR;
BEGIN
  IF NEW.parent_prefix_id IS NULL THEN
    RETURN NEW;  -- Root level prefix
  END IF;

  -- Get parent's CIDR
  SELECT p.cidr INTO parent_cidr FROM prefix p WHERE p.prefix_id = NEW.parent_prefix_id;
  
  IF parent_cidr IS NULL THEN
    RAISE EXCEPTION 'Parent prefix % not found', NEW.parent_prefix_id;
  END IF;

  -- PostgreSQL native CIDR containment check
  IF NOT (NEW.cidr <<= parent_cidr) THEN
    RAISE EXCEPTION 'Child % must be within parent %', NEW.cidr, parent_cidr;
  END IF;

  RETURN NEW;
END
$$ LANGUAGE plpgsql;
```

#### Trigger Registration
```sql
CREATE TRIGGER prefix_parent_contains 
BEFORE INSERT OR UPDATE OF cidr, parent_prefix_id ON prefix
FOR EACH ROW EXECUTE FUNCTION ensure_parent_contains_child();
```

### 3. PostgreSQL CIDR Operators

The database leverages PostgreSQL's native CIDR data type and operators:

| Operator | Description | Example |
|----------|-------------|---------|
| `<<=` | Is contained by | `'192.168.1.0/24' <<= '192.168.0.0/16'` → `TRUE` |
| `>>=` | Contains | `'192.168.0.0/16' >>= '192.168.1.0/24'` → `TRUE` |
| `&&` | Overlaps | `'192.168.1.0/24' && '192.168.1.128/25'` → `TRUE` |
| `masklen()` | Get mask length | `masklen('192.168.1.0/24')` → `24` |

### 4. Hierarchy Maintenance

#### Automatic Indentation Calculation
```sql
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
```

#### Additional Validation Rules
- **Routing inheritance**: Non-routable parents cannot have routable children
- **VPC constraints**: VPC-sourced prefixes follow specific containment rules
- **Deletion protection**: Cannot delete prefixes with children

### 5. Performance Optimizations

#### Specialized Indexes
```sql
-- Fast parent-child lookups
CREATE INDEX idx_prefix_parent ON prefix (parent_prefix_id);

-- CIDR containment and overlap queries
CREATE INDEX idx_prefix_cidr_gist ON prefix USING GIST (cidr);

-- VRF-scoped queries
CREATE INDEX idx_prefix_vrf_cidr ON prefix (vrf_id, cidr);
```

## Frontend Level Implementation

### 1. Auto-Suggestion System

The frontend provides intelligent parent prefix suggestions during prefix creation.

#### Trigger Mechanism
```javascript
watch: {
  'newPrefix.vrf_id'() {
    this.debouncedSuggestParent()
  },
  'newPrefix.cidr'() {
    this.debouncedSuggestParent()
  }
}
```

#### Debounced Processing
```javascript
debouncedSuggestParent() {
  clearTimeout(this.suggestionTimeout)
  this.suggestionTimeout = setTimeout(() => {
    this.suggestParentPrefix()
  }, 500) // Wait 500ms after user stops typing
}
```

### 2. Client-Side CIDR Logic

#### Containment Algorithm
```javascript
isSubnet(childCidr, parentCidr) {
  try {
    const [childNetwork, childMask] = childCidr.split('/')
    const [parentNetwork, parentMask] = parentCidr.split('/')
    
    const childMaskNum = parseInt(childMask)
    const parentMaskNum = parseInt(parentMask)
    
    // Child must have longer mask (strictly greater)
    // Equal masks mean same network size, so cannot be parent-child
    if (childMaskNum <= parentMaskNum) {
      return false
    }
    
    // Convert IPs to numbers for comparison
    const childIp = this.ipToNumber(childNetwork)
    const parentIp = this.ipToNumber(parentNetwork)
    
    // Calculate network boundaries
    const parentNetworkSize = Math.pow(2, 32 - parentMaskNum)
    const parentNetworkStart = Math.floor(parentIp / parentNetworkSize) * parentNetworkSize
    const parentNetworkEnd = parentNetworkStart + parentNetworkSize - 1
    
    return childIp >= parentNetworkStart && childIp <= parentNetworkEnd
  } catch (error) {
    return false
  }
}
```

#### IP Address Conversion
```javascript
ipToNumber(ip) {
  return ip.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet), 0) >>> 0
}
```

### 3. Smart Parent Selection

#### Algorithm Flow
```javascript
suggestParentPrefix() {
  // 1. Filter candidates by VRF
  const potentialParents = this.availableParentPrefixes
    .filter(prefix => prefix.vrf_id === this.newPrefix.vrf_id)
    
  // 2. Filter by containment capability
    .filter(prefix => this.isSubnet(newCidr, prefix.cidr))
    
  // 3. Sort by specificity (most specific first)
    .sort((a, b) => {
      const aLength = parseInt(a.cidr.split('/')[1])
      const bLength = parseInt(b.cidr.split('/')[1])
      return bLength - aLength // Descending order
    })
  
  // 4. Auto-select most specific parent
  if (potentialParents.length > 0 && !this.newPrefix.parent_prefix_id) {
    this.newPrefix.parent_prefix_id = potentialParents[0].prefix_id
  }
}
```

### 4. Tree Visualization

#### Hierarchical Display
```javascript
// Tree view uses indentation_level for visual hierarchy
<div class="tree-node" :style="{ paddingLeft: (data.indentation_level * 20) + 'px' }">
  <span class="node-cidr">{{ data.cidr }}</span>
  <span class="node-vrf">{{ data.vrf_id }}</span>
</div>
```

#### List View Sorting
```javascript
// Prefixes ordered by VRF, then hierarchy level, then CIDR
query.order_by(Prefix.vrf_id, Prefix.indentation_level, Prefix.cidr)
```

## Validation Layers

### 1. Multi-Level Validation Strategy

| Level | Purpose | Technology | Failure Mode |
|-------|---------|------------|--------------|
| **Frontend** | User experience | JavaScript | Silent fallback |
| **API** | Business logic | Python/FastAPI | HTTP error response |
| **Database** | Data integrity | PostgreSQL triggers | Exception + rollback |

### 2. Error Handling

#### Frontend Error Processing
```javascript
// Parse database validation errors
if (detail.includes('must be within parent')) {
  errorMessage = `CIDR ${this.newPrefix.cidr} must be contained within the selected parent prefix`
} else if (detail.includes('Nonroutable parent cannot have routable child')) {
  errorMessage = 'Cannot create routable prefix under non-routable parent'
}
```

#### Database Error Messages
```sql
-- Clear, actionable error messages
RAISE EXCEPTION 'Child % must be within parent %', NEW.cidr, parent_cidr;
RAISE EXCEPTION 'Parent prefix % not found', NEW.parent_prefix_id;
```

## Example Workflows

### 1. Creating a Child Prefix

```
User Input:
├─ VRF: prod-vrf
├─ CIDR: 10.1.1.0/24
└─ Parent: (auto-suggested)

Frontend Processing:
├─ Debounced suggestion (500ms delay)
├─ Filter parents in same VRF
├─ Check containment: isSubnet('10.1.1.0/24', '10.1.0.0/16') → true
├─ Sort by specificity: /16 is most specific containing parent
└─ Auto-select: parent_prefix_id = 'manual-prod-vrf-10-1-0-0-16'

Database Validation:
├─ Trigger fires on INSERT
├─ Lookup parent CIDR: '10.1.0.0/16'
├─ Check containment: '10.1.1.0/24' <<= '10.1.0.0/16' → true
├─ Calculate indentation_level: 2 (parent is level 1)
└─ Insert successful ✅
```

### 2. Invalid Hierarchy Attempt

```
User Input:
├─ VRF: prod-vrf  
├─ CIDR: 192.168.1.0/24
└─ Parent: manual-prod-vrf-10-0-0-0-8

Frontend Processing:
├─ No auto-suggestion (different network ranges)
└─ User manually selects incompatible parent

Database Validation:
├─ Trigger fires on INSERT
├─ Lookup parent CIDR: '10.0.0.0/8'
├─ Check containment: '192.168.1.0/24' <<= '10.0.0.0/8' → false
├─ RAISE EXCEPTION: 'Child 192.168.1.0/24 must be within parent 10.0.0.0/8'
└─ Transaction rolled back ❌

Frontend Error Handling:
├─ Catch exception from API
├─ Parse error message
└─ Display user-friendly error: "CIDR must be contained within parent"
```

## Key Benefits

### 1. **Data Integrity**
- **Guaranteed consistency**: Database triggers prevent invalid hierarchies
- **Atomic operations**: All validation happens within transactions
- **Referential integrity**: Foreign key constraints prevent orphaned records

### 2. **User Experience**
- **Intelligent suggestions**: Auto-suggest appropriate parents
- **Real-time feedback**: Immediate validation during typing
- **Visual hierarchy**: Tree and list views show relationships clearly

### 3. **Performance**
- **Optimized queries**: GIST indexes for efficient CIDR operations
- **Minimal overhead**: Triggers only fire on relevant column changes
- **Debounced processing**: Avoid excessive client-side calculations

### 4. **Maintainability**
- **Separation of concerns**: UI convenience vs data integrity
- **Clear error messages**: Actionable feedback for users and developers
- **Consistent validation**: Same rules enforced regardless of entry point

## Technical Considerations

### 1. **IPv4 vs IPv6**
- Current implementation focuses on IPv4
- PostgreSQL CIDR type supports both IPv4 and IPv6
- Frontend logic would need extension for IPv6 support

### 2. **Scalability**
- GIST indexes provide efficient containment queries
- Tree traversal limited by practical network hierarchy depth
- Debounced suggestions prevent UI performance issues

### 3. **Extensibility**
- Modular validation functions allow additional rules
- Frontend suggestion algorithm can be enhanced
- Database triggers can be extended for new constraints

This multi-layered approach ensures robust CIDR hierarchy management while providing an excellent user experience through intelligent automation and clear validation feedback.
