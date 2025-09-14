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
              @click="switchToReadOnly"
              plain
            >
              <el-icon><View /></el-icon>
              Read-Only Interface
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
    async switchToReadOnly() {
      try {
        await ElMessageBox.confirm(
          'You are about to switch to the read-only interface where you can only view and query resources. Continue?',
          'Switch to Read-Only Interface',
          {
            confirmButtonText: 'Switch to Read-Only',
            cancelButtonText: 'Stay in Management',
            type: 'info'
          }
        )
        
        // Switch to read-only interface
        this.$router.push('/readonly')
      } catch (error) {
        // User cancelled, stay in management mode
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

