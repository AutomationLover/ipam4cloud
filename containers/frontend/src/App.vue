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
          <el-menu-item index="/export-import">
            <el-icon><Download /></el-icon>
            <span>Export/Import</span>
          </el-menu-item>
        </el-menu>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </div>
</template>

<script>
import { Grid, List, Connection, Monitor, Download } from '@element-plus/icons-vue'

export default {
  name: 'App',
  components: {
    Grid,
    List,
    Connection,
    Monitor,
    Download
  },
  methods: {
    // Reserved for future methods
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
</style>

