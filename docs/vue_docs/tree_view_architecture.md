# Tree View Architecture: From Vue to Database

This document explains how the tree view works across all layers of the application, from the Vue frontend component to the database layer, including how indentation is calculated and how the tree structure is built and displayed.

## Overview

The tree view displays network prefixes in a hierarchical structure, showing parent-child relationships. The system maintains this hierarchy through:

1. **Database Layer**: Automatic indentation calculation via PostgreSQL triggers
2. **Backend API**: Tree structure building from flat database queries
3. **Frontend Vue**: Element Plus tree component rendering with expand/collapse functionality

## Architecture Flow

```
Vue Frontend (el-tree component)
    ↓ HTTP GET /api/prefixes/tree
Backend API (FastAPI)
    ↓ build_tree() recursive function
Database Query (SQLAlchemy)
    ↓ ORDER BY vrf_id, indentation_level, cidr
PostgreSQL Database
    ↓ Trigger: compute_indentation()
Prefix Table (with indentation_level)
```

## 1. Database Layer: Indentation Calculation

### When Indentation is Inserted

Indentation level is **automatically calculated and inserted** by a PostgreSQL trigger function whenever a prefix is created or its `parent_prefix_id` is updated.

### Database Trigger Function

**File:** `containers/init/01_schema.sql`

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

CREATE TRIGGER prefix_set_indent BEFORE INSERT OR UPDATE OF parent_prefix_id ON prefix
FOR EACH ROW EXECUTE FUNCTION compute_indentation();
```

### How Indentation Works

1. **Trigger Activation**: The trigger fires `BEFORE INSERT OR UPDATE OF parent_prefix_id`
2. **Level Calculation**: The function traverses up the parent chain:
   - Starts with `level = 0`
   - For each parent found, increments `level` by 1
   - Follows `parent_prefix_id` links until reaching `NULL` (root level)
3. **Assignment**: Sets `NEW.indentation_level = level` before the row is inserted/updated

### Example Calculation

```
Root prefix: 10.0.0.0/16
  parent_prefix_id = NULL
  indentation_level = 0 (no parent)

Child prefix: 10.0.1.0/24
  parent_prefix_id = <root_prefix_id>
  indentation_level = 1 (1 level deep)

Grandchild prefix: 10.0.1.0/28
  parent_prefix_id = <child_prefix_id>
  indentation_level = 2 (2 levels deep)
```

### Database Schema

**File:** `containers/app/models.py`

```python
class Prefix(Base):
    __tablename__ = 'prefix'
    
    prefix_id = Column(String, primary_key=True)
    vrf_id = Column(String, ForeignKey('vrf.vrf_id'), nullable=False)
    cidr = Column(CIDR, nullable=False)
    indentation_level = Column(Integer, default=0, nullable=False)  # Auto-calculated
    parent_prefix_id = Column(String, ForeignKey('prefix.prefix_id'))
    # ... other fields
    
    # Self-referential relationship
    parent = relationship("Prefix", remote_side=[prefix_id], backref="children")
```

**Key Points:**
- `indentation_level` is stored as an integer (0 = root, 1 = first level child, etc.)
- `parent_prefix_id` creates the parent-child relationship
- The trigger ensures `indentation_level` is always correct, even if parent relationships change

## 2. Backend API Layer: Tree Structure Building

### Database Query

**File:** `containers/app/models.py`

```python
def get_prefix_tree(self, vrf_id: Optional[str] = None) -> List[Prefix]:
    """Get prefixes in tree order"""
    with self.db_manager.get_session() as session:
        query = session.query(Prefix).order_by(
            Prefix.vrf_id, 
            Prefix.indentation_level,  # Order by indentation level
            Prefix.cidr
        )
        if vrf_id:
            query = query.filter(Prefix.vrf_id == vrf_id)
        return query.all()
```

**Query Ordering:**
1. `vrf_id` - Groups prefixes by VRF
2. `indentation_level` - Orders by depth (root first, then children)
3. `cidr` - Sorts siblings alphabetically

### Tree Building Function

**File:** `containers/backend/main.py`

```python
def build_tree(prefixes: List[Prefix], parent_id: Optional[str] = None) -> List[TreeNode]:
    """
    Recursively build tree structure from flat list of prefixes.
    
    Args:
        prefixes: Flat list of all prefixes (ordered by indentation_level)
        parent_id: Current parent prefix_id (None for root level)
    
    Returns:
        List of TreeNode objects with nested children arrays
    """
    tree = []
    for prefix in prefixes:
        if prefix.parent_prefix_id == parent_id:
            # Recursively build children for this prefix
            children = build_tree(prefixes, prefix.prefix_id)
            node = TreeNode(
                prefix_id=prefix.prefix_id,
                vrf_id=prefix.vrf_id,
                cidr=str(prefix.cidr),
                tags=prefix.tags,
                indentation_level=prefix.indentation_level,  # Preserved from DB
                parent_prefix_id=prefix.parent_prefix_id,
                source=prefix.source,
                routable=prefix.routable,
                vpc_children_type_flag=prefix.vpc_children_type_flag,
                vpc_id=str(prefix.vpc_id) if prefix.vpc_id else None,
                children=children  # Nested children array
            )
            tree.append(node)
    return tree
```

### How Tree Building Works

1. **Input**: Flat list of prefixes ordered by `indentation_level`
2. **Recursion**: For each prefix matching the current `parent_id`:
   - Create a `TreeNode` object
   - Recursively find all children (prefixes with `parent_prefix_id == current.prefix_id`)
   - Attach children array to the node
3. **Output**: Nested tree structure with parent-child relationships

### Example Transformation

**Input (Flat List):**
```python
[
    Prefix(cidr="10.0.0.0/16", parent_prefix_id=None, indentation_level=0),
    Prefix(cidr="10.0.1.0/24", parent_prefix_id="prefix1", indentation_level=1),
    Prefix(cidr="10.0.2.0/24", parent_prefix_id="prefix1", indentation_level=1),
    Prefix(cidr="10.0.1.0/28", parent_prefix_id="prefix2", indentation_level=2),
]
```

**Output (Nested Tree):**
```python
[
    TreeNode(
        cidr="10.0.0.0/16",
        indentation_level=0,
        children=[
            TreeNode(
                cidr="10.0.1.0/24",
                indentation_level=1,
                children=[
                    TreeNode(cidr="10.0.1.0/28", indentation_level=2, children=[])
                ]
            ),
            TreeNode(cidr="10.0.2.0/24", indentation_level=1, children=[])
        ]
    )
]
```

### API Endpoint

**File:** `containers/backend/main.py`

```python
@app.get("/api/prefixes/tree", response_model=List[TreeNode])
async def get_prefixes_tree(
    vrf_id: Optional[str] = Query(None),
    include_deleted: bool = Query(False),
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get prefixes in tree structure"""
    try:
        # Get flat list ordered by indentation_level
        prefixes = pm.get_prefix_tree(vrf_id)
        
        # Filter out deleted prefixes unless explicitly requested
        if not include_deleted:
            prefixes = [p for p in prefixes if not p.tags.get('deleted_from_aws')]
        
        # Build nested tree structure
        return build_tree(prefixes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### TreeNode Model

**File:** `containers/backend/main.py`

```python
class TreeNode(BaseModel):
    prefix_id: str
    vrf_id: str
    cidr: str
    tags: Dict[str, Any]
    indentation_level: int  # Preserved from database
    parent_prefix_id: Optional[str]
    source: str
    routable: bool
    vpc_children_type_flag: bool
    vpc_id: Optional[str]
    children: List['TreeNode'] = []  # Nested children array

TreeNode.model_rebuild()  # Required for recursive type
```

## 3. Frontend Vue Layer: Tree Display

### API Call

**File:** `containers/frontend/src/api/index.js`

```javascript
getPrefixesTree: (params = {}) => {
  return api.get('/api/prefixes/tree', { params })
}
```

### Vue Component Setup

**File:** `containers/frontend/src/views/Prefixes.vue`

```javascript
data() {
  return {
    treeData: [],  // Nested tree structure from API
    treeProps: {
      children: 'children',  // Tell el-tree where to find children
      label: 'cidr'          // What to display as label
    }
  }
}
```

### Loading Tree Data

```javascript
async loadTree() {
  this.loading = true
  try {
    if (this.filters.vrfIds && this.filters.vrfIds.length > 0) {
      // For multiple VRFs, combine tree data from all selected VRFs
      const allTreeData = []
      for (const vrfId of this.filters.vrfIds) {
        const params = { vrf_id: vrfId }
        if (this.filters.includeDeleted) params.include_deleted = this.filters.includeDeleted
        const response = await prefixAPI.getPrefixesTree(params)
        allTreeData.push(...response.data)
      }
      this.treeData = allTreeData
    } else {
      // No VRF filter - load tree for all VRFs
      const params = {}
      if (this.filters.includeDeleted) params.include_deleted = this.filters.includeDeleted
      const response = await prefixAPI.getPrefixesTree(params)
      this.treeData = response.data
    }
  } catch (error) {
    ElMessage.error('Failed to load prefix tree')
    console.error(error)
  } finally {
    this.loading = false
  }
}
```

### Tree Component Template

```vue
<div v-if="viewMode === 'tree'" class="tree-view">
  <el-tree
    :data="treeData"
    :props="treeProps"
    :expand-on-click-node="false"
    default-expand-all
    v-loading="loading"
  >
    <template #default="{ node, data }">
      <div class="tree-node">
        <div class="node-content">
          <el-tag :type="data.source === 'manual' ? 'primary' : 'success'" size="small">
            {{ data.source }}
          </el-tag>
          <router-link 
            :to="`/prefixes/${data.prefix_id}`"
            class="cidr-link"
          >
            <span class="node-cidr">{{ data.cidr }}</span>
          </router-link>
          <el-icon v-if="data.routable" color="green" class="node-icon">
            <Check />
          </el-icon>
          <el-icon v-else color="red" class="node-icon">
            <Close />
          </el-icon>
          <div class="node-vrf">
            <div class="vrf-primary">{{ formatVRFDisplay(data.vrf_id) }}</div>
          </div>
        </div>
        <div class="node-actions">
          <!-- Action buttons -->
        </div>
      </div>
    </template>
  </el-tree>
</div>
```

### How Element Plus Tree Displays "+" Signs

The Element Plus `el-tree` component **automatically** displays expand/collapse icons ("+" and "-") based on the `children` array:

1. **Node with Children**: If `data.children` exists and has length > 0:
   - Shows **"+"** icon when collapsed
   - Shows **"-"** icon when expanded
   - Clicking the icon expands/collapses the node

2. **Leaf Node**: If `data.children` is empty or undefined:
   - No expand/collapse icon shown
   - Node is displayed as a leaf

3. **Configuration**:
   - `:props="{ children: 'children' }"` tells el-tree to look for children in the `children` field
   - `default-expand-all` expands all nodes by default (shows "-" initially)
   - `:expand-on-click-node="false"` prevents expanding when clicking the node content (only icon expands)

### Tree Structure Visualization

```
Root Prefix (indentation_level=0)
├─ Child Prefix 1 (indentation_level=1)
│  ├─ Grandchild Prefix 1.1 (indentation_level=2)
│  └─ Grandchild Prefix 1.2 (indentation_level=2)
└─ Child Prefix 2 (indentation_level=1)
   └─ Grandchild Prefix 2.1 (indentation_level=2)
```

**In Element Plus Tree:**
```
[+] Root Prefix (10.0.0.0/16)
    [+] Child Prefix 1 (10.0.1.0/24)
        [-] Grandchild Prefix 1.1 (10.0.1.0/28)
        [-] Grandchild Prefix 1.2 (10.0.1.16/28)
    [-] Child Prefix 2 (10.0.2.0/24)
        [-] Grandchild Prefix 2.1 (10.0.2.0/28)
```

**Legend:**
- `[+]` = Collapsed node (click to expand)
- `[-]` = Expanded node (click to collapse)
- No icon = Leaf node (no children)

## 4. Complete Data Flow Example

### Step 1: Database Insert

```sql
-- Insert root prefix
INSERT INTO prefix (prefix_id, vrf_id, cidr, parent_prefix_id, ...)
VALUES ('prefix1', 'vrf1', '10.0.0.0/16', NULL, ...);
-- Trigger fires: indentation_level = 0

-- Insert child prefix
INSERT INTO prefix (prefix_id, vrf_id, cidr, parent_prefix_id, ...)
VALUES ('prefix2', 'vrf1', '10.0.1.0/24', 'prefix1', ...);
-- Trigger fires: 
--   cur_parent = 'prefix1'
--   Follow parent chain: prefix1.parent_prefix_id = NULL
--   level = 1
--   indentation_level = 1
```

### Step 2: Backend Query

```python
# Query returns flat list ordered by indentation_level
prefixes = [
    Prefix(prefix_id='prefix1', cidr='10.0.0.0/16', parent_prefix_id=None, indentation_level=0),
    Prefix(prefix_id='prefix2', cidr='10.0.1.0/24', parent_prefix_id='prefix1', indentation_level=1),
]
```

### Step 3: Tree Building

```python
# build_tree() recursively creates nested structure
tree = [
    TreeNode(
        prefix_id='prefix1',
        cidr='10.0.0.0/16',
        indentation_level=0,
        children=[
            TreeNode(
                prefix_id='prefix2',
                cidr='10.0.1.0/24',
                indentation_level=1,
                children=[]  # Empty = leaf node
            )
        ]
    )
]
```

### Step 4: API Response

```json
[
  {
    "prefix_id": "prefix1",
    "cidr": "10.0.0.0/16",
    "indentation_level": 0,
    "parent_prefix_id": null,
    "children": [
      {
        "prefix_id": "prefix2",
        "cidr": "10.0.1.0/24",
        "indentation_level": 1,
        "parent_prefix_id": "prefix1",
        "children": []
      }
    ]
  }
]
```

### Step 5: Vue Component Rendering

```javascript
// treeData receives the nested structure
this.treeData = response.data

// el-tree component:
// - Sees prefix1 has children array with 1 item
// - Displays [+] icon next to prefix1
// - Sees prefix2 has empty children array
// - Displays no icon (leaf node)
```

## 5. Key Design Decisions

### Why Store indentation_level in Database?

1. **Performance**: Avoids recalculating depth on every query
2. **Ordering**: Enables efficient `ORDER BY indentation_level` for tree traversal
3. **Consistency**: Ensures indentation is always correct, even if parent relationships change
4. **Query Optimization**: Database can use indexes on `indentation_level` for filtering

### Why Build Tree Structure in Backend?

1. **Efficiency**: Single API call returns complete tree structure
2. **Consistency**: Tree building logic centralized in backend
3. **Flexibility**: Frontend receives ready-to-render nested structure
4. **Performance**: Avoids multiple round-trips to build tree in frontend

### Why Use Element Plus el-tree?

1. **Built-in Features**: Automatic expand/collapse icons, lazy loading support
2. **Accessibility**: ARIA attributes and keyboard navigation
3. **Customization**: Flexible template slots for custom node rendering
4. **Performance**: Efficient rendering of large trees

## 6. Performance Considerations

### Database Indexes

```sql
-- Fast parent-child lookups
CREATE INDEX idx_prefix_parent ON prefix (parent_prefix_id);

-- Efficient tree ordering
CREATE INDEX idx_prefix_vrf_indent ON prefix (vrf_id, indentation_level);

-- CIDR containment queries
CREATE INDEX idx_prefix_cidr_gist ON prefix USING GIST (cidr);
```

### Query Optimization

- **Ordering**: `ORDER BY vrf_id, indentation_level, cidr` ensures efficient tree traversal
- **Filtering**: VRF filtering happens at database level, reducing data transfer
- **Tree Building**: Recursive function is O(n²) worst case, but typically O(n log n) for balanced trees

### Frontend Optimization

- **Default Expand All**: `default-expand-all` loads entire tree upfront (good for small-medium trees)
- **Lazy Loading**: Can be implemented by loading children on expand (not currently used)
- **Virtual Scrolling**: Element Plus supports virtual scrolling for very large trees

## 7. Troubleshooting

### Issue: Indentation Level Incorrect

**Symptoms**: Prefixes appear at wrong depth in tree

**Causes**:
- Trigger not firing (check trigger exists: `\d+ prefix`)
- Parent relationship changed but trigger didn't update indentation
- Manual database modification bypassed trigger

**Solution**:
```sql
-- Recalculate indentation for all prefixes
UPDATE prefix SET parent_prefix_id = parent_prefix_id;
-- This triggers the UPDATE, causing indentation recalculation
```

### Issue: Tree Not Displaying Correctly

**Symptoms**: All nodes at root level, no nesting

**Causes**:
- `build_tree()` function not called
- `children` array not populated correctly
- Frontend `treeProps` misconfigured

**Solution**:
- Check API response includes `children` arrays
- Verify `treeProps.children = 'children'` matches API response structure
- Check browser console for errors

### Issue: "+" Icons Not Showing

**Symptoms**: No expand/collapse icons visible

**Causes**:
- `children` array is empty or undefined
- Element Plus tree component not recognizing children structure
- CSS hiding icons

**Solution**:
- Verify API response includes non-empty `children` arrays for parent nodes
- Check `treeProps` configuration matches data structure
- Inspect DOM to see if icons are rendered but hidden

## Summary

The tree view architecture follows a clear separation of concerns:

1. **Database**: Automatically calculates and stores `indentation_level` via triggers
2. **Backend**: Queries flat list and builds nested tree structure recursively
3. **Frontend**: Renders tree using Element Plus component with automatic expand/collapse

The indentation level is calculated **once** at insert/update time and stored in the database, enabling efficient tree queries and display. The backend transforms the flat database structure into a nested tree, which the frontend renders with automatic expand/collapse functionality based on the presence of children arrays.

