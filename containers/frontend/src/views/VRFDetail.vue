<template>
  <div class="vrf-detail">
    <div class="detail-header">
      <el-button @click="goBack" size="small" type="info" plain>
        <el-icon><ArrowLeft /></el-icon>
        Back to VRFs
      </el-button>
      <h1>
        <el-icon><Connection /></el-icon>
        VRF Details: {{ vrf?.vrf_id || 'Loading...' }}
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

    <div v-else-if="vrf" class="detail-content">
      <!-- Basic Information Card -->
      <el-card class="detail-card">
        <template #header>
          <div class="card-header">
            <span>📋 Basic Information</span>
            <el-button 
              v-if="!isAutoCreatedVRF(vrf.vrf_id)" 
              type="primary" 
              size="small"
              @click="editVRF"
            >
              <el-icon><Edit /></el-icon>
              Edit VRF
            </el-button>
          </div>
        </template>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="VRF ID">
                <div class="vrf-id-display">
                  <el-text type="primary" class="monospace">{{ vrf.vrf_id }}</el-text>
                  <el-tag 
                    v-if="isAutoCreatedVRF(vrf.vrf_id)" 
                    size="small" 
                    type="info"
                    style="margin-left: 8px;"
                  >
                    Auto-created
                  </el-tag>
                </div>
              </el-descriptions-item>
              <el-descriptions-item label="Description">
                <el-text>{{ vrf.description || 'No description' }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="Default VRF">
                <el-tag v-if="vrf.is_default" type="warning">Default VRF</el-tag>
                <el-text v-else type="info">No</el-text>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
          <el-col :span="12">
            <el-descriptions :column="1" border>
              <el-descriptions-item label="Routable">
                <el-icon v-if="vrf.routable_flag" color="green" size="20"><Check /></el-icon>
                <el-icon v-else color="red" size="20"><Close /></el-icon>
                <span class="ml-2">{{ vrf.routable_flag ? 'Yes' : 'No' }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="Created">
                <el-text type="info">{{ formatDate(vrf.created_at) }}</el-text>
              </el-descriptions-item>
              <el-descriptions-item label="Updated">
                <el-text type="info">{{ formatDate(vrf.updated_at) }}</el-text>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-card>

      <!-- Auto-created VRF Information -->
      <el-card v-if="isAutoCreatedVRF(vrf.vrf_id)" class="detail-card">
        <template #header>
          <span>🤖 Auto-created VRF Information</span>
        </template>
        
        <div class="auto-vrf-info">
          <el-descriptions :column="1" border>
            <el-descriptions-item label="Provider">
              <el-tag :type="getProviderType(parsedVRF.provider)">
                {{ parsedVRF.provider.toUpperCase() }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Account ID">
              <el-text class="monospace">{{ parsedVRF.account }}</el-text>
            </el-descriptions-item>
            <el-descriptions-item label="VPC ID">
              <el-text class="monospace">{{ parsedVRF.vpcId }}</el-text>
            </el-descriptions-item>
          </el-descriptions>
          
          <el-alert
            type="info"
            title="Auto-created VRF"
            description="This VRF was automatically created when a VPC was added to the system. It follows the naming convention: provider_account_vpcid"
            show-icon
            :closable="false"
            style="margin-top: 16px;"
          />
        </div>
      </el-card>

      <!-- Tags -->
      <el-card class="detail-card">
        <template #header>
          <span>🏷️ Tags</span>
        </template>
        
        <div v-if="Object.keys(vrf.tags).length > 0" class="tags-container">
          <div v-for="(value, key) in vrf.tags" :key="key" class="tag-row">
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
            <el-button size="small" @click="loadPrefixes" :loading="loadingPrefixes">
              <el-icon><Refresh /></el-icon>
              Refresh
            </el-button>
          </div>
        </template>
        
        <div v-if="loadingPrefixes" class="loading-prefixes">
          <el-skeleton :rows="3" animated />
        </div>
        
        <div v-else-if="prefixes.length > 0">
          <el-table :data="prefixes" size="small" max-height="400">
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
            <el-table-column prop="indentation_level" label="Level" width="80" />
          </el-table>
          
          <div class="prefix-summary">
            <el-statistic-group>
              <el-statistic title="Total Prefixes" :value="prefixes.length" />
              <el-statistic title="Manual Prefixes" :value="prefixes.filter(p => p.source === 'manual').length" />
              <el-statistic title="VPC Prefixes" :value="prefixes.filter(p => p.source === 'vpc').length" />
            </el-statistic-group>
          </div>
        </div>
        
        <el-empty v-else description="No prefixes associated with this VRF" :image-size="80" />
      </el-card>

      <!-- Actions -->
      <el-card v-if="!isAutoCreatedVRF(vrf.vrf_id)" class="detail-card">
        <template #header>
          <span>⚡ Actions</span>
        </template>
        
        <div class="actions-container">
          <el-button type="primary" @click="createPrefix">
            <el-icon><Plus /></el-icon>
            Create Prefix in VRF
          </el-button>
          
          <el-button type="warning" @click="editVRF">
            <el-icon><Edit /></el-icon>
            Edit VRF
          </el-button>
          
          <el-button type="danger" @click="deleteVRF">
            <el-icon><Delete /></el-icon>
            Delete VRF
          </el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script>
import { ArrowLeft, Connection, Edit, Check, Close, Refresh, Plus, Delete } from '@element-plus/icons-vue'
import { vrfAPI, prefixAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'VRFDetail',
  components: {
    ArrowLeft, Connection, Edit, Check, Close, Refresh, Plus, Delete
  },
  data() {
    return {
      vrf: null,
      prefixes: [],
      loading: true,
      loadingPrefixes: false,
      error: null
    }
  },
  computed: {
    parsedVRF() {
      if (!this.vrf || !this.isAutoCreatedVRF(this.vrf.vrf_id)) {
        return null
      }
      return this.parseVRFId(this.vrf.vrf_id)
    }
  },
  async mounted() {
    await this.loadVRFDetails()
  },
  watch: {
    '$route.params.vrfId': {
      immediate: true,
      async handler() {
        if (this.$route.params.vrfId) {
          await this.loadVRFDetails()
        }
      }
    }
  },
  methods: {
    async loadVRFDetails() {
      this.loading = true
      this.error = null
      
      try {
        const vrfId = this.$route.params.vrfId
        
        // Load VRF details and prefixes in parallel
        const [vrfResponse] = await Promise.all([
          vrfAPI.getVRF(vrfId),
          this.loadPrefixes()
        ])
        
        this.vrf = vrfResponse.data
        
      } catch (error) {
        console.error('Failed to load VRF details:', error)
        this.error = error.response?.data?.detail || 'Failed to load VRF details'
      } finally {
        this.loading = false
      }
    },
    
    async loadPrefixes() {
      this.loadingPrefixes = true
      try {
        const vrfId = this.$route.params.vrfId
        const response = await prefixAPI.getPrefixes({ vrf_id: vrfId })
        this.prefixes = response.data
      } catch (error) {
        console.error('Failed to load prefixes:', error)
        this.prefixes = []
      } finally {
        this.loadingPrefixes = false
      }
    },
    
    goBack() {
      this.$router.go(-1)
    },
    
    createPrefix() {
      this.$router.push({
        path: '/prefixes',
        query: { vrf_id: this.vrf.vrf_id }
      })
    },
    
    editVRF() {
      this.$router.push({
        path: '/vrfs',
        query: { edit: this.vrf.vrf_id }
      })
    },
    
    async deleteVRF() {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete VRF ${this.vrf.vrf_id}? This will also delete all associated prefixes. This action cannot be undone.`,
          'Confirm Delete',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        await vrfAPI.deleteVRF(this.vrf.vrf_id)
        ElMessage.success('VRF deleted successfully')
        this.$router.push('/vrfs')
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete VRF: ' + (error.response?.data?.detail || error.message))
        }
      }
    },
    
    formatDate(dateString) {
      return new Date(dateString).toLocaleString()
    },
    
    isAutoCreatedVRF(vrfId) {
      return /^(aws|azure|gcp|other)_([^_]+)_(.+)$/.test(vrfId)
    },
    
    parseVRFId(vrfId) {
      const match = vrfId.match(/^(aws|azure|gcp|other)_([^_]+)_(.+)$/)
      if (match) {
        return {
          provider: match[1],
          account: match[2] !== 'unknown' ? match[2] : 'Unknown',
          vpcId: match[3]
        }
      }
      return null
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
.vrf-detail {
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

.vrf-id-display {
  display: flex;
  align-items: center;
}

.ml-2 {
  margin-left: 8px;
}

.auto-vrf-info {
  padding: 8px 0;
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

.loading-prefixes {
  padding: 20px;
}

.cidr-link {
  text-decoration: none;
  cursor: pointer;
}

.cidr-link:hover {
  text-decoration: underline;
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
