<template>
  <div class="vpc-detail">
    <div class="detail-header">
      <el-button @click="goBack" size="small" type="info" plain>
        <el-icon><ArrowLeft /></el-icon>
        Back to VPCs
      </el-button>
      <h1>
        <el-icon><Monitor /></el-icon>
        VPC Details: {{ vpc?.provider_vpc_id || 'Loading...' }}
      </h1>
    </div>

    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="6" animated />
    </div>

    <div v-else-if="error" class="error-container">
      <el-alert
        :title="error"
        type="error"
        center
        show-icon
      />
    </div>

    <div v-else-if="vpc" class="detail-content">
      <!-- Basic Information Card -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>📋 Basic Information</span>
            <el-button 
              type="primary" 
              size="small"
              @click="editVPC"
            >
              <el-icon><Edit /></el-icon>
              Edit VPC
            </el-button>
          </div>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Provider VPC ID">
                <el-tag type="primary" size="large">{{ vpc.provider_vpc_id }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Internal UUID">
                <div class="uuid-display">
                  <el-text type="info" class="monospace">{{ vpc.vpc_id }}</el-text>
                  <el-button 
                    size="small" 
                    type="info" 
                    text 
                    @click="copyToClipboard(vpc.vpc_id)"
                    style="margin-left: 8px;"
                  >
                    <el-icon><CopyDocument /></el-icon>
                  </el-button>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="Provider">
                <el-tag :type="getProviderType(vpc.provider)" size="large">
                  {{ vpc.provider.toUpperCase() }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Description">
                <el-text>{{ vpc.description || 'No description' }}</el-text>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Account ID">
                <el-text class="monospace">{{ vpc.provider_account_id || 'Not specified' }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="Region">
                <el-tag type="info">{{ vpc.region || 'Not specified' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Created">
                <el-text type="info">{{ formatDate(vpc.created_at) }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="Updated">
                <el-text type="info">{{ formatDate(vpc.updated_at) }}</el-text>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-card>

      <!-- Associated VRF Information -->
      <el-card v-if="associatedVRF" class="detail-card">
        <template #header>
          <span>🔗 Associated VRF</span>
        </template>
        
        <el-descriptions :column="1" border>
          <el-descriptions-item label="VRF ID">
            <router-link 
              :to="`/vrfs/${associatedVRF.vrf_id}`"
              class="vrf-link"
            >
              <el-text type="primary">{{ associatedVRF.vrf_id }}</el-text>
              <el-icon style="margin-left: 4px;"><TopRight /></el-icon>
            </router-link>
          </el-descriptions-item>
          <el-descriptions-item label="VRF Description">
            <el-text>{{ associatedVRF.description || 'No description' }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="VRF Routable">
            <el-icon v-if="associatedVRF.routable_flag" color="green"><Check /></el-icon>
            <el-icon v-else color="red"><Close /></el-icon>
            <span class="ml-2">{{ associatedVRF.routable_flag ? 'Yes' : 'No' }}</span>
          </el-descriptions-item>
        </el-descriptions>
        
        <el-alert
          type="info"
          title="Auto-created VRF"
          description="This VPC has an automatically created VRF following the naming convention: provider_account_vpcid"
          show-icon
          :closable="false"
          style="margin-top: 16px;"
        />
      </el-card>

      <!-- Tags -->
      <el-card class="detail-card">
        <template #header>
          <span>🏷️ Tags</span>
        </template>
        
        <div v-if="Object.keys(vpc.tags).length > 0" class="tags-container">
          <div v-for="(value, key) in vpc.tags" :key="key" class="tag-row">
            <el-tag type="primary" class="tag-key">{{ key }}</el-tag>
            <el-text class="tag-value">{{ value }}</el-text>
          </div>
        </div>
        <el-empty v-else description="No tags assigned" :image-size="60" />
      </el-card>

      <!-- Associated Prefixes -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>📊 Associated Prefixes</span>
            <el-button size="small" @click="loadAssociatedPrefixes" :loading="loadingPrefixes">
              <el-icon><Refresh /></el-icon>
              Refresh
            </el-button>
          </div>
        </template>
        
        <div v-if="loadingPrefixes" class="loading-prefixes">
          <el-skeleton :rows="3" animated />
        </div>
        
        <div v-else-if="associatedPrefixes.length > 0">
          <el-table :data="associatedPrefixes" size="small" max-height="400">
            <el-table-column label="CIDR">
              <template #default="scope">
                <router-link 
                  :to="`/prefixes/${scope.row.prefix_id}`"
                  class="cidr-link"
                >
                  <el-text type="primary">{{ scope.row.cidr }}</el-text>
                </router-link>
              </template>
            </el-table-column>
            <el-table-column label="VRF" width="200">
              <template #default="scope">
                <router-link 
                  :to="`/vrfs/${scope.row.vrf_id}`"
                  class="vrf-link"
                >
                  <el-text type="info" size="small">{{ scope.row.vrf_id }}</el-text>
                </router-link>
              </template>
            </el-table-column>
            <el-table-column label="Source" width="100">
              <template #default="scope">
                <el-tag :type="scope.row.source === 'manual' ? 'primary' : 'success'" size="small">
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
          </el-table>
          
          <div class="prefix-summary">
            <el-statistic-group>
              <el-statistic title="Total Prefixes" :value="associatedPrefixes.length" />
              <el-statistic title="Manual Prefixes" :value="associatedPrefixes.filter(p => p.source === 'manual').length" />
              <el-statistic title="VPC Prefixes" :value="associatedPrefixes.filter(p => p.source === 'vpc').length" />
            </el-statistic-group>
          </div>
        </div>
        
        <el-empty v-else description="No prefixes associated with this VPC" :image-size="80" />
      </el-card>

      <!-- VPC Associations -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>🔗 VPC Associations</span>
            <el-button size="small" @click="loadVPCAssociations" :loading="loadingAssociations">
              <el-icon><Refresh /></el-icon>
              Refresh
            </el-button>
          </div>
        </template>
        
        <div v-if="loadingAssociations" class="loading-associations">
          <el-skeleton :rows="3" animated />
        </div>
        
        <div v-else-if="vpcAssociations.length > 0">
          <el-table :data="vpcAssociations" size="small">
            <el-table-column label="Associated Prefix">
              <template #default="scope">
                <router-link 
                  :to="`/prefixes/${scope.row.parent_prefix_id}`"
                  class="cidr-link"
                >
                  <el-text type="primary">{{ scope.row.vpc_prefix_cidr }}</el-text>
                </router-link>
              </template>
            </el-table-column>
            <el-table-column label="Routable" width="100">
              <template #default="scope">
                <el-icon v-if="scope.row.routable" color="green"><Check /></el-icon>
                <el-icon v-else color="red"><Close /></el-icon>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="Description" />
            <el-table-column label="Actions" width="120">
              <template #default="scope">
                <el-button 
                  size="small" 
                  type="danger" 
                  @click="removeVPCAssociation(scope.row)"
                >
                  <el-icon><Delete /></el-icon>
                  Remove
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
        
        <el-empty v-else description="No VPC associations found" :image-size="80" />
      </el-card>

      <!-- Actions -->
      <el-card class="detail-card">
        <template #header>
          <span>⚡ Actions</span>
        </template>
        
        <div class="actions-container">
          <el-button type="primary" @click="createAssociation">
            <el-icon><Plus /></el-icon>
            Create VPC Association
          </el-button>
          
          <el-button type="warning" @click="editVPC">
            <el-icon><Edit /></el-icon>
            Edit VPC
          </el-button>
          
          <el-button type="danger" @click="deleteVPC">
            <el-icon><Delete /></el-icon>
            Delete VPC
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ArrowLeft, Monitor, Edit, Check, Close, CopyDocument, TopRight, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import { vpcAPI, vrfAPI, prefixAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'VPCDetail',
  components: {
    ArrowLeft, Monitor, Edit, Check, Close, CopyDocument, TopRight, Refresh, Plus, Delete
  },
  data() {
    return {
      vpc: null,
      associatedVRF: null,
      associatedPrefixes: [],
      vpcAssociations: [],
      loading: true,
      loadingPrefixes: false,
      loadingAssociations: false,
      error: null
    }
  },
  async mounted() {
    await this.loadVPCDetails()
  },
  watch: {
    '$route.params.vpcId': {
      immediate: true,
      async handler() {
        if (this.$route.params.vpcId) {
          await this.loadVPCDetails()
        }
      }
    }
  },
  methods: {
    async loadVPCDetails() {
      this.loading = true
      this.error = null
      
      try {
        const vpcId = this.$route.params.vpcId
        
        // Load VPC details
        const vpcResponse = await vpcAPI.getVPC(vpcId)
        this.vpc = vpcResponse.data
        
        // Load additional data in parallel
        await Promise.all([
          this.loadAssociatedVRF(),
          this.loadAssociatedPrefixes(),
          this.loadVPCAssociations()
        ])
        
      } catch (error) {
        console.error('Failed to load VPC details:', error)
        this.error = error.response?.data?.detail || 'Failed to load VPC details'
      } finally {
        this.loading = false
      }
    },
    
    async loadAssociatedVRF() {
      if (!this.vpc) return
      
      try {
        // Try to find the auto-created VRF for this VPC
        const vrfId = `${this.vpc.provider}_${this.vpc.provider_account_id || 'unknown'}_${this.vpc.provider_vpc_id}`
        const response = await vrfAPI.getVRF(vrfId)
        this.associatedVRF = response.data
      } catch (error) {
        console.log('No associated auto-created VRF found:', error)
        this.associatedVRF = null
      }
    },
    
    async loadAssociatedPrefixes() {
      this.loadingPrefixes = true
      try {
        const vpcId = this.$route.params.vpcId
        // Get all prefixes and filter by VPC ID
        const response = await prefixAPI.getPrefixes()
        this.associatedPrefixes = response.data.filter(prefix => prefix.vpc_id === vpcId)
      } catch (error) {
        console.error('Failed to load associated prefixes:', error)
        this.associatedPrefixes = []
      } finally {
        this.loadingPrefixes = false
      }
    },
    
    async loadVPCAssociations() {
      this.loadingAssociations = true
      try {
        // This would need to be implemented in the backend
        // For now, we'll use a placeholder
        this.vpcAssociations = []
      } catch (error) {
        console.error('Failed to load VPC associations:', error)
        this.vpcAssociations = []
      } finally {
        this.loadingAssociations = false
      }
    },
    
    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text)
        ElMessage.success('Copied to clipboard')
      } catch (error) {
        ElMessage.error('Failed to copy to clipboard')
      }
    },
    
    goBack() {
      this.$router.go(-1)
    },
    
    createAssociation() {
      this.$router.push({
        path: '/prefixes',
        query: { associateVPC: this.vpc.vpc_id }
      })
    },
    
    editVPC() {
      this.$router.push({
        path: '/vpcs',
        query: { edit: this.vpc.vpc_id }
      })
    },
    
    async deleteVPC() {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete VPC ${this.vpc.provider_vpc_id}? This will also remove all associated prefixes and associations. This action cannot be undone.`,
          'Confirm Delete',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        await vpcAPI.deleteVPC(this.vpc.vpc_id)
        ElMessage.success('VPC deleted successfully')
        this.$router.push('/vpcs')
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete VPC: ' + (error.response?.data?.detail || error.message))
        }
      }
    },
    
    async removeVPCAssociation(association) {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to remove this VPC association?`,
          'Confirm Remove',
          {
            confirmButtonText: 'Remove',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        await vpcAPI.removeVPCAssociation(association.association_id)
        ElMessage.success('VPC association removed successfully')
        await this.loadVPCAssociations()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to remove VPC association: ' + (error.response?.data?.detail || error.message))
        }
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return 'N/A'
      return new Date(dateString).toLocaleString()
    },
    
    getProviderType(provider) {
      const types = {
        aws: 'warning',
        azure: 'info', 
        gcp: 'success',
        other: 'info'
      }
      return types[provider] || 'info'
    }
  }
}
</script>

<style scoped>
.vpc-detail {
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

.uuid-display {
  display: flex;
  align-items: center;
}

.ml-2 {
  margin-left: 8px;
}

.vrf-link, .cidr-link {
  text-decoration: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
}

.vrf-link:hover, .cidr-link:hover {
  text-decoration: underline;
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

.loading-prefixes, .loading-associations {
  padding: 20px;
}

.prefix-summary {
  margin-top: 16px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 6px;
}

.actions-container {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>
