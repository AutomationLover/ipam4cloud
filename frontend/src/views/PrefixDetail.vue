<template>
  <div class="prefix-detail">
    <div class="detail-header">
      <el-button @click="goBack" size="small" type="info" plain>
        <el-icon><ArrowLeft /></el-icon>
        Back to Prefixes
      </el-button>
      <h1>
        <el-icon><Grid /></el-icon>
        Prefix Details: {{ prefix?.cidr || 'Loading...' }}
      </h1>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="error-container">
      <el-alert
        :title="error"
        type="error"
        center
        show-icon
      />
    </div>

    <div v-else-if="prefix" class="detail-content">
      <!-- Basic Information Card -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>📋 Basic Information</span>
            <el-button 
              v-if="prefix.source === 'manual'" 
              type="primary" 
              size="small"
              @click="editPrefix"
            >
              <el-icon><Edit /></el-icon>
              Edit Prefix
            </el-button>
          </div>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="CIDR">
                <el-tag type="primary" size="large">{{ prefix.cidr }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Prefix ID">
                <el-text type="info" class="monospace">{{ prefix.prefix_id }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="VRF">
                <div class="vrf-info">
                  <div class="vrf-primary">{{ formatVRFDisplay(prefix.vrf_id) }}</div>
                  <div v-if="getVRFDetails(prefix.vrf_id)" class="vrf-details">
                    {{ getVRFDetails(prefix.vrf_id) }}
                  </div>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="Source">
                <el-tag :type="prefix.source === 'manual' ? 'primary' : 'success'">
                  {{ prefix.source }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Routable">
                <el-icon v-if="prefix.routable" color="green" size="20"><Check /></el-icon>
                <el-icon v-else color="red" size="20"><Close /></el-icon>
                <span class="ml-2">{{ prefix.routable ? 'Yes' : 'No' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="VPC Children">
                <el-icon v-if="prefix.vpc_children_type_flag" color="green" size="20"><Check /></el-icon>
                <el-icon v-else color="red" size="20"><Close /></el-icon>
                <span class="ml-2">{{ prefix.vpc_children_type_flag ? 'Enabled' : 'Disabled' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="Created">
                <el-text type="info">{{ formatDate(prefix.created_at) }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="Updated">
                <el-text type="info">{{ formatDate(prefix.updated_at) }}</el-text>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-card>

      <!-- Hierarchy Information -->
      <el-card class="detail-card">
        <template #header>
          <span>🌳 Hierarchy Information</span>
        </template>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="Indentation Level">
            <el-tag>Level {{ prefix.indentation_level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Parent Prefix">
            <div v-if="prefix.parent_prefix_id">
              <router-link 
                :to="`/prefixes/${prefix.parent_prefix_id}`"
                class="parent-link"
              >
                <el-text type="primary">{{ parentPrefix?.cidr || 'Loading...' }}</el-text>
                <el-icon><TopRight /></el-icon>
              </router-link>
            </div>
            <el-text v-else type="info">Root prefix (no parent)</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="Child Prefixes">
            <div v-if="children.length > 0">
              <div v-for="child in children" :key="child.prefix_id" class="child-item">
                <router-link 
                  :to="`/prefixes/${child.prefix_id}`"
                  class="child-link"
                >
                  <el-tag type="info" size="small">{{ child.cidr }}</el-tag>
                </router-link>
              </div>
            </div>
            <el-text v-else type="info">No child prefixes</el-text>
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- Tags -->
      <el-card class="detail-card">
        <template #header>
          <span>🏷️ Tags</span>
        </template>
        
        <div v-if="Object.keys(prefix.tags).length > 0" class="tags-container">
          <div v-for="(value, key) in prefix.tags" :key="key" class="tag-row">
            <el-tag type="primary" class="tag-key">{{ key }}</el-tag>
            <el-text class="tag-value">{{ value }}</el-text>
          </div>
        </div>
        <el-empty v-else description="No tags assigned" :image-size="60" />
      </el-card>

      <!-- VPC Information -->
      <el-card v-if="prefix.vpc_id" class="detail-card">
        <template #header>
          <span>☁️ VPC Information</span>
        </template>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="VPC ID">
            <el-text type="info" class="monospace">{{ prefix.vpc_id }}</el-text>
          </el-descriptions-item>
        </el-descriptions>
        
        <!-- VPC Associations -->
        <div v-if="vpcAssociations.length > 0" class="vpc-associations">
          <h4>VPC Associations</h4>
          <el-table :data="vpcAssociations" size="small">
            <el-table-column prop="provider_vpc_id" label="VPC ID" />
            <el-table-column prop="provider" label="Provider" />
            <el-table-column prop="vpc_prefix_cidr" label="VPC CIDR" />
            <el-table-column label="Routable">
              <template #default="scope">
                <el-icon v-if="scope.row.routable" color="green"><Check /></el-icon>
                <el-icon v-else color="red"><Close /></el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="Description" />
          </el-table>
        </div>
      </el-card>

      <!-- Actions -->
      <el-card v-if="prefix.source === 'manual'" class="detail-card">
        <template #header>
          <span>⚡ Actions</span>
        </template>
        
        <div class="actions-container">
          <el-button 
            v-if="canCreateChild"
            type="primary" 
            @click="createChild"
          >
            <el-icon><Plus /></el-icon>
            Create Child Prefix
          </el-button>
          
          <el-button 
            v-if="canAssociateVPC"
            type="success" 
            @click="associateVPC"
          >
            <el-icon><Link /></el-icon>
            Associate VPC
          </el-button>
          
          <el-button 
            type="warning" 
            @click="editPrefix"
          >
            <el-icon><Edit /></el-icon>
            Edit Prefix
          </el-button>
          
          <el-button 
            type="danger" 
            @click="deletePrefix"
          >
            <el-icon><Delete /></el-icon>
            Delete Prefix
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ArrowLeft, Grid, Edit, Check, Close, TopRight, Plus, Link, Delete } from '@element-plus/icons-vue'
import { prefixAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'PrefixDetail',
  components: {
    ArrowLeft, Grid, Edit, Check, Close, TopRight, Plus, Link, Delete
  },
  data() {
    return {
      prefix: null,
      parentPrefix: null,
      children: [],
      vpcAssociations: [],
      loading: true,
      error: null,
      canCreateChild: false,
      canAssociateVPC: false
    }
  },
  async mounted() {
    await this.loadPrefixDetails()
  },
  watch: {
    '$route.params.prefixId': {
      immediate: true,
      async handler() {
        if (this.$route.params.prefixId) {
          await this.loadPrefixDetails()
        }
      }
    }
  },
  methods: {
    async loadPrefixDetails() {
      this.loading = true
      this.error = null
      
      try {
        const prefixId = this.$route.params.prefixId
        
        // Load main prefix details
        const response = await prefixAPI.getPrefix(prefixId)
        this.prefix = response.data
        
        // Load additional data in parallel
        await Promise.all([
          this.loadParentPrefix(),
          this.loadChildren(),
          this.loadVPCAssociations(),
          this.checkCapabilities()
        ])
        
      } catch (error) {
        console.error('Failed to load prefix details:', error)
        this.error = error.response?.data?.detail || 'Failed to load prefix details'
      } finally {
        this.loading = false
      }
    },
    
    async loadParentPrefix() {
      if (this.prefix.parent_prefix_id) {
        try {
          const response = await prefixAPI.getPrefix(this.prefix.parent_prefix_id)
          this.parentPrefix = response.data
        } catch (error) {
          console.error('Failed to load parent prefix:', error)
        }
      }
    },
    
    async loadChildren() {
      try {
        const response = await prefixAPI.getPrefixChildren(this.prefix.prefix_id)
        this.children = response.data
      } catch (error) {
        console.error('Failed to load children:', error)
        this.children = []
      }
    },
    
    async loadVPCAssociations() {
      if (this.prefix.vpc_id) {
        try {
          const response = await prefixAPI.getPrefixVPCAssociations(this.prefix.prefix_id)
          this.vpcAssociations = response.data
        } catch (error) {
          console.error('Failed to load VPC associations:', error)
          this.vpcAssociations = []
        }
      }
    },
    
    async checkCapabilities() {
      if (this.prefix.source === 'manual') {
        try {
          const [childResponse, vpcResponse] = await Promise.all([
            prefixAPI.canCreateChild(this.prefix.prefix_id),
            prefixAPI.canAssociateVPC(this.prefix.prefix_id)
          ])
          this.canCreateChild = childResponse.data.can_create
          this.canAssociateVPC = vpcResponse.data.can_associate
        } catch (error) {
          console.error('Failed to check capabilities:', error)
        }
      }
    },
    
    goBack() {
      this.$router.go(-1)
    },
    
    createChild() {
      this.$router.push({
        path: '/prefixes',
        query: { createChild: this.prefix.prefix_id }
      })
    },
    
    associateVPC() {
      this.$router.push({
        path: '/prefixes',
        query: { associateVPC: this.prefix.prefix_id }
      })
    },
    
    editPrefix() {
      this.$router.push({
        path: '/prefixes',
        query: { edit: this.prefix.prefix_id }
      })
    },
    
    async deletePrefix() {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete prefix ${this.prefix.cidr}? This action cannot be undone.`,
          'Confirm Delete',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        await prefixAPI.deletePrefix(this.prefix.prefix_id)
        ElMessage.success('Prefix deleted successfully')
        this.$router.push('/prefixes')
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete prefix: ' + (error.response?.data?.detail || error.message))
        }
      }
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleString()
    },
    
    formatVRFDisplay(vrfId) {
      const parsed = this.parseVRFId(vrfId)
      if (parsed) {
        return `${parsed.provider.toUpperCase()} VPC ${parsed.vpcId}`
      }
      return vrfId
    },

    getVRFDetails(vrfId) {
      const parsed = this.parseVRFId(vrfId)
      if (parsed && parsed.account) {
        return `Account: ${parsed.account}`
      }
      return null
    },

    parseVRFId(vrfId) {
      // Parse auto-created VRF IDs
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
          vpcId: uuid.substring(0, 8) + '...'
        }
      }

      return null
    }
  }
}
</script>

<style scoped>
.prefix-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.detail-header h1 {
  margin: 0;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 8px;
}

.loading-container, .error-container {
  text-align: center;
  padding: 40px;
}

.detail-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.detail-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.monospace {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 3px;
}

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

.ml-2 {
  margin-left: 8px;
}

.parent-link, .child-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  text-decoration: none;
}

.parent-link:hover, .child-link:hover {
  text-decoration: underline;
}

.child-item {
  display: inline-block;
  margin-right: 8px;
  margin-bottom: 4px;
}

.tags-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.tag-key {
  min-width: 120px;
  font-weight: 600;
}

.tag-value {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 3px;
}

.vpc-associations {
  margin-top: 16px;
}

.vpc-associations h4 {
  margin: 0 0 12px 0;
  color: #409EFF;
}

.actions-container {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
