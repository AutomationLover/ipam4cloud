<template>
  <div id="readonly-app">
    <el-container>
      <el-header>
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          router
          background-color="#2c3e50"
          text-color="#ecf0f1"
          active-text-color="#3498db"
        >
          <el-menu-item index="/">
            <el-icon><Grid /></el-icon>
            <span>Prefix Query System</span>
          </el-menu-item>
          <el-menu-item index="/prefixes">
            <el-icon><List /></el-icon>
            <span>Prefixes</span>
          </el-menu-item>
          <el-menu-item index="/vrfs">
            <el-icon><Connection /></el-icon>
            <span>VRFs</span>
          </el-menu-item>
          <el-menu-item index="/vpcs">
            <el-icon><Monitor /></el-icon>
            <span>VPCs</span>
          </el-menu-item>
          <el-menu-item index="/ip-addresses">
            <el-icon><Search /></el-icon>
            <span>IP Addresses</span>
          </el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer style="text-align: center; color: #909399; font-size: 12px;">
        IPAM4Cloud - Read-Only Portal (Port 8081) |
        <el-icon><InfoFilled /></el-icon>
        This interface provides query-only access to network resources
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import { Grid, List, Connection, Monitor, Search } from '@element-plus/icons-vue'

export default {
  name: 'ReadOnlyApp',
  components: {
    Grid,
    List,
    Connection,
    Monitor,
    Search
  },
  methods: {
    // Reserved for future methods
  }
}
</script>

<style>
#readonly-app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

.el-header {
  padding: 0;
  position: relative;
}

.el-menu--horizontal {
  border-bottom: none;
}

.el-main {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 120px);
}

.el-footer {
  background-color: #2c3e50;
  color: #ecf0f1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
</style>
