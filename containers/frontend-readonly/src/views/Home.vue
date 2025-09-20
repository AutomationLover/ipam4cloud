<template>
  <div class="home-readonly">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <span>Prefix Management System - Query Interface</span>
              <el-tag type="info" size="large">
                <el-icon><View /></el-icon>
                Read-Only Access
              </el-tag>
            </div>
          </template>
          <div class="welcome-content">
            <p>Welcome to the Prefix Management System query interface. This is a read-only view where you can:</p>
            <ul>
              <li><strong>Browse Prefixes:</strong> View all network prefixes with filtering and search capabilities</li>
              <li><strong>Explore VRFs:</strong> Query Virtual Routing and Forwarding instances</li>
              <li><strong>Check VPCs:</strong> View Virtual Private Cloud configurations</li>
              <li><strong>Search & Filter:</strong> Use advanced search to find specific resources</li>
            </ul>
            <p class="note">
              <el-icon><InfoFilled /></el-icon>
              Note: This interface is read-only. You cannot create, modify, or delete any resources.
            </p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card class="stat-card" @click="$router.push('/readonly/prefixes')">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon size="40" color="#409EFF"><List /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ stats.prefixes }}</div>
              <div class="stat-label">Total Prefixes</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="stat-card" @click="$router.push('/readonly/vrfs')">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon size="40" color="#67C23A"><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ stats.vrfs }}</div>
              <div class="stat-label">Total VRFs</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card class="stat-card" @click="$router.push('/readonly/vpcs')">
          <div class="stat-content">
            <div class="stat-icon">
              <el-icon size="40" color="#E6A23C"><Monitor /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-number">{{ stats.vpcs }}</div>
              <div class="stat-label">Total VPCs</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>Quick Actions</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/readonly/prefixes')">
              <el-icon><Search /></el-icon>
              Search Prefixes
            </el-button>
            <el-button type="success" @click="$router.push('/readonly/vrfs')">
              <el-icon><Connection /></el-icon>
              Browse VRFs
            </el-button>
            <el-button type="warning" @click="$router.push('/readonly/vpcs')">
              <el-icon><Monitor /></el-icon>
              View VPCs
            </el-button>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>System Information</span>
          </template>
          <div class="system-info">
            <div class="info-item">
              <span class="info-label">Access Level:</span>
              <el-tag type="info">Read-Only</el-tag>
            </div>
            <div class="info-item">
              <span class="info-label">Last Updated:</span>
              <span>{{ lastUpdated }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Total Resources:</span>
              <span>{{ stats.prefixes + stats.vrfs + stats.vpcs }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { List, Connection, Monitor, Search, View, InfoFilled } from '@element-plus/icons-vue'
import { prefixAPI, vrfAPI, vpcAPI } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'HomeReadOnly',
  components: {
    List, Connection, Monitor, Search, View, InfoFilled
  },
  data() {
    return {
      stats: {
        prefixes: 0,
        vrfs: 0,
        vpcs: 0
      },
      lastUpdated: new Date().toLocaleString()
    }
  },
  async mounted() {
    await this.loadStats()
  },
  methods: {
    async loadStats() {
      try {
        // Load all stats in parallel
        const [prefixResponse, vrfResponse, vpcResponse] = await Promise.all([
          prefixAPI.getPrefixes(),
          vrfAPI.getVRFs(),
          vpcAPI.getVPCs()
        ])
        
        this.stats.prefixes = prefixResponse.data.length
        this.stats.vrfs = vrfResponse.data.length
        this.stats.vpcs = vpcResponse.data.length
        this.lastUpdated = new Date().toLocaleString()
      } catch (error) {
        ElMessage.error('Failed to load statistics')
        console.error(error)
      }
    }
  }
}
</script>

<style scoped>
.home-readonly {
  max-width: 1400px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.welcome-content {
  font-size: 16px;
  line-height: 1.6;
}

.welcome-content ul {
  margin: 20px 0;
  padding-left: 20px;
}

.welcome-content li {
  margin-bottom: 8px;
}

.note {
  background-color: #f0f9ff;
  border: 1px solid #409EFF;
  border-radius: 4px;
  padding: 12px;
  margin-top: 20px;
  color: #409EFF;
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat-card {
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  flex-shrink: 0;
}

.stat-info {
  flex: 1;
}

.stat-number {
  font-size: 32px;
  font-weight: bold;
  color: #303133;
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.quick-actions .el-button {
  justify-content: flex-start;
}

.system-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-weight: 500;
  color: #606266;
}
</style>
