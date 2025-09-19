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
      <el-tag type="info" size="large">
        <el-icon><View /></el-icon>
        Read-Only
      </el-tag>
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
          <span>📋 Basic Information</span>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="CIDR">
                <el-tag type="primary" size="large">{{ prefix.cidr }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Prefix ID">
                <el-text type="info" class="monospace">{{ prefix.prefix_id }}</el-text>
                <el-button 
                  size="small" 
                  type="info" 
                  text 
                  @click="copyToClipboard(prefix.prefix_id)"
                  style="margin-left: 8px;"
                >
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
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
            <el-button 
              size="small" 
              type="info" 
              text 
              @click="copyToClipboard(`${key}:${value}`)"
            >
              <el-icon><CopyDocument /></el-icon>
            </el-button>
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
            <el-button 
              size="small" 
              type="info" 
              text 
              @click="copyToClipboard(prefix.vpc_id)"
              style="margin-left: 8px;"
            >
              <el-icon><CopyDocument /></el-icon>
            </el-button>
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

      <!-- Read-Only Actions -->
      <el-card class="detail-card">
        <template #header>
          <span>📄 Export & Copy</span>
        </template>
        
        <div class="readonly-actions">
          <el-button type="primary" @click="copyPrefixInfo">
            <el-icon><CopyDocument /></el-icon>
            Copy All Details
          </el-button>
          
          <el-button type="success" @click="exportToJSON">
            <el-icon><Download /></el-icon>
            Export as JSON
          </el-button>
          
          <el-button type="info" @click="goToAdminPortal" plain>
            <el-icon><Edit /></el-icon>
            Open in Admin Portal
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ArrowLeft, Grid, Check, Close, TopRight, CopyDocument, Download, Edit, View } from '@element-plus/icons-vue'
import { prefixAPI } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'PrefixDetailReadOnly',
  components: {
    ArrowLeft, Grid, Check, Close, TopRight, CopyDocument, Download, Edit, View
  },
  data() {
    return {
      prefix: null,
      parentPrefix: null,
      children: [],
      vpcAssociations: [],
      loading: true,
      error: null
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
          this.loadVPCAssociations()
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
    
    goBack() {
      this.$router.go(-1)
    },
    
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('Copied to clipboard')
      } catch (error) {
        ElMessage.error('Failed to copy to clipboard')
      }
    },
    
    async copyPrefixInfo() {
      const info = `Prefix Details:
CIDR: ${this.prefix.cidr}
Prefix ID: ${this.prefix.prefix_id}
VRF: ${this.prefix.vrf_id}
Source: ${this.prefix.source}
Routable: ${this.prefix.routable ? 'Yes' : 'No'}
VPC Children: ${this.prefix.vpc_children_type_flag ? 'Enabled' : 'Disabled'}
Created: ${this.formatDate(this.prefix.created_at)}
Updated: ${this.formatDate(this.prefix.updated_at)}

Tags:
${Object.entries(this.prefix.tags).map(([key, value]) => `${key}: ${value}`).join('\n')}

Parent: ${this.parentPrefix?.cidr || 'None'}
Children: ${this.children.map(c => c.cidr).join(', ') || 'None'}
${this.prefix.vpc_id ? `VPC ID: ${this.prefix.vpc_id}` : ''}
`
      await this.copyToClipboard(info)
    },
    
    exportToJSON() {
      const data = {
        ...this.prefix,
        parent_prefix: this.parentPrefix,
        children: this.children,
        vpc_associations: this.vpcAssociations
      }
      
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `prefix-${this.prefix.cidr.replace(/[/.]/g, '-')}-details.json`
      link.click()
      URL.revokeObjectURL(url)
      
      ElMessage.success('Prefix details exported as JSON')
    },
    
    goToAdminPortal() {
      const adminUrl = `http://localhost:8080/prefixes/${this.prefix.prefix_id}`
      window.open(adminUrl, '_blank')
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
  flex: 1;
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
  flex: 1;
}

.vpc-associations {
  margin-top: 16px;
}

.vpc-associations h4 {
  margin: 0 0 12px 0;
  color: #409EFF;
}

.readonly-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
