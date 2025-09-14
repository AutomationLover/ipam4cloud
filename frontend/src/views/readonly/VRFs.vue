<template>
  <div class="vrfs-readonly">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VRF Query (Read-Only)</span>
          <el-tag type="info" size="large">
            <el-icon><View /></el-icon>
            View Only
          </el-tag>
        </div>
      </template>
      
      <el-table
        :data="vrfs"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="vrf_id" label="VRF ID" width="200" />
        <el-table-column prop="description" label="Description" min-width="250" />
        <el-table-column label="Type" width="120">
          <template #default="scope">
            <el-tag :type="isAutoCreatedVRF(scope.row.vrf_id) ? 'warning' : 'primary'">
              {{ isAutoCreatedVRF(scope.row.vrf_id) ? 'Auto' : 'Manual' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Routable" width="100">
          <template #default="scope">
            <el-icon v-if="scope.row.routable_flag" color="green"><Check /></el-icon>
            <el-icon v-else color="red"><Close /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="Default" width="100">
          <template #default="scope">
            <el-icon v-if="scope.row.is_default" color="gold"><Star /></el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
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
        <el-table-column label="Prefixes" width="120">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewPrefixes(scope.row.vrf_id)"
            >
              {{ getPrefixCount(scope.row.vrf_id) }}
            </el-button>
          </template>
        </el-table-column>
        <!-- No Actions column for read-only view -->
      </el-table>
    </el-card>
  </div>
</template>

<script>
import { Check, Close, Star, View } from '@element-plus/icons-vue'
import { vrfAPI, prefixAPI } from '../../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'VRFsReadOnly',
  components: {
    Check, Close, Star, View
  },
  data() {
    return {
      loading: false,
      vrfs: [],
      prefixCounts: {}
    }
  },
  async mounted() {
    await this.loadVRFs()
    await this.loadPrefixCounts()
  },
  methods: {
    async loadVRFs() {
      this.loading = true
      try {
        const response = await vrfAPI.getVRFs()
        this.vrfs = response.data
      } catch (error) {
        ElMessage.error('Failed to load VRFs')
        console.error(error)
      } finally {
        this.loading = false
      }
    },
    
    async loadPrefixCounts() {
      try {
        const response = await prefixAPI.getPrefixes()
        const prefixes = response.data
        
        // Count prefixes per VRF
        this.prefixCounts = {}
        prefixes.forEach(prefix => {
          if (!this.prefixCounts[prefix.vrf_id]) {
            this.prefixCounts[prefix.vrf_id] = 0
          }
          this.prefixCounts[prefix.vrf_id]++
        })
      } catch (error) {
        console.error('Failed to load prefix counts:', error)
      }
    },
    
    getPrefixCount(vrfId) {
      return this.prefixCounts[vrfId] || 0
    },
    
    viewPrefixes(vrfId) {
      this.$router.push({
        path: '/readonly/prefixes',
        query: { vrf_id: vrfId }
      })
    },

    isAutoCreatedVRF(vrfId) {
      // Legacy format: vrf:uuid
      if (vrfId.startsWith('vrf:')) {
        return true
      }
      
      // New format: provider_account_vpcid (e.g., aws_123456789_vpc-abc123)
      const providerPattern = /^(aws|azure|gcp|other)_[^_]+_[^_]+$/
      return providerPattern.test(vrfId)
    }
  }
}
</script>

<style scoped>
.vrfs-readonly {
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
</style>
