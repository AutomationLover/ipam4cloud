<template>
  <div class="vpcs-readonly">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VPC Query (Read-Only)</span>
          <el-tag type="info" size="large">
            <el-icon><View /></el-icon>
            View Only
          </el-tag>
        </div>
      </template>
      
      <el-table
        :data="vpcs"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="provider_vpc_id" label="Provider VPC ID" width="150" />
        <el-table-column label="Internal UUID" width="200">
          <template #default="scope">
            <div class="uuid-display">
              <el-text size="small" type="info">{{ scope.row.vpc_id }}</el-text>
              <el-tooltip content="Copy Internal VPC UUID" placement="top">
                <el-button 
                  size="small" 
                  text 
                  @click="copyToClipboard(scope.row.vpc_id)"
                  style="margin-left: 4px; padding: 0;"
                >
                  <el-icon size="12"><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Provider" width="100">
          <template #default="scope">
            <el-tag :type="getProviderType(scope.row.provider)">
              {{ scope.row.provider.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="provider_account_id" label="Account ID" width="150" />
        <el-table-column prop="region" label="Region" width="120" />
        <el-table-column prop="description" label="Description" min-width="200" />
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
            <span v-if="Object.keys(scope.row.tags).length === 0" class="no-tags">No tags</span>
          </template>
        </el-table-column>
        <el-table-column label="Subnets" width="100">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewSubnets(scope.row.vpc_id)"
            >
              {{ getSubnetCount(scope.row.vpc_id) }}
            </el-button>
          </template>
        </el-table-column>
        <!-- No Actions column for read-only view -->
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { View, CopyDocument } from '@element-plus/icons-vue'
import { vpcAPI, prefixAPI } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'VPCsReadOnly',
  components: {
    View, CopyDocument
  },
  data() {
    return {
      loading: false,
      vpcs: [],
      subnetCounts: {}
    }
  },
  async mounted() {
    await this.loadVPCs()
    await this.loadSubnetCounts()
  },
  methods: {
    async loadVPCs() {
      this.loading = true
      try {
        const response = await vpcAPI.getVPCs()
        this.vpcs = response.data
      } catch (error) {
        ElMessage.error('Failed to load VPCs')
        console.error(error)
      } finally {
        this.loading = false
      }
    },
    
    async loadSubnetCounts() {
      try {
        const response = await prefixAPI.getPrefixes({ source: 'vpc' })
        const vpcPrefixes = response.data
        
        // Count subnets per VPC
        this.subnetCounts = {}
        vpcPrefixes.forEach(prefix => {
          if (prefix.vpc_id) {
            if (!this.subnetCounts[prefix.vpc_id]) {
              this.subnetCounts[prefix.vpc_id] = 0
            }
            this.subnetCounts[prefix.vpc_id]++
          }
        })
      } catch (error) {
        console.error('Failed to load subnet counts:', error)
      }
    },
    
    getProviderType(provider) {
      const types = {
        aws: 'warning',
        azure: 'primary',
        gcp: 'success',
        other: 'info'
      }
      return types[provider] || 'info'
    },
    
    getSubnetCount(vpcId) {
      return this.subnetCounts[vpcId] || 0
    },
    
    viewSubnets(vpcId) {
      this.$router.push({
        path: '/readonly/prefixes',
        query: { 
          source: 'vpc',
          search: vpcId
        }
      })
    },

    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text)
        ElMessage.success(`Copied to clipboard: ${text}`)
      } catch (error) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea')
        textArea.value = text
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        ElMessage.success(`Copied to clipboard: ${text}`)
      }
    }
  }
}
</script>

<style scoped>
.vpcs-readonly {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tag-item {
  margin-right: 5px;
  margin-bottom: 5px;
}

.no-tags {
  color: #909399;
  font-style: italic;
}

.uuid-display {
  display: flex;
  align-items: center;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
}

.uuid-display .el-text {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
