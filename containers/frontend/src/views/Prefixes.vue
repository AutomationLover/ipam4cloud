<template>
  <div class="prefixes">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>Prefix Management</span>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            Create Prefix
          </el-button>
        </div>
      </template>
      
      <!-- Filters -->
      <el-row :gutter="20" class="filters">
        <el-col :span="6">
          <el-select 
            v-model="filters.vrfIds" 
            placeholder="Select VRFs" 
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable 
            @change="loadPrefixes"
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
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.source" placeholder="Source" clearable @change="loadPrefixes">
            <el-option label="All Sources" value="" />
            <el-option label="Manual" value="manual" />
            <el-option label="VPC" value="vpc" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-select v-model="filters.routable" placeholder="Routable" clearable @change="loadPrefixes">
            <el-option label="All" value="" />
            <el-option label="Routable" :value="true" />
            <el-option label="Non-routable" :value="false" />
          </el-select>
        </el-col>
      </el-row>
      
      <el-row :gutter="20" style="margin-top: 10px;">
        <el-col :span="6">
          <el-checkbox 
            v-model="filters.includeDeleted" 
            @change="loadData"
            style="margin-top: 8px;"
          >
            <span style="color: #f56c6c;">Show VPC Subnets Deleted from AWS</span>
          </el-checkbox>
        </el-col>
        <el-col :span="18">
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
        </el-col>
      </el-row>
      
      <!-- View Toggle -->
      <el-row class="view-toggle">
        <el-col :span="24">
          <el-radio-group v-model="viewMode" @change="loadData">
            <el-radio-button label="list">
              <el-icon><List /></el-icon>
              List View
            </el-radio-button>
            <el-radio-button label="tree">
              <el-icon><Share /></el-icon>
              Tree View
            </el-radio-button>
          </el-radio-group>
        </el-col>
      </el-row>
      
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
          <el-table-column label="Actions" width="280">
            <template #default="scope">
              <el-button 
                v-if="canCreateChildPrefix(scope.row)"
                size="small" 
                @click="createChildPrefix(scope.row)"
              >
                <el-icon><Plus /></el-icon>
                Child
              </el-button>
              <el-button 
                v-if="scope.row.source !== 'vpc'"
                size="small" 
                type="primary" 
                @click="associateVPC(scope.row)"
                :disabled="!canAssociateVPC(scope.row)"
                :title="getVPCAssociationTooltip(scope.row)"
              >
                <el-icon><Link /></el-icon>
                VPC
              </el-button>
              <el-button 
                v-if="scope.row.source === 'manual'" 
                size="small" 
                type="warning" 
                @click="editPrefix(scope.row)"
              >
                <el-icon><Edit /></el-icon>
                Edit
              </el-button>
              <el-button 
                v-if="scope.row.source === 'manual'" 
                size="small" 
                type="danger" 
                @click="deletePrefix(scope.row)"
              >
                <el-icon><Delete /></el-icon>
                Delete
              </el-button>
            </template>
          </el-table-column>
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
              <div class="node-actions">
                <el-button 
                  v-if="canCreateChildPrefix(data)"
                  size="small" 
                  @click="createChildPrefix(data)"
                >
                  <el-icon><Plus /></el-icon>
                </el-button>
                <el-button 
                  v-if="data.source !== 'vpc'"
                  size="small" 
                  type="primary" 
                  @click="associateVPC(data)"
                  :disabled="!canAssociateVPC(data)"
                  :title="getVPCAssociationTooltip(data)"
                >
                  <el-icon><Link /></el-icon>
                </el-button>
                <el-button 
                  v-if="data.source === 'manual'" 
                  size="small" 
                  type="warning" 
                  @click="editPrefix(data)"
                >
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button 
                  v-if="data.source === 'manual'" 
                  size="small" 
                  type="danger" 
                  @click="deletePrefix(data)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </template>
        </el-tree>
      </div>
    </el-card>
    
    <!-- Create Prefix Dialog -->
    <el-dialog v-model="showCreateDialog" title="Create New Prefix" width="600px">
      <el-form :model="newPrefix" :rules="prefixRules" ref="prefixForm" label-width="120px">
        <el-form-item label="VRF" prop="vrf_id">
          <el-select v-model="newPrefix.vrf_id" placeholder="Select VRF">
            <el-option
              v-for="vrf in vrfs"
              :key="vrf.vrf_id"
              :label="vrf.vrf_id"
              :value="vrf.vrf_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="CIDR" prop="cidr">
          <el-input v-model="newPrefix.cidr" placeholder="e.g., 10.0.0.0/24" />
        </el-form-item>
        <el-form-item label="Parent Prefix">
          <el-select 
            v-model="newPrefix.parent_prefix_id" 
            placeholder="Select parent prefix (leave empty for root prefix)"
            clearable
            filterable
            :loading="loadingParentPrefixes"
          >
            <el-option
              v-for="prefix in filteredParentPrefixes"
              :key="prefix.prefix_id"
              :label="`${prefix.cidr} (${prefix.vrf_id})`"
              :value="prefix.prefix_id"
            >
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>{{ prefix.cidr }}</span>
                <span style="color: #8492a6; font-size: 12px;">{{ prefix.vrf_id }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="Routable">
          <el-switch v-model="newPrefix.routable" />
        </el-form-item>
        <el-form-item label="VPC Children">
          <el-switch v-model="newPrefix.vpc_children_type_flag" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input
            v-model="tagsInput"
            type="textarea"
            placeholder="JSON format: {&quot;env&quot;: &quot;prod&quot;, &quot;team&quot;: &quot;ops&quot;}"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createPrefix" :loading="creating">Create</el-button>
      </template>
    </el-dialog>
    
    <!-- Edit Prefix Dialog -->
    <el-dialog v-model="showEditDialog" title="Edit Prefix" width="600px">
      <el-form :model="editPrefixData" :rules="prefixRules" ref="editPrefixForm" label-width="120px">
        <el-form-item label="VRF" prop="vrf_id">
          <el-select v-model="editPrefixData.vrf_id" placeholder="Select VRF">
            <el-option
              v-for="vrf in vrfs"
              :key="vrf.vrf_id"
              :label="vrf.vrf_id"
              :value="vrf.vrf_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="CIDR" prop="cidr">
          <el-input v-model="editPrefixData.cidr" placeholder="e.g., 10.0.0.0/24" />
        </el-form-item>
        <el-form-item label="Parent Prefix">
          <el-select 
            v-model="editPrefixData.parent_prefix_id" 
            placeholder="Select parent prefix (leave empty for root prefix)"
            clearable
            filterable
            :loading="loadingParentPrefixes"
          >
            <el-option
              v-for="prefix in availableParentPrefixes"
              :key="prefix.prefix_id"
              :label="`${prefix.cidr} (${prefix.vrf_id})`"
              :value="prefix.prefix_id"
            >
              <div style="display: flex; justify-content: space-between; align-items: center;">
                <span>{{ prefix.cidr }}</span>
                <span style="color: #8492a6; font-size: 12px;">{{ prefix.vrf_id }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="Routable">
          <el-switch v-model="editPrefixData.routable" />
        </el-form-item>
        <el-form-item label="VPC Children">
          <el-switch v-model="editPrefixData.vpc_children_type_flag" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input
            v-model="editTagsInput"
            type="textarea"
            placeholder="JSON format: {&quot;env&quot;: &quot;prod&quot;, &quot;team&quot;: &quot;ops&quot;}"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">Cancel</el-button>
        <el-button type="primary" @click="updatePrefix" :loading="updating">Update</el-button>
      </template>
    </el-dialog>

    <!-- VPC Association Dialog -->
    <el-dialog v-model="showVPCDialog" title="Manage VPC Associations" width="800px">
      <!-- Current Associations Section -->
      <div v-if="currentAssociations.length > 0" class="current-associations">
        <h4>Current VPC Associations</h4>
        <el-table :data="currentAssociations" v-loading="loadingAssociations" size="small">
          <el-table-column prop="provider_vpc_id" label="VPC ID" width="150" />
          <el-table-column prop="provider" label="Provider" width="80" />
          <el-table-column prop="vpc_prefix_cidr" label="VPC CIDR" width="120" />
          <el-table-column label="Routable" width="80">
            <template #default="scope">
              <el-icon v-if="scope.row.routable" color="green"><Check /></el-icon>
              <el-icon v-else color="red"><Close /></el-icon>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="Description" min-width="150" />
          <el-table-column label="Actions" width="80">
            <template #default="scope">
              <el-button 
                size="small" 
                type="danger" 
                @click="removeVPCAssociation(scope.row)"
                :loading="scope.row.removing"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-divider />
      </div>
      
      <!-- Add New Association Section -->
      <div class="add-association">
        <h4>Add New VPC Association</h4>
      <el-form :model="vpcAssociation" :rules="vpcRules" ref="vpcForm" label-width="120px">
        <el-form-item label="VPC" prop="vpc_id">
          <el-select v-model="vpcAssociation.vpc_id" placeholder="Select VPC">
            <el-option
                v-for="vpc in availableVPCs"
              :key="vpc.vpc_id"
              :label="`${vpc.provider_vpc_id} (${vpc.provider})`"
              :value="vpc.vpc_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="VPC CIDR" prop="vpc_prefix_cidr">
          <el-input v-model="vpcAssociation.vpc_prefix_cidr" placeholder="e.g., 10.0.0.0/16" />
        </el-form-item>
        <el-form-item label="Routable">
          <el-switch v-model="vpcAssociation.routable" />
        </el-form-item>
      </el-form>
      </div>
      
      <template #footer>
        <el-button @click="showVPCDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createVPCAssociation" :loading="associating">Add Association</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { Plus, Search, List, Share, Check, Close, Link, Edit, Delete, QuestionFilled } from '@element-plus/icons-vue'
import { prefixAPI, vrfAPI, vpcAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Prefixes',
  components: {
    Plus, Search, List, Share, Check, Close, Link, Edit, Delete, QuestionFilled
  },
  data() {
    return {
      loading: false,
      creating: false,
      updating: false,
      associating: false,
      viewMode: 'list',
      prefixes: [],
      treeData: [],
      vrfs: [],
      vpcs: [],
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
      showCreateDialog: false,
      showEditDialog: false,
      showVPCDialog: false,
      selectedPrefix: null,
      newPrefix: {
        vrf_id: '',
        cidr: '',
        parent_prefix_id: '',
        routable: true,
        vpc_children_type_flag: false,
        tags: {}
      },
      editPrefixData: {
        vrf_id: '',
        cidr: '',
        parent_prefix_id: '',
        routable: true,
        vpc_children_type_flag: false,
        tags: {}
      },
      vpcAssociation: {
        vpc_id: '',
        vpc_prefix_cidr: '',
        routable: true,
        parent_prefix_id: ''
      },
      tagsInput: '{}',
      editTagsInput: '{}',
      treeProps: {
        children: 'children',
        label: 'cidr'
      },
      prefixRules: {
        vrf_id: [{ required: true, message: 'Please select a VRF', trigger: 'change' }],
        cidr: [{ required: true, message: 'Please enter CIDR', trigger: 'blur' }]
      },
      vpcRules: {
        vpc_id: [{ required: true, message: 'Please select a VPC', trigger: 'change' }],
        vpc_prefix_cidr: [{ required: true, message: 'Please enter VPC CIDR', trigger: 'blur' }]
      },
      searchTimeout: null,
      vpcAssociations: {}, // Cache VPC associations for prefixes
      vpcAssociationRules: {}, // Cache VPC association rules for prefixes
      currentAssociations: [], // Current VPC associations for selected prefix
      loadingAssociations: false,
      availableParentPrefixes: [], // Available parent prefixes for selection
      loadingParentPrefixes: false,
      suggestionTimeout: null,
      showSearchHelp: false,
      searchHelpTimeout: null
    }
  },
  computed: {
    availableVPCs() {
      // Filter out VPCs that are already associated (to prevent duplicates)
      const associatedVPCIds = this.currentAssociations.map(assoc => assoc.vpc_id)
      return this.vpcs.filter(vpc => !associatedVPCIds.includes(vpc.vpc_id))
    },
    
    filteredParentPrefixes() {
      // Filter parent prefixes by selected VRF
      if (!this.newPrefix.vrf_id) {
        return this.availableParentPrefixes
      }
      return this.availableParentPrefixes.filter(prefix => prefix.vrf_id === this.newPrefix.vrf_id)
    }
  },
  
  watch: {
    // Watch for changes in VRF and CIDR to auto-suggest parent
    'newPrefix.vrf_id'() {
      this.debouncedSuggestParent()
    },
    'newPrefix.cidr'() {
      this.debouncedSuggestParent()
    }
  },
  async mounted() {
    await this.loadVRFs()
    await this.loadVPCs()
    
    // Handle query parameters for VRF filtering
    if (this.$route.query.vrf_id) {
      // Convert single vrf_id query param to array format
      this.filters.vrfIds = [this.$route.query.vrf_id]
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
          // No VRF filter - load tree for all VRFs (pass null/empty)
          const params = { vrf_id: '' }
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
    
    async loadVPCs() {
      try {
        const response = await vpcAPI.getVPCs()
        this.vpcs = response.data
      } catch (error) {
        console.error('Failed to load VPCs:', error)
      }
    },
    
    debounceSearch() {
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => {
        this.loadData()
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
    
    async openCreateDialog() {
      // Reset form
      this.newPrefix = {
        vrf_id: '',
        cidr: '',
        parent_prefix_id: '',
        routable: true,
        vpc_children_type_flag: false,
        tags: {}
      }
      this.tagsInput = '{}'
      await this.loadAvailableParentPrefixes()
      this.showCreateDialog = true
    },
    
    async createChildPrefix(parentPrefix) {
      this.newPrefix = {
        vrf_id: parentPrefix.vrf_id,
        cidr: '',
        parent_prefix_id: parentPrefix.prefix_id,
        routable: parentPrefix.routable,
        vpc_children_type_flag: false,
        tags: {}
      }
      this.tagsInput = '{}'
      await this.loadAvailableParentPrefixes()
      this.showCreateDialog = true
    },
    
    async associateVPC(prefix) {
      // Check if association is allowed before opening dialog
      const canAssociate = await this.checkVPCAssociationRules(prefix.prefix_id)
      if (!canAssociate.can_associate) {
        ElMessage.error(canAssociate.reason)
        return
      }
      
      this.selectedPrefix = prefix
      this.vpcAssociation = {
        vpc_id: '',
        vpc_prefix_cidr: prefix.cidr,
        routable: prefix.routable,
        parent_prefix_id: prefix.prefix_id
      }
      
      // Load current associations
      await this.loadCurrentAssociations(prefix.prefix_id)
      
      this.showVPCDialog = true
    },
    
    async createPrefix() {
      try {
        await this.$refs.prefixForm.validate()
        
        // Parse tags
        try {
          this.newPrefix.tags = JSON.parse(this.tagsInput)
        } catch (e) {
          ElMessage.error('Invalid JSON format for tags')
          return
        }
        
        // Prepare data for API call - convert empty parent_prefix_id to null for root prefixes
        const prefixData = {
          ...this.newPrefix,
          parent_prefix_id: this.newPrefix.parent_prefix_id || null
        }
        
        this.creating = true
        await prefixAPI.createPrefix(prefixData)
        ElMessage.success('Prefix created successfully')
        this.showCreateDialog = false
        await this.loadData()
      } catch (error) {
        let errorMessage = 'Failed to create prefix'
        
        if (error.response?.data?.detail) {
          const detail = error.response.data.detail
          if (detail.includes('duplicate key') || detail.includes('already exists')) {
            errorMessage = `Prefix ${this.newPrefix.cidr} already exists in VRF ${this.newPrefix.vrf_id}`
          } else if (detail.includes('violates unique constraint')) {
            errorMessage = `Prefix ${this.newPrefix.cidr} already exists`
          } else if (detail.includes('Parent prefix') && detail.includes('not found')) {
            errorMessage = 'Selected parent prefix not found'
          } else if (detail.includes('must be within parent')) {
            errorMessage = `CIDR ${this.newPrefix.cidr} must be contained within the selected parent prefix`
          } else if (detail.includes('Nonroutable parent cannot have routable child')) {
            errorMessage = 'Cannot create routable prefix under non-routable parent'
          } else {
            errorMessage = `Failed to create prefix: ${detail}`
          }
        } else if (error.response?.status === 400) {
          errorMessage = 'Invalid prefix data. Please check your input.'
        }
        
        ElMessage.error(errorMessage)
        console.error(error)
      } finally {
        this.creating = false
      }
    },
    
    async editPrefix(prefix) {
      this.selectedPrefix = prefix
      this.editPrefixData = {
        vrf_id: prefix.vrf_id,
        cidr: prefix.cidr,
        parent_prefix_id: prefix.parent_prefix_id || '',
        routable: prefix.routable,
        vpc_children_type_flag: prefix.vpc_children_type_flag,
        tags: { ...prefix.tags }
      }
      this.editTagsInput = JSON.stringify(prefix.tags, null, 2)
      await this.loadAvailableParentPrefixes()
      this.showEditDialog = true
    },
    
    async updatePrefix() {
      try {
        await this.$refs.editPrefixForm.validate()
        
        // Parse tags
        try {
          this.editPrefixData.tags = JSON.parse(this.editTagsInput)
        } catch (e) {
          ElMessage.error('Invalid JSON format for tags')
          return
        }
        
        // Prepare data for API call - convert empty parent_prefix_id to null
        const updateData = {
          ...this.editPrefixData,
          parent_prefix_id: this.editPrefixData.parent_prefix_id || null
        }
        
        this.updating = true
        await prefixAPI.updatePrefix(this.selectedPrefix.prefix_id, updateData)
        ElMessage.success('Prefix updated successfully')
        this.showEditDialog = false
        await this.loadData()
      } catch (error) {
        ElMessage.error('Failed to update prefix: ' + (error.response?.data?.detail || error.message))
        console.error(error)
      } finally {
        this.updating = false
      }
    },
    
    async deletePrefix(prefix) {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete prefix ${prefix.cidr}? This action cannot be undone.`,
          'Confirm Delete',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        await prefixAPI.deletePrefix(prefix.prefix_id)
        ElMessage.success('Prefix deleted successfully')
        await this.loadData()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete prefix: ' + (error.response?.data?.detail || error.message))
          console.error(error)
        }
      }
    },

    async createVPCAssociation() {
      try {
        await this.$refs.vpcForm.validate()
        
        this.associating = true
        const response = await vpcAPI.createVPCAssociation(this.vpcAssociation)
        
        // Show success message with additional info if tags were updated
        if (response.data.tags_updated) {
          ElMessage.success('VPC associated successfully and associated_vpc tag added')
        } else {
        ElMessage.success('VPC associated successfully')
        }
        
        // Reset form
        this.vpcAssociation = {
          vpc_id: '',
          vpc_prefix_cidr: this.selectedPrefix.cidr,
          routable: this.selectedPrefix.routable,
          parent_prefix_id: this.selectedPrefix.prefix_id
        }
        
        // Reload current associations to show the new one
        await this.loadCurrentAssociations(this.selectedPrefix.prefix_id)
        
        // Clear caches to force refresh
        this.vpcAssociations = {}
        this.vpcAssociationRules = {}
        await this.loadData()
        
        // Don't close dialog automatically - let user add more or close manually
      } catch (error) {
        const errorMessage = error.response?.data?.detail || 'Failed to associate VPC'
        ElMessage.error(errorMessage)
        console.error(error)
      } finally {
        this.associating = false
      }
    },
    
    canCreateChildPrefix(prefix) {
      // Rule 1: VPC-sourced prefixes cannot have child prefixes
      if (prefix.source === 'vpc') {
        return false
      }
      
      // Rule 2: Manual prefixes associated with VPC cannot have child prefixes
      if (prefix.source === 'manual') {
        // Check if this prefix is associated with any VPC
        // We'll use a simple heuristic: if vpc_children_type_flag is true, it's likely associated
        if (prefix.vpc_children_type_flag) {
          return false
        }
      }
      
      // Rule 3: Manual prefixes not associated with VPC can have child prefixes
      return true
    },
    
    async checkVPCAssociationRules(prefixId) {
      // Check cache first
      if (this.vpcAssociationRules[prefixId]) {
        return this.vpcAssociationRules[prefixId]
      }
      
      try {
        const response = await prefixAPI.canAssociateVPC(prefixId)
        this.vpcAssociationRules[prefixId] = response.data
        return response.data
      } catch (error) {
        console.error('Failed to check VPC association rules:', error)
        return { can_associate: false, reason: 'Failed to check association rules' }
      }
    },
    
    canAssociateVPC(prefix) {
      // Quick check based on known rules
      // Rule 1: VPC-sourced prefixes cannot associate to VPC
      if (prefix.source === 'vpc') {
        return false
      }
      
      // For more complex rules (like checking existing associations), 
      // we'll rely on the backend validation
      return true
    },
    
    getVPCAssociationTooltip(prefix) {
      // Rule 1: VPC-sourced prefixes cannot associate to VPC
      if (prefix.source === 'vpc') {
        return 'Prefixes whose source is cloud VPC cannot associate to VPC'
      }
      
      // Rule 2: Routable prefixes can only associate to one VPC ID
      if (prefix.routable) {
        return 'Routable prefixes can only associate to one VPC ID'
      }
      
      // Rule 3: Non-routable prefixes can associate to multiple VPC IDs
      return 'Non-routable prefixes can associate to multiple VPC IDs'
    },
    
    async loadCurrentAssociations(prefixId) {
      this.loadingAssociations = true
      try {
        const response = await prefixAPI.getPrefixVPCAssociations(prefixId)
        this.currentAssociations = response.data.map(assoc => ({
          ...assoc,
          removing: false // Add loading state for remove button
        }))
      } catch (error) {
        console.error('Failed to load current associations:', error)
        ElMessage.error('Failed to load current VPC associations')
        this.currentAssociations = []
      } finally {
        this.loadingAssociations = false
      }
    },
    
    async removeVPCAssociation(association) {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to remove the association with VPC ${association.provider_vpc_id}?`,
          'Confirm Remove Association',
          {
            confirmButtonText: 'Remove',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        // Set loading state for this specific association
        association.removing = true
        
        const response = await vpcAPI.removeVPCAssociation(association.association_id)
        
        if (response.data.tags_updated) {
          ElMessage.success(`VPC association removed and associated_vpc tag updated`)
        } else {
          ElMessage.success('VPC association removed successfully')
        }
        
        // Reload current associations
        await this.loadCurrentAssociations(this.selectedPrefix.prefix_id)
        
        // Clear caches and reload data
        this.vpcAssociations = {}
        this.vpcAssociationRules = {}
        await this.loadData()
        
      } catch (error) {
        if (error !== 'cancel') {
          const errorMessage = error.response?.data?.detail || 'Failed to remove VPC association'
          ElMessage.error(errorMessage)
          console.error(error)
        }
      } finally {
        association.removing = false
      }
    },
    
    async loadAvailableParentPrefixes() {
      this.loadingParentPrefixes = true
      try {
        // Load all manual prefixes that can be parents
        const response = await prefixAPI.getPrefixes({ source: 'manual' })
        this.availableParentPrefixes = response.data.sort((a, b) => {
          // Sort by VRF first, then by CIDR
          if (a.vrf_id !== b.vrf_id) {
            return a.vrf_id.localeCompare(b.vrf_id)
          }
          return a.cidr.localeCompare(b.cidr)
        })
      } catch (error) {
        console.error('Failed to load parent prefixes:', error)
        ElMessage.error('Failed to load available parent prefixes')
        this.availableParentPrefixes = []
      } finally {
        this.loadingParentPrefixes = false
      }
    },
    
    debouncedSuggestParent() {
      clearTimeout(this.suggestionTimeout)
      this.suggestionTimeout = setTimeout(() => {
        this.suggestParentPrefix()
      }, 500)
    },
    
    suggestParentPrefix() {
      // Auto-suggest parent prefix based on CIDR containment
      if (!this.newPrefix.vrf_id || !this.newPrefix.cidr || !this.availableParentPrefixes.length) {
        return
      }
      
      try {
        // Parse the new CIDR
        const newCidr = this.newPrefix.cidr.trim()
        if (!newCidr.includes('/')) {
          return // Invalid CIDR format
        }
        
        // Find potential parents in the same VRF that can contain this CIDR
        const potentialParents = this.availableParentPrefixes
          .filter(prefix => prefix.vrf_id === this.newPrefix.vrf_id)
          .filter(prefix => {
            try {
              return this.isSubnet(newCidr, prefix.cidr)
            } catch (e) {
              return false
            }
          })
          .sort((a, b) => {
            // Sort by prefix length (most specific first)
            const aLength = parseInt(a.cidr.split('/')[1])
            const bLength = parseInt(b.cidr.split('/')[1])
            return bLength - aLength // Descending order (more specific first)
          })
        
        // Auto-select the most specific parent (if any)
        if (potentialParents.length > 0 && !this.newPrefix.parent_prefix_id) {
          this.newPrefix.parent_prefix_id = potentialParents[0].prefix_id
          console.log(`Auto-suggested parent: ${potentialParents[0].cidr} for ${newCidr}`)
        }
      } catch (error) {
        console.log('Error in parent suggestion:', error)
        // Ignore errors in auto-suggestion
      }
    },
    
    isSubnet(childCidr, parentCidr) {
      // Simple CIDR containment check
      try {
        const [childNetwork, childMask] = childCidr.split('/')
        const [parentNetwork, parentMask] = parentCidr.split('/')
        
        const childMaskNum = parseInt(childMask)
        const parentMaskNum = parseInt(parentMask)
        
        // Child must have longer or equal mask
        if (childMaskNum < parentMaskNum) {
          return false
        }
        
        // Convert IPs to numbers for comparison
        const childIp = this.ipToNumber(childNetwork)
        const parentIp = this.ipToNumber(parentNetwork)
        
        // Calculate network addresses
        const parentNetworkSize = Math.pow(2, 32 - parentMaskNum)
        const parentNetworkStart = Math.floor(parentIp / parentNetworkSize) * parentNetworkSize
        const parentNetworkEnd = parentNetworkStart + parentNetworkSize - 1
        
        return childIp >= parentNetworkStart && childIp <= parentNetworkEnd
      } catch (error) {
        return false
      }
    },
    
    ipToNumber(ip) {
      return ip.split('.').reduce((acc, octet) => (acc << 8) + parseInt(octet), 0) >>> 0
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
.prefixes {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  margin-bottom: 20px;
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

.node-actions {
  display: flex;
  gap: 5px;
}

.current-associations h4,
.add-association h4 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #409EFF;
}

.current-associations {
  margin-bottom: 20px;
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

.node-vrf .vrf-primary {
  font-size: 12px;
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
