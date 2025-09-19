<template>
  <div id="app">
    <el-container>
      <el-header>
        <el-menu
          :default-active="$route.path"
          mode="horizontal"
          router
          background-color="#545c64"
          text-color="#fff"
          active-text-color="#ffd04b"
        >
          <el-menu-item index="/">
            <el-icon><Grid /></el-icon>
            <span>Prefix Management</span>
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
          <div class="header-right">
            <el-button 
              type="info" 
              size="small" 
              @click="goToReadOnlyPortal"
              plain
            >
              <el-icon><View /></el-icon>
              Read-Only Portal
            </el-button>
          </div>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { Grid, List, Connection, Monitor, View } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

export default {
  name: 'App',
  components: {
    Grid,
    List,
    Connection,
    Monitor,
    View
  },
  methods: {
    async goToReadOnlyPortal() {
      try {
        await ElMessageBox.confirm(
          'You will be redirected to the Read-Only Portal (port 8081) where you can only view and query resources. Continue?',
          'Go to Read-Only Portal',
          {
            confirmButtonText: 'Go to Read-Only Portal',
            cancelButtonText: 'Stay in Admin Portal',
            type: 'info'
          }
        )
        
        // Redirect to readonly portal on port 8081
        window.location.href = 'http://localhost:8081'
      } catch (error) {
        // User cancelled, stay in admin portal
      }
    }
  }
}
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

.el-header {
  padding: 0;
  position: relative;
}

.el-main {
  padding: 20px;
}

.header-right {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
}
</style>

