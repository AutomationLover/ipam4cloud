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
        </el-col>
        <el-col :span="6">
          <el-select 
            v-model="filters.source" 
            placeholder="Source" 
            clearable 
            :disabled="viewMode === 'tree'"
            @change="loadPrefixes"
          >
            <el-option label="All Sources" value="" />
            <el-option label="Manual" value="manual" />
            <el-option label="VPC" value="vpc" />
          </el-select>
          <div v-if="viewMode === 'tree'" class="filter-hint">List view only</div>
        </el-col>
        <el-col :span="6">
          <el-select 
            v-model="filters.routable" 
            placeholder="Routable" 
            clearable 
            :disabled="viewMode === 'tree'"
            @change="loadPrefixes"
          >
            <el-option label="All" value="" />
            <el-option label="Routable" :value="true" />
            <el-option label="Non-routable" :value="false" />
          </el-select>
          <div v-if="viewMode === 'tree'" class="filter-hint">List view only</div>
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
            :placeholder="viewMode === 'tree' ? 'Search available in list view only' : 'Search prefixes, tags...'"
            :disabled="viewMode === 'tree'"
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
    <el-dialog v-model="showCreateDialog" title="Create New Prefix" width="700px">
      <el-tabs v-model="createMode" @tab-change="onCreateModeChange">
        <!-- Manual Prefix Creation Tab -->
        <el-tab-pane label="Manual CIDR" name="manual">
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
              <el-input v-model="newPrefix.cidr" placeholder="e.g., 10.0.0.0/24 or 2001:db8::/32" />
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
        </el-tab-pane>

        <!-- Automatic Subnet Allocation Tab -->
        <el-tab-pane label="Auto Allocate Subnet" name="allocate">
          <div class="allocation-header">
            <el-alert
              title="AWS IPAM-Style Subnet Allocation"
              type="info"
              description="Automatically find and allocate the first available subnet of specified size from matching parent prefixes."
              show-icon
              :closable="false"
              style="margin-bottom: 20px;"
            />
          </div>
          
          <el-form :model="subnetAllocation" :rules="allocationRules" ref="allocationForm" label-width="140px">
            <el-form-item label="VRF" prop="vrf_id">
              <el-select v-model="subnetAllocation.vrf_id" placeholder="Select VRF" @change="onAllocationVRFChange">
                <el-option
                  v-for="vrf in vrfs"
                  :key="vrf.vrf_id"
                  :label="vrf.vrf_id"
                  :value="vrf.vrf_id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="Subnet Size" prop="subnet_size">
              <el-select v-model="subnetAllocation.subnet_size" placeholder="Select subnet size" @change="updateAllocationPreview">
                <!-- IPv4 options -->
                <el-option-group label="IPv4 Subnet Sizes">
                  <el-option label="/16 (65,536 IPs)" :value="16" />
                  <el-option label="/20 (4,096 IPs)" :value="20" />
                  <el-option label="/24 (256 IPs)" :value="24" />
                  <el-option label="/25 (128 IPs)" :value="25" />
                  <el-option label="/26 (64 IPs)" :value="26" />
                  <el-option label="/27 (32 IPs)" :value="27" />
                  <el-option label="/28 (16 IPs)" :value="28" />
                  <el-option label="/29 (8 IPs)" :value="29" />
                </el-option-group>
                <!-- IPv6 options -->
                <el-option-group label="IPv6 Subnet Sizes">
                  <el-option label="/32 (IPv6 /32)" :value="32" />
                  <el-option label="/40 (IPv6 /40)" :value="40" />
                  <el-option label="/44 (IPv6 /44)" :value="44" />
                  <el-option label="/48 (IPv6 /48)" :value="48" />
                  <el-option label="/52 (IPv6 /52)" :value="52" />
                  <el-option label="/56 (IPv6 /56)" :value="56" />
                  <el-option label="/60 (IPv6 /60)" :value="60" />
                  <el-option label="/64 (IPv6 /64)" :value="64" />
                </el-option-group>
                <el-option label="/30 (4 IPs)" :value="30" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="Parent Prefix">
              <el-select 
                v-model="subnetAllocation.parent_prefix_id" 
                placeholder="Auto-select by tags, or choose specific parent"
                clearable
                filterable
                @change="updateAllocationPreview"
              >
                <el-option
                  v-for="prefix in allocationParentPrefixes"
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
            
            <el-form-item label="Tag Matching">
              <el-input
                v-model="allocationTagsInput"
                type="textarea"
                placeholder="JSON format: {&quot;purpose&quot;: &quot;vpc_reservation&quot;, &quot;env&quot;: &quot;prod&quot;}"
                @input="updateAllocationPreview"
              />
              <div class="form-help-text">
                Leave empty to match any parent prefix, or specify tags for strict matching
              </div>
            </el-form-item>
            
            <el-form-item label="Routable">
              <el-switch v-model="subnetAllocation.routable" />
            </el-form-item>
            
            <el-form-item label="Description">
              <el-input v-model="subnetAllocation.description" placeholder="Optional description for the allocated subnet" />
            </el-form-item>
            
            <!-- Allocation Preview -->
            <el-form-item v-if="allocationPreview" label="Preview">
              <el-card class="allocation-preview">
                <div v-if="allocationPreview.error" class="preview-error">
                  <el-icon><Warning /></el-icon>
                  {{ allocationPreview.error }}
                </div>
                <div v-else class="preview-success">
                  <div class="preview-item">
                    <strong>Will allocate:</strong> 
                    <el-tag type="success">{{ allocationPreview.next_subnet || 'First available' }}</el-tag>
                  </div>
                  <div class="preview-item">
                    <strong>From parent:</strong> 
                    <el-tag>{{ allocationPreview.parent_cidr }}</el-tag>
                  </div>
                  <div class="preview-item">
                    <strong>Available subnets:</strong> 
                    <el-tag type="info">{{ allocationPreview.available_count }} remaining</el-tag>
                  </div>
                </div>
              </el-card>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button 
          v-if="createMode === 'manual'" 
          type="primary" 
          @click="createPrefix" 
          :loading="creating"
        >
          Create Prefix
        </el-button>
        <el-button 
          v-if="createMode === 'allocate'" 
          type="primary" 
          @click="allocateSubnet" 
          :loading="allocating"
        >
          Allocate Subnet
        </el-button>
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
          <el-input v-model="vpcAssociation.vpc_prefix_cidr" placeholder="e.g., 10.0.0.0/16 or 2001:db8::/48" />
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

    <!-- Subnet Allocation Confirmation Dialog -->
    <el-dialog 
      v-model="showConfirmationDialog" 
      title="Subnet Allocation Successful" 
      width="600px"
      :close-on-click-modal="false"
    >
      <div class="confirmation-content">
        <!-- Success Icon and Message -->
        <div class="success-header">
          <el-icon class="success-icon" size="48" color="#67c23a">
            <CircleCheck />
          </el-icon>
          <h3 class="success-title">CIDR Successfully Allocated!</h3>
        </div>

        <!-- Allocation Details -->
        <div class="allocation-details">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Allocated CIDR">
              <el-tag type="success" size="large" class="cidr-tag">
                {{ allocationResult.allocated_cidr }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Parent CIDR">
              <el-text type="info">{{ allocationResult.parent_cidr }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="Routable">
              <el-tag :type="allocationResult.routable ? 'success' : 'warning'">
                {{ allocationResult.routable ? 'Yes' : 'No' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Remaining Subnets">
              <el-text>{{ allocationResult.available_count }} available</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="Created At">
              <el-text type="info">{{ formatDateTime(allocationResult.created_at) }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item v-if="Object.keys(allocationResult.tags).length > 0" label="Tags">
              <div class="tags-display">
                <el-tag 
                  v-for="(value, key) in allocationResult.tags" 
                  :key="key"
                  size="small"
                  class="tag-item"
                >
                  {{ key }}: {{ value }}
                </el-tag>
              </div>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- Quick Actions -->
        <div class="quick-actions">
          <el-alert
            title="What's Next?"
            type="info"
            :closable="false"
            show-icon
          >
            <template #default>
              <p>Your subnet has been allocated and is ready to use. You can:</p>
              <ul>
                <li>Create child subnets within this allocation</li>
                <li>Associate VPCs with this prefix</li>
                <li>View the allocation in the prefix list</li>
              </ul>
            </template>
          </el-alert>
        </div>
      </div>

      <template #footer>
        <div class="confirmation-footer">
          <el-button @click="closeConfirmationDialog">Close</el-button>
          <el-button 
            type="primary" 
            @click="viewAllocatedPrefix"
          >
            View Allocated Prefix
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { Plus, Search, List, Share, Check, Close, Link, Edit, Delete, QuestionFilled, Warning, CircleCheck } from '@element-plus/icons-vue'
import { prefixAPI, vrfAPI, vpcAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Prefixes',
  components: {
    Plus, Search, List, Share, Check, Close, Link, Edit, Delete, QuestionFilled, Warning
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
      showConfirmationDialog: false,
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
      searchHelpTimeout: null,
      isLoadingFromUrl: false, // Flag to prevent URL updates during initial load from URL
      // Subnet allocation properties
      createMode: 'manual', // 'manual' or 'allocate'
      allocating: false,
      subnetAllocation: {
        vrf_id: '',
        subnet_size: 24,
        parent_prefix_id: '',
        tags: {},
        routable: true,
        description: ''
      },
      allocationTagsInput: '{}',
      allocationParentPrefixes: [],
      allocationPreview: null,
      allocationRules: {
        vrf_id: [{ required: true, message: 'Please select a VRF', trigger: 'change' }],
        subnet_size: [{ required: true, message: 'Please select subnet size', trigger: 'change' }]
      },
      // Allocation confirmation data
      allocationResult: {
        allocated_cidr: '',
        parent_prefix_id: '',
        prefix_id: '',
        available_count: 0,
        parent_cidr: '',
        tags: {},
        routable: true,
        created_at: ''
      }
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
    },
    // Watch for URL query parameter changes
    '$route.query'(newQuery, oldQuery) {
      // Only reload if query actually changed and we're not currently updating URL from filters
      // This prevents infinite loops when updateUrl() triggers route changes
      if (!this.isLoadingFromUrl && JSON.stringify(newQuery) !== JSON.stringify(oldQuery)) {
        this.loadFiltersFromUrl()
        // Handle action query parameters if present
        this.handleActionQueryParams()
        this.loadData()
      }
    },
    // Watch filter changes and update URL
    'filters.vrfIds'() {
      this.updateUrl()
    },
    'filters.source'() {
      this.updateUrl()
    },
    'filters.routable'() {
      this.updateUrl()
    },
    'filters.search'() {
      // Debounce search URL updates
      clearTimeout(this.searchTimeout)
      this.searchTimeout = setTimeout(() => {
        this.updateUrl()
      }, 500)
    },
    'filters.includeDeleted'() {
      this.updateUrl()
    },
    'viewMode'() {
      this.updateUrl()
    },
    'pagination.currentPage'() {
      this.updateUrl()
    }
  },
  async mounted() {
    await this.loadVRFs()
    await this.loadVPCs()
    
    // Handle query parameters for filtering
    this.loadFiltersFromUrl()
    
    // Handle action query parameters (edit, createChild, associateVPC)
    await this.handleActionQueryParams()
    
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
    
    async loadVPCs() {
      try {
        const response = await vpcAPI.getVPCs()
        this.vpcs = response.data
      } catch (error) {
        console.error('Failed to load VPCs:', error)
      }
    },
    
    // Load filters from URL query parameters
    loadFiltersFromUrl() {
      this.isLoadingFromUrl = true
      const query = this.$route.query
      
      // Handle VRF IDs - support both vrf_id (single) and vrf_id (multiple) or vrf_ids (comma-separated)
      if (query.vrf_id) {
        // Handle array of vrf_id params or comma-separated string
        if (Array.isArray(query.vrf_id)) {
          this.filters.vrfIds = query.vrf_id
        } else if (query.vrf_id.includes(',')) {
          this.filters.vrfIds = query.vrf_id.split(',').filter(id => id.trim())
        } else {
          this.filters.vrfIds = [query.vrf_id]
        }
      } else if (query.vrf_ids) {
        // Support comma-separated vrf_ids parameter
        this.filters.vrfIds = query.vrf_ids.split(',').filter(id => id.trim())
      }
      
      // Handle source filter
      if (query.source !== undefined) {
        this.filters.source = query.source || ''
      }
      
      // Handle routable filter
      if (query.routable !== undefined) {
        if (query.routable === 'true' || query.routable === true) {
          this.filters.routable = true
        } else if (query.routable === 'false' || query.routable === false) {
          this.filters.routable = false
        } else {
          this.filters.routable = ''
        }
      }
      
      // Handle search filter
      if (query.search !== undefined) {
        this.filters.search = query.search || ''
      }
      
      // Handle includeDeleted filter
      if (query.include_deleted !== undefined) {
        this.filters.includeDeleted = query.include_deleted === 'true' || query.include_deleted === true
      }
      
      // Handle view mode
      if (query.view_mode !== undefined) {
        if (query.view_mode === 'tree' || query.view_mode === 'list') {
          this.viewMode = query.view_mode
        }
      }
      
      // Handle pagination
      if (query.page !== undefined) {
        const pageNum = parseInt(query.page, 10)
        if (pageNum > 0) {
          this.pagination.currentPage = pageNum
        }
      }
      
      this.isLoadingFromUrl = false
    },
    
    // Handle action query parameters (edit, createChild, associateVPC)
    async handleActionQueryParams() {
      const query = this.$route.query
      
      // Handle edit action
      if (query.edit) {
        try {
          const response = await prefixAPI.getPrefix(query.edit)
          const prefix = response.data
          await this.editPrefix(prefix)
          // Remove edit param from URL after opening dialog
          const newQuery = { ...this.$route.query }
          delete newQuery.edit
          this.$router.replace({ query: newQuery })
        } catch (error) {
          console.error('Failed to load prefix for editing:', error)
          ElMessage.error('Failed to load prefix for editing: ' + (error.response?.data?.detail || error.message))
        }
      }
      
      // Handle createChild action
      if (query.createChild) {
        try {
          const response = await prefixAPI.getPrefix(query.createChild)
          const parentPrefix = response.data
          await this.createChildPrefix(parentPrefix)
          // Remove createChild param from URL after opening dialog
          const newQuery = { ...this.$route.query }
          delete newQuery.createChild
          this.$router.replace({ query: newQuery })
        } catch (error) {
          console.error('Failed to load parent prefix:', error)
          ElMessage.error('Failed to load parent prefix: ' + (error.response?.data?.detail || error.message))
        }
      }
      
      // Handle associateVPC action
      if (query.associateVPC) {
        try {
          const response = await prefixAPI.getPrefix(query.associateVPC)
          const prefix = response.data
          await this.associateVPC(prefix)
          // Remove associateVPC param from URL after opening dialog
          const newQuery = { ...this.$route.query }
          delete newQuery.associateVPC
          this.$router.replace({ query: newQuery })
        } catch (error) {
          console.error('Failed to load prefix for VPC association:', error)
          ElMessage.error('Failed to load prefix for VPC association: ' + (error.response?.data?.detail || error.message))
        }
      }
    },
    
    // Update URL with current filter values
    updateUrl() {
      // Don't update URL if we're currently loading from URL (prevents infinite loops)
      if (this.isLoadingFromUrl) {
        return
      }
      
      const query = {}
      
      // Add VRF IDs
      if (this.filters.vrfIds && this.filters.vrfIds.length > 0) {
        // Use multiple vrf_id params for better compatibility
        query.vrf_id = this.filters.vrfIds
      }
      
      // Add source filter
      if (this.filters.source) {
        query.source = this.filters.source
      }
      
      // Add routable filter
      if (this.filters.routable !== '') {
        query.routable = this.filters.routable.toString()
      }
      
      // Add search filter
      if (this.filters.search) {
        query.search = this.filters.search
      }
      
      // Add includeDeleted filter
      if (this.filters.includeDeleted) {
        query.include_deleted = 'true'
      }
      
      // Add view mode
      if (this.viewMode !== 'list') {
        query.view_mode = this.viewMode
      }
      
      // Add pagination
      if (this.pagination.currentPage > 1) {
        query.page = this.pagination.currentPage.toString()
      }
      
      // Update URL without triggering navigation
      this.$router.push({ query }).catch(() => {})
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
    
    isIPv6(cidr) {
      // Check if CIDR is IPv6 (contains colons or uses IPv6 format)
      return cidr.includes(':') || /^[0-9a-fA-F:]+/.test(cidr.split('/')[0])
    },
    
    isSubnet(childCidr, parentCidr) {
      // CIDR containment check supporting both IPv4 and IPv6
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
        
        // Detect IP version
        const isIPv6Child = this.isIPv6(childCidr)
        const isIPv6Parent = this.isIPv6(parentCidr)
        
        // Both must be same IP version
        if (isIPv6Child !== isIPv6Parent) {
          return false
        }
        
        if (isIPv6Child) {
          // IPv6 containment check - rely on backend validation for accuracy
          // Frontend just checks mask length relationship (already verified childMaskNum > parentMaskNum above)
          return true
        } else {
          // IPv4 containment check
          const childIp = this.ipToNumber(childNetwork)
          const parentIp = this.ipToNumber(parentNetwork)
          
          // Calculate network addresses
          const parentNetworkSize = Math.pow(2, 32 - parentMaskNum)
          const parentNetworkStart = Math.floor(parentIp / parentNetworkSize) * parentNetworkSize
          const parentNetworkEnd = parentNetworkStart + parentNetworkSize - 1
          
          return childIp >= parentNetworkStart && childIp <= parentNetworkEnd
        }
      } catch (error) {
        return false
      }
    },
    
    ipToNumber(ip) {
      // IPv4 address to number conversion
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
    },

    // Subnet allocation methods
    onCreateModeChange(mode) {
      this.createMode = mode
      if (mode === 'allocate') {
        // Reset allocation form
        this.subnetAllocation = {
          vrf_id: '',
          subnet_size: 24,
          parent_prefix_id: '',
          tags: {},
          routable: true,
          description: ''
        }
        this.allocationTagsInput = '{}'
        this.allocationPreview = null
        this.loadAllocationParentPrefixes()
      }
    },

    async onAllocationVRFChange() {
      this.subnetAllocation.parent_prefix_id = ''
      this.allocationPreview = null
      await this.loadAllocationParentPrefixes()
      this.updateAllocationPreview()
    },

    async loadAllocationParentPrefixes() {
      if (!this.subnetAllocation.vrf_id) {
        this.allocationParentPrefixes = []
        return
      }

      try {
        const response = await prefixAPI.getPrefixes({
          vrf_id: this.subnetAllocation.vrf_id,
          source: 'manual'
        })
        this.allocationParentPrefixes = response.data.filter(prefix => 
          // Only show prefixes that can have children
          prefix.source === 'manual' && !prefix.vpc_children_type_flag
        )
      } catch (error) {
        console.error('Failed to load parent prefixes for allocation:', error)
        this.allocationParentPrefixes = []
      }
    },

    async updateAllocationPreview() {
      if (!this.subnetAllocation.vrf_id || !this.subnetAllocation.subnet_size) {
        this.allocationPreview = null
        return
      }

      // Parse tags
      let tags = {}
      try {
        if (this.allocationTagsInput.trim()) {
          tags = JSON.parse(this.allocationTagsInput)
        }
      } catch (e) {
        this.allocationPreview = {
          error: 'Invalid JSON format for tags'
        }
        return
      }

      // If specific parent is selected, preview that parent
      if (this.subnetAllocation.parent_prefix_id) {
        try {
          const response = await prefixAPI.getAvailableSubnets(
            this.subnetAllocation.parent_prefix_id,
            this.subnetAllocation.subnet_size
          )
          
          this.allocationPreview = {
            parent_cidr: response.data.parent_cidr,
            available_count: response.data.available_count,
            next_subnet: response.data.available_subnets[0] || null
          }
        } catch (error) {
          this.allocationPreview = {
            error: error.response?.data?.detail || 'Failed to get preview'
          }
        }
      } else {
        // Preview based on tag matching
        const matchingParents = this.allocationParentPrefixes.filter(prefix => {
          return this.tagsMatchStrictly(prefix.tags, tags)
        })

        if (matchingParents.length === 0) {
          this.allocationPreview = {
            error: Object.keys(tags).length > 0 
              ? `No parent prefixes found matching tags: ${JSON.stringify(tags)}`
              : 'No parent prefixes available'
          }
        } else {
          // Show preview for first matching parent
          const firstParent = matchingParents[0]
          try {
            const response = await prefixAPI.getAvailableSubnets(
              firstParent.prefix_id,
              this.subnetAllocation.subnet_size
            )
            
            this.allocationPreview = {
              parent_cidr: response.data.parent_cidr,
              available_count: response.data.available_count,
              next_subnet: response.data.available_subnets[0] || null
            }
          } catch (error) {
            this.allocationPreview = {
              error: error.response?.data?.detail || 'Failed to get preview'
            }
          }
        }
      }
    },

    tagsMatchStrictly(prefixTags, requiredTags) {
      if (!requiredTags || Object.keys(requiredTags).length === 0) {
        return true // No tags required, any prefix matches
      }
      
      for (const [key, value] of Object.entries(requiredTags)) {
        if (!prefixTags || prefixTags[key] !== value) {
          return false
        }
      }
      return true
    },

    async allocateSubnet() {
      try {
        await this.$refs.allocationForm.validate()
        
        // Parse tags
        let tags = {}
        try {
          if (this.allocationTagsInput.trim()) {
            tags = JSON.parse(this.allocationTagsInput)
          }
        } catch (e) {
          ElMessage.error('Invalid JSON format for tags')
          return
        }
        
        const allocationData = {
          vrf_id: this.subnetAllocation.vrf_id,
          subnet_size: this.subnetAllocation.subnet_size,
          tags: tags,
          routable: this.subnetAllocation.routable,
          parent_prefix_id: this.subnetAllocation.parent_prefix_id || null,
          description: this.subnetAllocation.description || null
        }
        
        this.allocating = true
        const response = await prefixAPI.allocateSubnet(allocationData)
        
        // Store allocation result for confirmation dialog
        this.allocationResult = {
          allocated_cidr: response.data.allocated_cidr,
          parent_prefix_id: response.data.parent_prefix_id,
          prefix_id: response.data.prefix_id,
          available_count: response.data.available_count,
          parent_cidr: response.data.parent_cidr,
          tags: response.data.tags || {},
          routable: response.data.routable,
          created_at: response.data.created_at
        }
        
        // Show confirmation dialog instead of toast
        this.showCreateDialog = false
        this.showConfirmationDialog = true
        
      } catch (error) {
        let errorMessage = 'Failed to allocate subnet'
        
        if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        }
        
        ElMessage.error(errorMessage)
        console.error(error)
      } finally {
        this.allocating = false
      }
    },

    closeConfirmationDialog() {
      this.showConfirmationDialog = false
      // Refresh the data to show the new allocation
      this.loadData()
    },

    viewAllocatedPrefix() {
      // Navigate to the allocated prefix detail page
      this.$router.push(`/prefixes/${this.allocationResult.prefix_id}`)
      this.showConfirmationDialog = false
    },

    formatDateTime(dateString) {
      if (!dateString) return ''
      try {
        return new Date(dateString).toLocaleString()
      } catch (e) {
        return dateString
      }
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

.view-toggle {
  margin-bottom: 20px;
}

/* Confirmation Dialog Styles */
.confirmation-content {
  text-align: center;
}

.success-header {
  margin-bottom: 24px;
}

.success-icon {
  margin-bottom: 16px;
}

.success-title {
  color: #67c23a;
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.allocation-details {
  margin: 24px 0;
  text-align: left;
}

.cidr-tag {
  font-size: 16px;
  font-weight: 600;
  padding: 8px 16px;
}

.tags-display {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  margin: 0;
}

.quick-actions {
  margin-top: 24px;
  text-align: left;
}

.quick-actions ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.quick-actions li {
  margin-bottom: 4px;
}

.confirmation-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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

/* Subnet allocation styles */
.allocation-header {
  margin-bottom: 20px;
}

.allocation-preview {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 15px;
}

.preview-error {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #f56c6c;
  font-size: 14px;
}

.preview-success {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.form-help-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}
</style>
