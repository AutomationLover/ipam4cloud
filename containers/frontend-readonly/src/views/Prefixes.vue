<template>
  <div class="prefixes-container" :class="{ 'sidebar-hidden': !showSidebar }">
    <!-- Sidebar Toggle Button -->
    <div class="sidebar-toggle" :class="{ 'toggle-collapsed': !showSidebar }" @click="showSidebar = !showSidebar">
      <el-icon>
        <ArrowLeft v-if="showSidebar" />
        <ArrowRight v-else />
      </el-icon>
    </div>
    
    <!-- Sidebar -->
    <div class="sidebar" :class="{ 'sidebar-collapsed': !showSidebar }">
      <div class="sidebar-content">
        <div class="sidebar-header">
          <h3>Filters</h3>
        </div>
        
        <div class="sidebar-filters">
          <!-- VRF Filter - Available in both views -->
          <div class="filter-group">
            <label class="filter-label">VRF</label>
            <el-select 
              v-model="filters.vrfIds" 
              placeholder="Select VRFs" 
              multiple
              collapse-tags
              collapse-tags-tooltip
              clearable 
              @change="loadData"
              style="width: 100%"
              :max-collapse-tags="2"
            >
              <el-option
                v-for="vrf in vrfs"
                :key="vrf.vrf_id"
                :label="formatVRFDisplay(vrf.vrf_id)"
                :value="vrf.vrf_id"
              >
                <div class="vrf-option">
                  <div class="vrf-primary">{{ formatVRFDisplay(vrf.vrf_id) }}</div>
                  <div v-if="getVRFDetails(vrf.vrf_id)" class="vrf-details">
                    {{ getVRFDetails(vrf.vrf_id) }}
                  </div>
                </div>
              </el-option>
            </el-select>
          </div>
          
          <!-- Include Deleted Checkbox - Available in both views -->
          <div class="filter-group">
            <el-checkbox 
              v-model="filters.includeDeleted" 
              @change="loadData"
            >
              <span style="color: #f56c6c;">Show VPC Subnets Deleted from AWS</span>
            </el-checkbox>
          </div>
          
          <!-- List View Only Filters -->
          <template v-if="viewMode === 'list'">
            <!-- Source Filter -->
            <div class="filter-group">
              <label class="filter-label">Source</label>
              <el-select 
                v-model="filters.source" 
                placeholder="Source" 
                clearable 
                @change="loadPrefixes"
                style="width: 100%"
              >
                <el-option label="All Sources" value="" />
                <el-option label="Manual" value="manual" />
                <el-option label="VPC" value="vpc" />
              </el-select>
            </div>
            
            <!-- Routable Filter -->
            <div class="filter-group">
              <label class="filter-label">Routable</label>
              <el-select 
                v-model="filters.routable" 
                placeholder="Routable" 
                clearable 
                @change="loadPrefixes"
                style="width: 100%"
              >
                <el-option label="All" value="" />
                <el-option label="Routable" :value="true" />
                <el-option label="Non-routable" :value="false" />
              </el-select>
            </div>
            
            <!-- Search Filter -->
            <div class="filter-group">
              <label class="filter-label">Search</label>
              <div class="search-container">
                <el-input
                  v-model="filters.search"
                  placeholder="Search prefixes, tags..."
                  @input="debounceSearch"
                  @focus="showSearchHelp = true"
                  @blur="hideSearchHelp"
                  clearable
                >
                  <template #prefix>
                    <el-icon><Search /></el-icon>
                  </template>
                  <template #suffix>
                    <el-tooltip content="Search Help" placement="top">
                      <el-icon 
                        class="search-help-icon" 
                        @click="toggleSearchHelp"
                      >
                        <QuestionFilled />
                      </el-icon>
                    </el-tooltip>
                  </template>
                </el-input>
                
                <!-- Search Help Dropdown -->
                <div 
                  v-show="showSearchHelp" 
                  class="search-help-dropdown"
                  @mousedown.prevent
                >
                  <div class="search-help-title">Search Examples:</div>
                  <div class="search-examples">
                    <div 
                      class="search-example" 
                      @click="applySearchExample('AZ:us-east-1a')"
                    >
                      <code>AZ:us-east-1a</code>
                      <span>Find by tag</span>
                    </div>
                    <div 
                      class="search-example" 
                      @click="applySearchExample('10.0.1')"
                    >
                      <code>10.0.1</code>
                      <span>CIDR contains</span>
                    </div>
                    <div 
                      class="search-example" 
                      @click="applySearchExample('10.0.1.0/24')"
                    >
                      <code>10.0.1.0/24</code>
                      <span>Exact CIDR match</span>
                    </div>
                    <div 
                      class="search-example" 
                      @click="applySearchExample('Name:prod')"
                    >
                      <code>Name:prod</code>
                      <span>Tag key:value</span>
                    </div>
                    <div 
                      class="search-example" 
                      @click="applySearchExample('AZ:us-east-1a 10.0.1')"
                    >
                      <code>AZ:us-east-1a 10.0.1</code>
                      <span>Multiple terms (AND)</span>
                    </div>
                  </div>
                  <div class="search-help-note">
                    💡 Use <strong>tag:value</strong> format for specific tag searches
                  </div>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
    
    <!-- Main Content -->
    <div class="main-content">
      <div class="prefixes-readonly">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>Prefix Query (Read-Only)</span>
              <el-tag type="info" size="large">
                <el-icon><View /></el-icon>
                View Only
              </el-tag>
            </div>
          </template>
          
          <!-- View Toggle Subnav -->
          <div class="view-subnav">
            <el-radio-group v-model="viewMode" @change="loadData" size="default">
              <el-radio-button label="list">
                <el-icon><List /></el-icon>
                List View
              </el-radio-button>
              <el-radio-button label="tree">
                <el-icon><Share /></el-icon>
                Tree View
              </el-radio-button>
            </el-radio-group>
          </div>
      
      <!-- List View -->
      <div v-if="viewMode === 'list'">
        <el-table
          :data="prefixes"
          v-loading="loading"
          style="width: 100%"
          @sort-change="handleSortChange"
        >
          <el-table-column label="CIDR" width="150">
            <template #default="scope">
              <div class="cidr-cell">
                <router-link 
                  :to="`/prefixes/${scope.row.prefix_id}`"
                  class="cidr-link"
                >
                  <el-text 
                    :type="scope.row.tags.deleted_from_aws ? 'danger' : 'primary'"
                    :class="{ 'deleted-prefix': scope.row.tags.deleted_from_aws }"
                  >
                    {{ scope.row.cidr }}
                  </el-text>
                </router-link>
                <el-tag 
                  v-if="scope.row.tags.deleted_from_aws" 
                  type="danger" 
                  size="small" 
                  style="margin-left: 5px;"
                >
                  DELETED
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="VRF" width="280">
            <template #default="scope">
              <div class="vrf-info">
                <div class="vrf-primary">{{ formatVRFDisplay(scope.row.vrf_id) }}</div>
                <div v-if="getVRFDetails(scope.row.vrf_id)" class="vrf-details">
                  {{ getVRFDetails(scope.row.vrf_id) }}
                </div>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Source" width="80">
            <template #default="scope">
              <el-tag :type="scope.row.source === 'manual' ? 'primary' : 'success'">
                {{ scope.row.source }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="Routable" width="100">
            <template #default="scope">
              <el-icon v-if="scope.row.routable" color="green"><Check /></el-icon>
              <el-icon v-else color="red"><Close /></el-icon>
            </template>
          </el-table-column>
          <el-table-column prop="parent_prefix_id" label="Parent" width="200" />
          <el-table-column label="Tags" min-width="200">
            <template #default="scope">
              <el-tag
                v-for="(value, key) in scope.row.tags"
                :key="key"
                size="small"
                class="tag-item"
              >
                {{ key }}: {{ value }}
              </el-tag>
            </template>
          </el-table-column>
          <!-- No Actions column for read-only view -->
        </el-table>
        
        <!-- Pagination -->
        <div class="pagination-container">
          <el-pagination
            v-model:current-page="pagination.currentPage"
            v-model:page-size="pagination.pageSize"
            :page-sizes="pagination.pageSizes"
            :total="pagination.total"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
      
      <!-- Tree View -->
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
                <el-icon v-if="data.routable" color="green" class="node-icon"><Check /></el-icon>
                <el-icon v-else color="red" class="node-icon"><Close /></el-icon>
                <div class="node-vrf">
                  <div class="vrf-primary">{{ formatVRFDisplay(data.vrf_id) }}</div>
                  <div v-if="getVRFDetails(data.vrf_id)" class="vrf-details">
                    {{ getVRFDetails(data.vrf_id) }}
                  </div>
                </div>
              </div>
              <!-- No actions for read-only view -->
            </div>
          </template>
        </el-tree>
      </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
import { Search, List, Share, Check, Close, QuestionFilled, View, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { prefixAPI, vrfAPI } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'PrefixesReadOnly',
  components: {
    Search, List, Share, Check, Close, QuestionFilled, View, ArrowLeft, ArrowRight
  },
  data() {
    return {
      loading: false,
      viewMode: 'list',
      prefixes: [],
      treeData: [],
      vrfs: [],
      filters: {
        vrfIds: [], // Changed to array for multiple selection
        source: '',
        routable: '',
        search: '',
        includeDeleted: false
      },
      // Pagination
      pagination: {
        currentPage: 1,
        pageSize: 50,
        total: 0,
        pageSizes: [10, 20, 50, 100, 200]
      },
      treeProps: {
        children: 'children',
        label: 'cidr'
      },
      searchTimeout: null,
      showSearchHelp: false,
      searchHelpTimeout: null,
      showSidebar: true // Sidebar visibility state
    }
  },
  async mounted() {
    await this.loadVRFs()
    
    // Handle query parameters from URL
    if (this.$route.query.vrf_id) {
      // Convert single vrf_id query param to array format
      this.filters.vrfIds = [this.$route.query.vrf_id]
    }
    if (this.$route.query.source) {
      this.filters.source = this.$route.query.source
    }
    if (this.$route.query.search) {
      this.filters.search = this.$route.query.search
    }
    
    await this.loadData()
  },
  methods: {
    async loadData() {
      if (this.viewMode === 'list') {
        await this.loadPrefixes()
      } else {
        await this.loadTree()
      }
    },
    
    async loadPrefixes() {
      this.loading = true
      try {
        const params = {}
        let allPrefixes = []
        
        // Handle multiple VRF selection
        if (this.filters.vrfIds && this.filters.vrfIds.length > 0) {
          // For multiple VRFs, we need to make multiple API calls and combine results
          for (const vrfId of this.filters.vrfIds) {
            const vrfParams = { ...params, vrf_id: vrfId }
            if (this.filters.source) vrfParams.source = this.filters.source
            if (this.filters.routable !== '') vrfParams.routable = this.filters.routable
            if (this.filters.search) vrfParams.search = this.filters.search
            if (this.filters.includeDeleted) vrfParams.include_deleted = this.filters.includeDeleted
            
            const response = await prefixAPI.getPrefixes(vrfParams)
            allPrefixes.push(...response.data)
          }
          
          // Remove duplicates based on prefix_id
          allPrefixes = allPrefixes.filter((prefix, index, self) => 
            index === self.findIndex(p => p.prefix_id === prefix.prefix_id)
          )
        } else {
          // No VRF filter or empty selection - load all prefixes
          if (this.filters.source) params.source = this.filters.source
          if (this.filters.routable !== '') params.routable = this.filters.routable
          if (this.filters.search) params.search = this.filters.search
          if (this.filters.includeDeleted) params.include_deleted = this.filters.includeDeleted
          
          const response = await prefixAPI.getPrefixes(params)
          allPrefixes = response.data
        }
        
        // Apply pagination
        this.pagination.total = allPrefixes.length
        const startIndex = (this.pagination.currentPage - 1) * this.pagination.pageSize
        const endIndex = startIndex + this.pagination.pageSize
        this.prefixes = allPrefixes.slice(startIndex, endIndex)
        
      } catch (error) {
        ElMessage.error('Failed to load prefixes')
        console.error(error)
      } finally {
        this.loading = false
      }
    },
    
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
          // No VRF filter - load tree for all VRFs (don't pass vrf_id parameter)
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
    },
    
    async loadVRFs() {
      try {
        const response = await vrfAPI.getVRFs()
        this.vrfs = response.data
      } catch (error) {
        console.error('Failed to load VRFs:', error)
      }
    },
    
    debounceSearch() {
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => {
        // Search filter only applies to list view, not tree view
        if (this.viewMode === 'list') {
          this.loadPrefixes()
        }
        // In tree view, search is ignored to preserve parent-child relationships
      }, 500)
    },
    
    handleSortChange({ prop, order }) {
      if (prop === 'cidr') {
        this.prefixes.sort((a, b) => {
          const comparison = a.cidr.localeCompare(b.cidr)
          return order === 'ascending' ? comparison : -comparison
        })
      }
    },
    
    // Pagination handlers
    handleSizeChange(newSize) {
      this.pagination.pageSize = newSize
      this.pagination.currentPage = 1 // Reset to first page when changing page size
      this.loadData()
    },
    
    handleCurrentChange(newPage) {
      this.pagination.currentPage = newPage
      this.loadData()
    },

    // Search help methods
    toggleSearchHelp() {
      this.showSearchHelp = !this.showSearchHelp
    },

    hideSearchHelp() {
      // Delay hiding to allow clicking on examples
      this.searchHelpTimeout = setTimeout(() => {
        this.showSearchHelp = false
      }, 200)
    },

    applySearchExample(example) {
      clearTimeout(this.searchHelpTimeout)
      this.filters.search = example
      this.showSearchHelp = false
      this.debounceSearch()
    },

    // VRF formatting methods
    formatVRFDisplay(vrfId) {
      // Return the VRF ID as-is for consistency and completeness
      // VRF IDs contain all necessary info: provider_account_vpcid
      return vrfId
    },

    getVRFDetails(vrfId) {
      // No additional details needed since VRF ID is now shown in full
      // VRF ID format: provider_account_vpcid contains all info
      return null
    },

    parseVRFId(vrfId) {
      // Parse auto-created VRF IDs
      // Format: provider_account_vpcid (e.g., aws_123456789_vpc-abc123)
      const providerPattern = /^(aws|azure|gcp|other)_([^_]+)_(.+)$/
      const match = vrfId.match(providerPattern)
      
      if (match) {
        return {
          provider: match[1],
          account: match[2] !== 'unknown' ? match[2] : null,
          vpcId: match[3]
        }
      }

      // Legacy format: vrf:uuid
      if (vrfId.startsWith('vrf:')) {
        const uuid = vrfId.substring(4)
        return {
          provider: 'legacy',
          account: null,
          vpcId: uuid.substring(0, 8) + '...' // Show first 8 chars of UUID
        }
      }

      // Manual VRF - return null to show original ID
      return null
    }
  }
}
</script>

<style scoped>
.prefixes-container {
  display: flex;
  position: relative;
  width: 100%;
  min-height: 100vh;
}

.sidebar-toggle {
  position: absolute;
  left: 300px;
  top: 20px;
  z-index: 1001;
  background: #409eff;
  color: white;
  width: 24px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 0 4px 4px 0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  transition: left 0.3s ease;
}

.prefixes-container.sidebar-hidden .sidebar-toggle {
  left: 0;
}

.sidebar-toggle:hover {
  background: #66b1ff;
}

.sidebar {
  width: 300px;
  min-width: 300px;
  background: #fff;
  border-right: 1px solid #dcdfe6;
  transition: transform 0.3s ease, min-width 0.3s ease, width 0.3s ease;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  z-index: 1000;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
}

.sidebar-collapsed {
  width: 0 !important;
  min-width: 0 !important;
  overflow: hidden;
  border-right: none;
}

.sidebar-content {
  padding: 20px;
}

.sidebar-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.sidebar-filters {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-label {
  font-size: 14px;
  font-weight: 500;
  color: #606266;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  min-width: 0;
  transition: flex 0.3s ease;
}

.prefixes-readonly {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  margin-bottom: 20px;
}

.filter-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  font-style: italic;
}

.search-container {
  position: relative;
}

.search-help-icon {
  cursor: pointer;
  color: #909399;
  transition: color 0.3s;
}

.search-help-icon:hover {
  color: #409eff;
}

.search-help-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  z-index: 1000;
  padding: 12px;
  margin-top: 4px;
}

.search-help-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
  font-size: 13px;
}

.search-examples {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.search-example {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 8px;
  border-radius: 3px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.search-example:hover {
  background-color: #f5f7fa;
}

.search-example code {
  background: #f1f2f3;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 12px;
  color: #e6a23c;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
}

.search-example span {
  font-size: 12px;
  color: #909399;
}

.search-help-note {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
  font-size: 12px;
  color: #606266;
}

.view-subnav {
  background: #fff;
  padding: 15px 20px;
  margin-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.view-toggle {
  margin-bottom: 20px;
}

.tag-item {
  margin-right: 5px;
  margin-bottom: 5px;
}

.tree-view {
  max-height: 600px;
  overflow-y: auto;
}

.tree-node {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 5px 0;
}

.node-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.node-cidr {
  font-weight: bold;
  color: #409EFF;
}

.node-icon {
  font-size: 16px;
}

.node-vrf {
  color: #909399;
  font-size: 12px;
}

/* VRF display styles */
.vrf-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.vrf-primary {
  font-weight: 600;
  color: #409EFF;
  font-size: 13px;
}

.vrf-details {
  font-size: 11px;
  color: #909399;
  font-style: italic;
}

/* Pagination styles */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding: 20px 0;
}

/* Deleted prefix styles */
.cidr-cell {
  display: flex;
  align-items: center;
}

.deleted-prefix {
  text-decoration: line-through;
  opacity: 0.7;
}

.node-vrf .vrf-primary {
  font-size: 12px;
}

.node-vrf .vrf-details {
  font-size: 10px;
}

.vrf-option {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.vrf-option .vrf-primary {
  font-size: 13px;
}

.vrf-option .vrf-details {
  font-size: 11px;
}

/* Clickable CIDR styles */
.cidr-link {
  text-decoration: none;
  cursor: pointer;
}

.cidr-link:hover .node-cidr {
  text-decoration: underline;
}
</style>
