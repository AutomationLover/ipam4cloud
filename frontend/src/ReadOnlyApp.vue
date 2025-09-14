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
          <el-menu-item index="/readonly">
            <el-icon><Grid /></el-icon>
            <span>Prefix Query System</span>
          </el-menu-item>
          <el-menu-item index="/readonly/prefixes">
            <el-icon><List /></el-icon>
            <span>Prefixes</span>
          </el-menu-item>
          <el-menu-item index="/readonly/vrfs">
            <el-icon><Connection /></el-icon>
            <span>VRFs</span>
          </el-menu-item>
          <el-menu-item index="/readonly/vpcs">
            <el-icon><Monitor /></el-icon>
            <span>VPCs</span>
          </el-menu-item>
          <div class="header-right">
            <el-tag type="info" size="large">
              <el-icon><View /></el-icon>
              Read-Only Mode
            </el-tag>
            <el-button 
              type="primary" 
              size="small" 
              @click="switchToManagement"
              style="margin-left: 12px;"
            >
              <el-icon><Setting /></el-icon>
              Management Interface
            </el-button>
          </div>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <el-footer style="text-align: center; color: #909399; font-size: 12px;">
        Prefix Management System - Read-Only Interface | 
        <el-icon><InfoFilled /></el-icon>
        This interface provides query-only access to network resources
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import { Grid, List, Connection, Monitor, View, Setting, InfoFilled } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'

export default {
  name: 'ReadOnlyApp',
  components: {
    Grid,
    List,
    Connection,
    Monitor,
    View,
    Setting,
    InfoFilled
  },
  methods: {
    async switchToManagement() {
      try {
        await ElMessageBox.confirm(
          'You are about to switch to the management interface where you can create, edit, and delete resources. Continue?',
          'Switch to Management Interface',
          {
            confirmButtonText: 'Switch to Management',
            cancelButtonText: 'Stay in Read-Only',
            type: 'warning'
          }
        )
        
        // Switch to management interface
        window.location.href = '/'
      } catch (error) {
        // User cancelled, stay in read-only mode
      }
    }
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

.header-right {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
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
