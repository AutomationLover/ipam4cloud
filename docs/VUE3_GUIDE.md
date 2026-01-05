# Vue 3 Frontend Guide

## Table of Contents
1. [Vue 3 Basics](#vue-3-basics)
2. [Project Structure](#project-structure)
3. [File Purposes](#file-purposes)
4. [Component Functions](#component-functions)

---

## Vue 3 Basics

### What is Vue 3?
Vue 3 is a progressive JavaScript framework for building user interfaces. It uses a component-based architecture where each component manages its own state and UI.

### Key Concepts

#### 1. **Single File Components (.vue files)**
Vue components are written in `.vue` files with three sections:
- `<template>`: HTML markup (what users see)
- `<script>`: JavaScript logic (component behavior)
- `<style>`: CSS styling (how it looks)

#### 2. **Options API vs Composition API**
This project uses the **Options API**, which organizes code into:
- `data()`: Component state (reactive variables)
- `methods`: Functions that can be called
- `computed`: Derived values that update automatically
- `watch`: React to data changes
- `mounted()`: Lifecycle hook that runs when component loads

#### 3. **Reactivity**
Vue automatically updates the UI when data changes:
```javascript
data() {
  return {
    count: 0  // Changing this updates the UI automatically
  }
}
```

#### 4. **Directives**
- `v-model`: Two-way data binding (input ↔ data)
- `v-if`/`v-show`: Conditional rendering
- `v-for`: Loop through arrays
- `v-bind` (or `:`) : Bind attributes
- `v-on` (or `@`) : Event handlers

#### 5. **Vue Router**
Handles navigation between pages:
- Routes map URLs to components
- `this.$router.push()`: Navigate programmatically
- `this.$route.params`: Access URL parameters

#### 6. **Element Plus**
UI component library providing pre-built components like:
- `el-button`, `el-table`, `el-dialog`, `el-form`, etc.

---

## Project Structure

```
frontend/
├── src/
│   ├── main.js              # Application entry point
│   ├── App.vue              # Root component with navigation
│   ├── api/
│   │   └── index.js         # API client and endpoints
│   ├── router/
│   │   └── index.js         # Route definitions
│   └── views/               # Page components
│       ├── Home.vue
│       ├── Prefixes.vue
│       ├── PrefixDetail.vue
│       ├── VRFs.vue
│       ├── VRFDetail.vue
│       ├── VPCs.vue
│       ├── VPCDetail.vue
│       ├── IPAddresses.vue
│       ├── BackupRestore.vue
│       └── PCExportImport.vue
├── package.json             # Dependencies
├── vue.config.js            # Vue CLI configuration
└── babel.config.js          # Babel transpiler config
```

---

## File Purposes

### Configuration Files

#### `package.json`
- Lists all dependencies (Vue, Element Plus, Vue Router, Axios)
- Defines npm scripts (`serve`, `build`, `lint`)

#### `vue.config.js`
- Configures Vue CLI build settings
- Sets dev server host/port
- Configures linting behavior

#### `babel.config.js`
- Configures Babel to transpile modern JavaScript for older browsers

### Core Application Files

#### `src/main.js`
**Purpose**: Application entry point that:
- Creates the Vue app instance
- Registers Vue Router for navigation
- Registers Element Plus UI components
- Registers all Element Plus icons
- Mounts the app to the DOM

#### `src/App.vue`
**Purpose**: Root component that provides:
- Global navigation menu (header)
- Layout structure (container, header, main content area)
- Router view outlet (where page components render)

#### `src/router/index.js`
**Purpose**: Defines all application routes:
- Maps URL paths to Vue components
- Handles navigation between pages
- Supports dynamic routes (e.g., `/prefixes/:prefixId`)

#### `src/api/index.js`
**Purpose**: Centralized API client that:
- Configures Axios HTTP client
- Defines all API endpoints (prefixes, VRFs, VPCs, etc.)
- Handles request/response interceptors
- Provides reusable API functions

---

## Component Functions

### `src/App.vue`

**Purpose**: Root component with navigation menu

**Functions**:
- None (reserved for future methods)

**Key Features**:
- Horizontal navigation menu
- Router links to all main pages
- Sub-menu for data management features

---

### `src/views/Home.vue`

**Purpose**: Dashboard/homepage showing system overview

**Data Properties**:
- `stats`: Object containing statistics (totalPrefixes, manualPrefixes, vpcPrefixes, totalVRFs)

**Functions**:
- `loadStats()`: Fetches statistics from API and updates `stats` object
  - Calls `prefixAPI.getPrefixes()` and `vrfAPI.getVRFs()`
  - Calculates counts for different prefix types
  - Handles errors gracefully

**Lifecycle**:
- `mounted()`: Automatically loads statistics when component loads

---

### `src/views/Prefixes.vue`

**Purpose**: Main prefix management page with list/tree views

**Data Properties**:
- `loading`: Boolean for loading state
- `viewMode`: 'list' or 'tree'
- `prefixes`: Array of prefix objects (for list view)
- `treeData`: Array of tree nodes (for tree view)
- `filters`: Object with search/filter criteria
- `pagination`: Object with page info
- `showCreateDialog`, `showEditDialog`, `showVPCDialog`: Boolean flags for dialogs
- `newPrefix`, `editPrefixData`: Form data objects
- `subnetAllocation`: Object for subnet allocation form
- `allocationPreview`: Preview data for subnet allocation

**Computed Properties**:
- `availableVPCs`: Filters VPCs to exclude already-associated ones
- `filteredParentPrefixes`: Filters parent prefixes by selected VRF

**Functions**:

**Data Loading**:
- `loadData()`: Main data loader - calls `loadPrefixes()` or `loadTree()` based on view mode
- `loadPrefixes()`: Fetches prefixes from API with filters
  - Handles multiple VRF selection
  - Applies pagination
  - Filters by source, routable, search terms
- `loadTree()`: Fetches hierarchical tree structure
  - Supports multiple VRF filtering
  - Handles deleted prefixes option
- `loadVRFs()`: Fetches all VRFs for dropdowns
- `loadVPCs()`: Fetches all VPCs for association dialogs

**Search & Filtering**:
- `debounceSearch()`: Delays search execution (500ms) to avoid excessive API calls
- `handleSortChange()`: Handles table column sorting
- `handleSizeChange()`: Updates page size and resets to page 1
- `handleCurrentChange()`: Handles page navigation

**Prefix CRUD Operations**:
- `openCreateDialog()`: Opens create dialog and resets form
- `createChildPrefix(parentPrefix)`: Opens create dialog pre-filled with parent info
- `createPrefix()`: Creates new prefix
  - Validates form
  - Parses JSON tags
  - Handles empty parent_prefix_id (root prefixes)
  - Shows success/error messages
- `editPrefix(prefix)`: Opens edit dialog with prefix data
- `updatePrefix()`: Updates existing prefix
  - Validates form
  - Parses JSON tags
  - Handles parent prefix changes
- `deletePrefix(prefix)`: Deletes prefix with confirmation dialog

**VPC Association**:
- `associateVPC(prefix)`: Opens VPC association dialog
  - Checks if association is allowed
  - Loads current associations
- `createVPCAssociation()`: Creates new VPC association
  - Validates form
  - Updates tags if needed
  - Reloads associations
- `loadCurrentAssociations(prefixId)`: Fetches current VPC associations for a prefix
- `removeVPCAssociation(association)`: Removes VPC association with confirmation

**Validation & Rules**:
- `canCreateChildPrefix(prefix)`: Checks if prefix can have children
  - VPC-sourced prefixes cannot have children
  - Manual prefixes with VPC associations cannot have children
- `checkVPCAssociationRules(prefixId)`: Fetches backend validation rules
- `canAssociateVPC(prefix)`: Quick frontend check for VPC association
- `getVPCAssociationTooltip(prefix)`: Returns tooltip text explaining association rules

**Parent Prefix Management**:
- `loadAvailableParentPrefixes()`: Loads all manual prefixes that can be parents
- `debouncedSuggestParent()`: Debounced parent suggestion
- `suggestParentPrefix()`: Auto-suggests parent based on CIDR containment
  - Parses CIDR
  - Finds potential parents in same VRF
  - Sorts by specificity (most specific first)
  - Auto-selects if no parent chosen

**Subnet Allocation**:
- `onCreateModeChange(mode)`: Handles tab change in create dialog
- `onAllocationVRFChange()`: Handles VRF change in allocation form
- `loadAllocationParentPrefixes()`: Loads parent prefixes for allocation
- `updateAllocationPreview()`: Updates preview of subnet allocation
  - Parses tags
  - If specific parent selected, gets available subnets
  - If tag matching, finds matching parents and shows preview
- `tagsMatchStrictly(prefixTags, requiredTags)`: Checks if tags match exactly
- `allocateSubnet()`: Performs subnet allocation
  - Validates form
  - Parses tags
  - Calls API
  - Shows confirmation dialog with results
- `closeConfirmationDialog()`: Closes confirmation and refreshes data
- `viewAllocatedPrefix()`: Navigates to allocated prefix detail page

**Search Help**:
- `toggleSearchHelp()`: Toggles search help dropdown
- `hideSearchHelp()`: Hides search help with delay
- `applySearchExample(example)`: Applies example search query

**VRF Formatting**:
- `formatVRFDisplay(vrfId)`: Formats VRF ID for display
- `getVRFDetails(vrfId)`: Gets additional VRF details (currently returns null)
- `parseVRFId(vrfId)`: Parses auto-created VRF IDs into components

**Utility Functions**:
- `isIPv6(cidr)`: Checks if CIDR is IPv6
- `isSubnet(childCidr, parentCidr)`: Checks CIDR containment
  - Supports both IPv4 and IPv6
  - Validates mask length relationship
- `ipToNumber(ip)`: Converts IPv4 address to number
- `formatDateTime(dateString)`: Formats date for display

---

### `src/views/PrefixDetail.vue`

**Purpose**: Detailed view of a single prefix

**Data Properties**:
- `prefix`: Current prefix object
- `parentPrefix`: Parent prefix object (if exists)
- `children`: Array of child prefixes
- `vpcAssociations`: Array of VPC associations
- `loading`: Boolean for loading state
- `error`: Error message string
- `canCreateChild`, `canAssociateVPC`: Boolean flags for capabilities

**Functions**:
- `loadPrefixDetails()`: Main loader - fetches prefix and related data
  - Loads prefix details
  - Loads parent, children, VPC associations in parallel
  - Checks capabilities
- `loadParentPrefix()`: Fetches parent prefix if exists
- `loadChildren()`: Fetches child prefixes
- `loadVPCAssociations()`: Fetches VPC associations
- `checkCapabilities()`: Checks if prefix can create child or associate VPC
- `goBack()`: Navigates back to previous page
- `createChild()`: Navigates to prefixes page with create child query
- `associateVPC()`: Navigates to prefixes page with associate VPC query
- `editPrefix()`: Navigates to prefixes page with edit query
- `deletePrefix()`: Deletes prefix with confirmation
- `formatDate(dateString)`: Formats date for display
- `formatVRFDisplay(vrfId)`: Formats VRF ID
- `getVRFDetails(vrfId)`: Gets VRF details
- `parseVRFId(vrfId)`: Parses VRF ID

**Watchers**:
- Watches `$route.params.prefixId` to reload when route changes

---

### `src/views/VRFs.vue`

**Purpose**: VRF management page (list, create, edit, delete)

**Data Properties**:
- `loading`, `saving`: Loading states
- `vrfs`: Array of VRF objects
- `prefixCounts`: Object mapping VRF IDs to prefix counts
- `showDialog`: Boolean for create/edit dialog
- `isEditing`: Boolean flag for edit mode
- `vrfForm`: Form data object
- `vrfRules`: Form validation rules

**Functions**:
- `loadVRFs()`: Fetches all VRFs
- `loadPrefixCounts()`: Counts prefixes per VRF
- `getPrefixCount(vrfId)`: Returns prefix count for VRF
- `viewPrefixes(vrfId)`: Navigates to prefixes page filtered by VRF
- `openCreateDialog()`: Opens create dialog
- `editVRF(vrf)`: Opens edit dialog with VRF data
- `deleteVRF(vrf)`: Deletes VRF with validation
  - Checks if VRF has prefixes
  - Confirms deletion
- `saveVRF()`: Creates or updates VRF
  - Validates form
  - Handles default VRF logic
- `resetForm()`: Resets form to initial state
- `tagsToList(tags)`: Converts tags object to array for editing
- `updateTags()`: Updates tags object from tag list
- `addTag()`: Adds new tag input row
- `removeTag(index)`: Removes tag input row
- `isAutoCreatedVRF(vrfId)`: Checks if VRF is auto-created

---

### `src/views/VRFDetail.vue`

**Purpose**: Detailed view of a single VRF

**Data Properties**:
- `vrf`: Current VRF object
- `prefixes`: Array of associated prefixes
- `loading`, `loadingPrefixes`: Loading states
- `error`: Error message

**Computed Properties**:
- `parsedVRF`: Parsed VRF information (provider, account, vpcId)

**Functions**:
- `loadVRFDetails()`: Fetches VRF details and prefixes
- `loadPrefixes()`: Fetches prefixes for this VRF
- `goBack()`: Navigates back
- `createPrefix()`: Navigates to prefixes page with VRF filter
- `editVRF()`: Navigates to VRFs page with edit query
- `deleteVRF()`: Deletes VRF with confirmation
- `formatDate(dateString)`: Formats date
- `isAutoCreatedVRF(vrfId)`: Checks if VRF is auto-created
- `parseVRFId(vrfId)`: Parses VRF ID
- `getProviderType(provider)`: Returns Element Plus tag type for provider

**Watchers**:
- Watches `$route.params.vrfId` to reload when route changes

---

### `src/views/VPCs.vue`

**Purpose**: VPC management page (list, create, edit, delete)

**Data Properties**:
- `loading`, `creating`, `updating`: Loading states
- `vpcs`: Array of VPC objects
- `subnetCounts`: Object mapping VPC IDs to subnet counts
- `showCreateDialog`, `showEditDialog`: Dialog flags
- `newVPC`, `editVPCData`: Form data objects
- `tagsInput`, `editTagsInput`: JSON string inputs for tags
- `vpcRules`, `editVpcRules`: Form validation rules

**Functions**:
- `loadVPCs()`: Fetches all VPCs
- `loadSubnetCounts()`: Counts subnets per VPC
- `getProviderType(provider)`: Returns tag type for provider
- `getSubnetCount(vpcId)`: Returns subnet count for VPC
- `viewSubnets(vpcId)`: Navigates to prefixes page filtered by VPC
- `createVPC()`: Creates new VPC
  - Validates form
  - Parses JSON tags
  - Resets form on success
- `editVPC(vpc)`: Opens edit dialog with VPC data
- `updateVPC()`: Updates VPC
  - Validates form
  - Parses JSON tags
  - Excludes immutable fields (provider, provider_vpc_id)
- `deleteVPC(vpc)`: Deletes VPC with confirmation
- `copyToClipboard(text)`: Copies text to clipboard with fallback

---

### `src/views/VPCDetail.vue`

**Purpose**: Detailed view of a single VPC

**Data Properties**:
- `vpc`: Current VPC object
- `associatedVRF`: Auto-created VRF for this VPC
- `associatedPrefixes`: Array of prefixes associated with VPC
- `vpcAssociations`: Array of VPC associations
- `loading`, `loadingPrefixes`, `loadingAssociations`: Loading states
- `error`: Error message

**Functions**:
- `loadVPCDetails()`: Fetches VPC details and related data
- `loadAssociatedVRF()`: Finds and loads auto-created VRF
- `loadAssociatedPrefixes()`: Fetches prefixes associated with VPC
- `loadVPCAssociations()`: Fetches VPC associations (placeholder)
- `copyToClipboard(text)`: Copies text to clipboard
- `goBack()`: Navigates back
- `createAssociation()`: Navigates to prefixes page with associate VPC query
- `editVPC()`: Navigates to VPCs page with edit query
- `deleteVPC()`: Deletes VPC with confirmation
- `removeVPCAssociation(association)`: Removes VPC association
- `formatDate(dateString)`: Formats date
- `getProviderType(provider)`: Returns tag type for provider

**Watchers**:
- Watches `$route.params.vpcId` to reload when route changes

---

### `src/views/IPAddresses.vue`

**Purpose**: IP address search and query page

**Note**: This component uses Composition API (`setup()` function) instead of Options API

**Reactive References**:
- `labelQuery`: Current label search query
- `currentLabel`: Active label being searched
- `matchMode`: Boolean (false=contains, true=exact)
- `ipAddresses`: Array of IP address results
- `loading`: Loading state
- `currentPage`, `pageSize`, `totalCount`: Pagination data

**Functions**:
- `searchLabels(queryString, cb)`: Autocomplete function for label suggestions
  - Fetches labels from API
  - Formats as suggestions
- `handleLabelSelect(item)`: Handles label selection from autocomplete
- `handleLabelClear()`: Clears search and loads all IPs
- `loadAllIPAddresses()`: Loads all IP addresses (no filter)
- `searchIPAddresses()`: Searches IP addresses by label
  - Updates URL query parameters
  - Supports exact/partial match modes
- `clearSearch()`: Clears search and resets
- `updateUrl(label, exact)`: Updates browser URL with query parameters
- `copyShareableUrl()`: Copies current URL with query params to clipboard
- `exportToCSV()`: Exports IP addresses to CSV file
  - Creates CSV content
  - Downloads as file
- `extractTicketId(notes)`: Extracts NET- ticket ID from notes
- `formatDate(dateString)`: Formats date
- `handleSortChange()`: Handles table column sorting
- `handlePageChange(page)`: Handles pagination
- `focusSearch()`: Focuses search input

**Lifecycle**:
- `onMounted()`: Checks URL query params and loads data accordingly
- `watch()`: Watches route query params for label/exact changes

---

### `src/views/BackupRestore.vue`

**Purpose**: Backup and restore management page

**Data Properties**:
- `backups`: Array of backup objects
- `loading`, `creating`, `restoring`: Loading states
- `newBackupDescription`: Description input for new backup
- `detailsDialogVisible`, `restoreDialogVisible`: Dialog flags
- `selectedBackup`: Currently selected backup for details
- `backupToRestore`: Backup selected for restore
- `restoringBackupId`: ID of backup being restored

**Computed Properties**:
- `totalSize`: Sum of all backup sizes (formatted)
- `latestBackup`: Timestamp of most recent backup (formatted)

**Functions**:
- `loadBackups()`: Fetches list of all backups
- `createBackup()`: Creates new backup
  - Uses optional description
  - Reloads backup list
- `showBackupDetails(backup)`: Shows backup details dialog
  - Fetches detailed backup info
- `confirmRestore(backup)`: Opens restore confirmation dialog
- `performRestore()`: Performs restore operation
  - Shows warning
  - Calls restore API
  - Reloads backups
- `confirmDelete(backup)`: Deletes backup with confirmation
- `formatTimestamp(timestamp, short)`: Formats timestamp
- `formatSize(bytes, withUnit)`: Formats byte size (B, KB, MB)
- `getTimelineType(backup)`: Returns Element Plus timeline type based on status
- `isLatestBackup(backup)`: Checks if backup is the latest

---

### `src/views/PCExportImport.vue`

**Purpose**: Export/import data to/from PC folders

**Data Properties**:
- `activeTab`: Current tab ('export' or 'import')
- `exportForm`: Export form data (pcFolder, exportName)
- `exporting`: Export loading state
- `recentExports`: Array of recent export records
- `importForm`: Import form data (pcFolder)
- `scanning`, `importing`: Loading states
- `scanResults`: Results from folder scan
- `validationResults`: Validation results
- `importDialogVisible`: Import confirmation dialog flag
- `importCandidate`: Export item selected for import

**Functions**:

**Path Management**:
- `setDefaultPaths()`: Sets default export path based on OS
- `getCurrentUsername()`: Gets username from localStorage or detects from environment
- `promptForUsername()`: Prompts user to set username for better path defaults
- `getDefaultPathForFolder(folderName)`: Gets default path for specific folder
- `getSmartPathGuess(folderName)`: Provides smart path guesses
- `getPathPlaceholder()`: Returns OS-appropriate path placeholder

**Export Functions**:
- `performExport()`: Performs export to PC folder
  - Validates folder path
  - Calls export API
  - Adds to recent exports
  - Clears form
- `clearExportForm()`: Clears export form
- `showFolderHelp()`: Shows help dialog with path examples

**Import Functions**:
- `scanFolder()`: Scans PC folder for exports
  - Validates folder
  - Gets scan results
  - Validates folder structure
- `confirmImport(exportItem)`: Opens import confirmation dialog
- `performImport()`: Performs import from PC folder
  - Shows warning
  - Calls import API
  - Clears results

**Browser Capability**:
- `getBrowserCapabilityTitle()`: Returns title for browser capability alert
- `getBrowserCapabilityType()`: Returns alert type
- `getBrowserCapabilityMessage()`: Returns HTML message with OS-specific examples

**Utility**:
- `formatTimestamp(row)`: Formats timestamp from row object

**Lifecycle**:
- `mounted()`: Sets default paths and optionally prompts for username

---

## API Client (`src/api/index.js`)

**Purpose**: Centralized API communication layer

**Configuration**:
- Creates Axios instance with base URL
- Sets timeout and headers
- Adds request/response interceptors for logging

**API Modules**:

### `prefixAPI`
- `getPrefixes(params)`: Get prefixes with optional filters
- `getPrefixesTree(vrfId)`: Get hierarchical tree structure
- `getPrefix(prefixId)`: Get single prefix
- `createPrefix(data)`: Create new prefix
- `updatePrefix(prefixId, data)`: Update prefix
- `deletePrefix(prefixId)`: Delete prefix
- `getPrefixChildren(prefixId)`: Get child prefixes
- `canCreateChild(prefixId)`: Check if can create child
- `canAssociateVPC(prefixId)`: Check if can associate VPC
- `getPrefixVPCAssociations(prefixId)`: Get VPC associations
- `allocateSubnet(data)`: Allocate subnet automatically
- `getAvailableSubnets(prefixId, subnetSize)`: Get available subnets

### `vrfAPI`
- `getVRFs()`: Get all VRFs
- `getVRF(vrfId)`: Get single VRF
- `createVRF(data)`: Create VRF
- `updateVRF(vrfId, data)`: Update VRF
- `deleteVRF(vrfId)`: Delete VRF

### `vpcAPI`
- `getVPCs()`: Get all VPCs
- `getVPC(vpcId)`: Get single VPC
- `getVPCAssociations(vpcId)`: Get VPC associations
- `createVPC(data)`: Create VPC
- `updateVPC(vpcId, data)`: Update VPC
- `deleteVPC(vpcId)`: Delete VPC
- `createVPCAssociation(data)`: Create VPC association
- `removeVPCAssociation(associationId)`: Remove VPC association

### `backupAPI`
- `createBackup(description)`: Create backup
- `listBackups()`: List all backups
- `restoreBackup(backupId)`: Restore from backup
- `deleteBackup(backupId)`: Delete backup
- `getBackupDetails(backupId)`: Get backup details

### `pcExportImportAPI`
- `exportToPC(pcFolder, exportName)`: Export to PC folder
- `importFromPC(pcFolder)`: Import from PC folder
- `scanPCFolder(pcFolder)`: Scan folder for exports
- `validatePCFolder(pcFolder)`: Validate folder structure

### `ipAddressAPI`
- `getIPAddresses(label, ipAddress, limit, exact)`: Get IP addresses
- `getLabels(search)`: Get list of unique labels

---

## Common Patterns

### 1. **Loading States**
Most components use `loading` flags to show spinners:
```javascript
data() {
  return {
    loading: false
  }
}
// In methods:
this.loading = true
try {
  // API call
} finally {
  this.loading = false
}
```

### 2. **Error Handling**
Components catch errors and show user-friendly messages:
```javascript
try {
  await api.someCall()
  ElMessage.success('Success!')
} catch (error) {
  ElMessage.error(error.response?.data?.detail || 'Failed')
}
```

### 3. **Form Validation**
Forms use Element Plus validation rules:
```javascript
rules: {
  field: [
    { required: true, message: 'Required', trigger: 'blur' }
  ]
}
// Validate with:
await this.$refs.formRef.validate()
```

### 4. **Dialog Management**
Dialogs are controlled by boolean flags:
```javascript
showDialog: false
// Open:
this.showDialog = true
// Close:
this.showDialog = false
```

### 5. **Debouncing**
Search inputs use debouncing to avoid excessive API calls:
```javascript
debounceSearch() {
  clearTimeout(this.searchTimeout)
  this.searchTimeout = setTimeout(() => {
    this.loadData()
  }, 500)
}
```

### 6. **URL Query Parameters**
Components read/write URL query params for shareable links:
```javascript
// Read:
const label = this.$route.query.label
// Write:
this.$router.push({ query: { label: 'value' } })
```

---

## Summary

This Vue 3 frontend application provides a comprehensive IPAM (IP Address Management) interface with:

- **10 main views** for managing prefixes, VRFs, VPCs, IP addresses, backups, and exports
- **Centralized API client** for all backend communication
- **Element Plus UI components** for consistent, modern interface
- **Vue Router** for single-page application navigation
- **Reactive data binding** for automatic UI updates
- **Form validation** and error handling throughout
- **Debounced search** for performance
- **Shareable URLs** with query parameters

The codebase follows Vue 3 Options API patterns with clear separation of concerns, making it maintainable and extensible.

