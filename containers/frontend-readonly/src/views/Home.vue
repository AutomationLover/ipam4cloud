<template>
  <div class="home">
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card class="welcome-card">
          <template #header>
            <div class="card-header">
              <span>Prefix Query System</span>
            </div>
          </template>
          <div class="welcome-content">
            <h2>Welcome to the Prefix Query System</h2>
            <p>This system provides read-only access to view hierarchical IP prefixes for cloud environments.</p>
            
            <el-row :gutter="20" class="feature-cards">
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <div class="feature-icon">
                    <el-icon size="48"><List /></el-icon>
                  </div>
                  <h3>Prefix Management</h3>
                  <p>View IP prefixes in both list and tree views. Explore child prefixes and VPC associations.</p>
                  <el-button type="primary" @click="$router.push('/prefixes')">
                    Go to Prefixes
                  </el-button>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <div class="feature-icon">
                    <el-icon size="48"><Connection /></el-icon>
                  </div>
                  <h3>VRF Management</h3>
                  <p>View Virtual Routing and Forwarding instances that organize your network prefixes.</p>
                  <el-button type="primary" @click="$router.push('/vrfs')">
                    View VRFs
                  </el-button>
                </el-card>
              </el-col>
              
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <div class="feature-icon">
                    <el-icon size="48"><Monitor /></el-icon>
                  </div>
                  <h3>VPC Management</h3>
                  <p>View cloud VPCs from different providers (AWS, Azure, GCP).</p>
                  <el-button type="primary" @click="$router.push('/vpcs')">
                    View VPCs
                  </el-button>
                </el-card>
              </el-col>
            </el-row>
            
            <el-row :gutter="20" class="feature-cards" style="margin-top: 20px;">
              <el-col :span="8">
                <el-card shadow="hover" class="feature-card">
                  <div class="feature-icon">
                    <el-icon size="48"><Search /></el-icon>
                  </div>
                  <h3>IP Address Query</h3>
                  <p>Search and query IP addresses by label. Share URLs for specific label queries.</p>
                  <el-button type="primary" @click="$router.push('/ip-addresses')">
                    Query IP Addresses
                  </el-button>
                </el-card>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="Total Prefixes" :value="stats.totalPrefixes" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="Manual Prefixes" :value="stats.manualPrefixes" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="VPC Prefixes" :value="stats.vpcPrefixes" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <el-statistic title="Total VRFs" :value="stats.totalVRFs" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { List, Connection, Monitor, Search } from '@element-plus/icons-vue'
import { prefixAPI, vrfAPI } from '../api'

export default {
  name: 'Home',
  components: {
    List,
    Connection,
    Monitor,
    Search
  },
  data() {
    return {
      stats: {
        totalPrefixes: 0,
        manualPrefixes: 0,
        vpcPrefixes: 0,
        totalVRFs: 0
      }
    }
  },
  async mounted() {
    await this.loadStats()
  },
  methods: {
    async loadStats() {
      try {
        const [prefixesRes, vrfsRes] = await Promise.all([
          prefixAPI.getPrefixes(),
          vrfAPI.getVRFs()
        ])
        
        const prefixes = prefixesRes.data
        this.stats.totalPrefixes = prefixes.length
        this.stats.manualPrefixes = prefixes.filter(p => p.source === 'manual').length
        this.stats.vpcPrefixes = prefixes.filter(p => p.source === 'vpc').length
        this.stats.totalVRFs = vrfsRes.data.length
      } catch (error) {
        console.error('Failed to load stats:', error)
      }
    }
  }
}
</script>

<style scoped>
.home {
  max-width: 1200px;
  margin: 0 auto;
}

.welcome-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

.welcome-content {
  text-align: center;
}

.welcome-content h2 {
  color: #409EFF;
  margin-bottom: 10px;
}

.welcome-content p {
  color: #606266;
  font-size: 16px;
  margin-bottom: 30px;
}

.feature-cards {
  margin-top: 30px;
}

.feature-card {
  text-align: center;
  height: 280px;
}

.feature-icon {
  color: #409EFF;
  margin-bottom: 15px;
}

.feature-card h3 {
  color: #303133;
  margin-bottom: 10px;
}

.feature-card p {
  color: #606266;
  margin-bottom: 20px;
  min-height: 60px;
}

.stats-row {
  margin-top: 20px;
}

.stat-card {
  text-align: center;
}
</style>
