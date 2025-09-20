<template>
  <div class="pc-export-import-container">
    <el-card class="page-header">
      <h1>📁 PC Export & Import</h1>
      <p>Export data to your PC folders and import from external sources</p>
    </el-card>

    <el-tabs v-model="activeTab" class="main-tabs">
      <!-- Export to PC Tab -->
      <el-tab-pane label="📤 Export to PC" name="export">
        <el-card>
          <template #header>
            <span>Export Data to Your PC</span>
          </template>
          
          <el-form @submit.prevent="performExport" label-width="120px">
            <el-form-item label="PC Folder Path" required>
              <el-input
                v-model="exportForm.pcFolder"
                placeholder="e.g., /Users/john/ipam-exports or C:\Users\john\ipam-exports"
                style="width: 100%"
              >
                <template #prepend>📂</template>
                <template #append>
                  <el-button-group>
                    <el-button @click="showFolderHelp" icon="QuestionFilled" size="small" title="Show help">
                      Help
                    </el-button>
                    <el-button @click="promptForUsername" icon="User" size="small" title="Set your username for better path defaults">
                      User
                    </el-button>
                  </el-button-group>
                </template>
              </el-input>
              <div class="form-help">
                Enter the full path to the folder on your PC where you want to save the export
              </div>
              <el-alert
                :title="getBrowserCapabilityTitle()"
                :type="getBrowserCapabilityType()"
                :closable="false"
                show-icon
                style="margin-top: 10px"
              >
                <div v-html="getBrowserCapabilityMessage()"></div>
              </el-alert>
            </el-form-item>
            
            
            <el-form-item label="Export Name">
              <el-input
                v-model="exportForm.exportName"
                placeholder="Optional custom name (auto-generated if empty)"
                style="width: 100%"
              >
                <template #prepend>🏷️</template>
              </el-input>
              <div class="form-help">
                Leave empty to auto-generate a timestamped name
              </div>
            </el-form-item>
            
            <el-form-item>
              <el-button 
                type="primary" 
                @click="performExport"
                :loading="exporting"
                icon="Upload"
                size="large"
              >
                Export to PC
              </el-button>
              <el-button 
                @click="clearExportForm"
                icon="RefreshLeft"
              >
                Clear
              </el-button>
            </el-form-item>
          </el-form>

          <el-divider>Recent Exports</el-divider>
          
          <div v-if="recentExports.length > 0" class="recent-exports">
            <el-table :data="recentExports" size="small">
              <el-table-column prop="export_name" label="Export Name" />
              <el-table-column prop="export_path" label="PC Path" />
              <el-table-column prop="timestamp" label="Created" :formatter="formatTimestamp" />
              <el-table-column prop="files_created" label="Files" />
            </el-table>
          </div>
          <div v-else class="empty-state">
            <el-empty description="No recent exports" />
          </div>
        </el-card>
      </el-tab-pane>

      <!-- Import from PC Tab -->
      <el-tab-pane label="📥 Import from PC" name="import">
        <el-card>
          <template #header>
            <span>Import Data from Your PC</span>
          </template>
          
          <el-form @submit.prevent="scanFolder" label-width="120px">
            <el-form-item label="PC Folder Path" required>
              <el-input
                v-model="importForm.pcFolder"
                placeholder="e.g., /Users/john/ipam-exports/my_export or C:\Users\john\ipam-exports\my_export"
                style="width: 100%"
              >
                <template #prepend>📂</template>
                <template #append>
                  <el-button @click="scanFolder" :loading="scanning" icon="Search" type="primary">
                    Scan
                  </el-button>
                </template>
              </el-input>
              <div class="form-help">
                Enter the path to a folder containing IPAM export files
              </div>
            </el-form-item>
            
          </el-form>

          <!-- Scan Results -->
          <div v-if="scanResults" class="scan-results">
            <el-divider>Scan Results</el-divider>
            
            <el-alert
              v-if="scanResults.valid_exports === 0"
              title="No valid exports found"
              type="warning"
              :closable="false"
              show-icon
            >
              The specified folder does not contain valid IPAM export files.
            </el-alert>
            
            <div v-else>
              <el-alert
                :title="`Found ${scanResults.valid_exports} valid export(s)`"
                type="success"
                :closable="false"
                show-icon
              />
              
              <div class="exports-found">
                <h4>Available Exports:</h4>
                <el-table :data="scanResults.exports_found" size="small">
                  <el-table-column prop="folder_name" label="Export Name" />
                  <el-table-column prop="timestamp" label="Created" :formatter="formatTimestamp" />
                  <el-table-column label="Status">
                    <template #default="scope">
                      <el-tag :type="scope.row.is_valid ? 'success' : 'danger'">
                        {{ scope.row.is_valid ? 'Valid' : 'Invalid' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column label="Summary" v-if="scanResults.valid_exports > 0">
                    <template #default="scope">
                      <div v-if="scope.row.summary">
                        VRFs: {{ scope.row.summary.total_vrfs || 0 }}, 
                        VPCs: {{ scope.row.summary.total_vpcs || 0 }}, 
                        Prefixes: {{ scope.row.summary.total_prefixes || 0 }}
                      </div>
                    </template>
                  </el-table-column>
                  <el-table-column label="Actions" width="120">
                    <template #default="scope">
                      <el-button
                        v-if="scope.row.is_valid"
                        size="small"
                        type="success"
                        @click="confirmImport(scope.row)"
                        :disabled="importing"
                      >
                        Import
                      </el-button>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </div>
          </div>

          <!-- Validation Details -->
          <div v-if="validationResults" class="validation-results">
            <el-divider>Validation Details</el-divider>
            
            <el-descriptions :column="2" border>
              <el-descriptions-item label="Folder Valid">
                <el-tag :type="validationResults.validation.is_valid ? 'success' : 'danger'">
                  {{ validationResults.validation.is_valid ? 'Yes' : 'No' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="Files Found">
                {{ validationResults.validation.found_files.length }}
              </el-descriptions-item>
              <el-descriptions-item label="Missing Files" v-if="validationResults.validation.missing_files.length > 0">
                <el-tag type="warning" v-for="file in validationResults.validation.missing_files" :key="file">
                  {{ file }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-tab-pane>

    </el-tabs>

    <!-- Import Confirmation Dialog -->
    <el-dialog
      v-model="importDialogVisible"
      title="Confirm Import"
      width="60%"
    >
      <div class="import-warning">
        <el-alert
          title="Warning: This will replace current data!"
          type="warning"
          :closable="false"
          show-icon
        >
          <p>Importing data will:</p>
          <ul>
            <li>Add new VRFs, VPCs, and Prefixes from the export</li>
            <li>Update existing items if they have the same IDs</li>
            <li>May cause conflicts with current data</li>
          </ul>
          <p><strong>Consider creating a backup first!</strong></p>
        </el-alert>
        
        <div v-if="importCandidate" class="import-info">
          <h4>Import from:</h4>
          <p><strong>{{ importCandidate.folder_name }}</strong></p>
          <p>Path: {{ importCandidate.folder_path }}</p>
          <p v-if="importCandidate.timestamp">Created: {{ formatTimestamp({ timestamp: importCandidate.timestamp }) }}</p>
          <div v-if="importCandidate.summary" class="import-summary">
            <p>Contains:</p>
            <ul>
              <li>VRFs: {{ importCandidate.summary.total_vrfs || 0 }}</li>
              <li>VPCs: {{ importCandidate.summary.total_vpcs || 0 }}</li>
              <li>Prefixes: {{ importCandidate.summary.total_prefixes || 0 }}</li>
              <li>Public IPs: {{ importCandidate.summary.total_public_ips || 0 }}</li>
            </ul>
          </div>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="importDialogVisible = false">Cancel</el-button>
        <el-button 
          type="primary" 
          @click="performImport"
          :loading="importing"
        >
          Import Now
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { pcExportImportAPI } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'PCExportImport',
  data() {
    return {
      activeTab: 'export',
      
      // Export form
      exportForm: {
        pcFolder: '',
        exportName: ''
      },
      exporting: false,
      recentExports: [],
      
      // Import form
      importForm: {
        pcFolder: ''
      },
      scanning: false,
      importing: false,
      scanResults: null,
      validationResults: null,
      
      
      // Import dialog
      importDialogVisible: false,
      importCandidate: null
    }
  },
  mounted() {
    // Set default paths based on OS
    this.setDefaultPaths()
    
    // Check if username is set, if not and using generic 'user', offer to set it
    const currentUser = this.getCurrentUsername()
    if (currentUser === 'user' && !localStorage.getItem('ipam_username')) {
      // Delay the prompt slightly to let the component fully load
      setTimeout(() => {
        ElMessageBox.confirm(
          'Would you like to set your username for better default folder paths?\n\nThis will help generate more accurate paths like /Users/[your-name]/Downloads instead of /Users/user/Downloads',
          'Improve Path Defaults',
          {
            confirmButtonText: 'Yes, Set Username',
            cancelButtonText: 'Maybe Later',
            type: 'info'
          }
        ).then(() => {
          this.promptForUsername()
        }).catch(() => {
          // User declined, that's fine
        })
      }, 1000)
    }
  },
  methods: {
    setDefaultPaths() {
      // Detect OS and set appropriate default paths with dynamic user detection
      const userAgent = navigator.userAgent
      const currentUser = this.getCurrentUsername()
      
      if (userAgent.includes('Mac')) {
        this.exportForm.pcFolder = `/Users/${currentUser}/tmp/ipambackup`
      } else if (userAgent.includes('Win')) {
        this.exportForm.pcFolder = `C:\\Users\\${currentUser}\\ipam-exports`
      } else {
        this.exportForm.pcFolder = `/home/${currentUser}/ipam-exports`
      }
    },
    
    getCurrentUsername() {
      // Try to get username from localStorage first (user preference)
      const savedUsername = localStorage.getItem('ipam_username')
      if (savedUsername) {
        return savedUsername
      }
      
      // Try to detect current username from various sources
      // Note: These may not always be available due to browser security
      
      // Method 1: Try environment variables (limited availability in browsers)
      if (typeof process !== 'undefined' && process.env) {
        if (process.env.USER) return process.env.USER
        if (process.env.USERNAME) return process.env.USERNAME
        if (process.env.LOGNAME) return process.env.LOGNAME
      }
      
      // Method 2: Provide OS-appropriate fallback that prompts user to customize
      const userAgent = navigator.userAgent
      if (userAgent.includes('Mac')) {
        return 'user' // Will be replaced by user's actual username
      } else if (userAgent.includes('Win')) {
        return 'user' // Will be replaced by user's actual username
      } else {
        return 'user' // Will be replaced by user's actual username
      }
    },
    
    async promptForUsername() {
      // Prompt user to set their username for better path defaults
      const userAgent = navigator.userAgent
      let placeholder = 'john'
      let example = '/Users/john/Downloads'
      
      if (userAgent.includes('Win')) {
        example = 'C:\\Users\\john\\Downloads'
      } else if (userAgent.includes('Linux')) {
        example = '/home/john/Downloads'
      }
      
      try {
        const result = await ElMessageBox.prompt(
          `To provide better default paths, please enter your username.\n\nThis will be used to generate paths like: ${example}`,
          'Set Username for Path Defaults',
          {
            confirmButtonText: 'Save',
            cancelButtonText: 'Skip',
            inputPlaceholder: placeholder,
            inputValue: ''
          }
        )
        
        if (result.value && result.value.trim()) {
          const username = result.value.trim()
          localStorage.setItem('ipam_username', username)
          ElMessage.success(`Username saved! Paths will now use: ${username}`)
          
          // Update current paths
          this.setDefaultPaths()
          return username
        }
      } catch (error) {
        // User cancelled, that's fine
      }
      
      return 'user' // fallback
    },
    
    async performExport() {
      if (!this.exportForm.pcFolder.trim()) {
        ElMessage.warning('Please enter a PC folder path')
        return
      }
      
      this.exporting = true
      try {
        const response = await pcExportImportAPI.exportToPC(
          this.exportForm.pcFolder,
          this.exportForm.exportName || undefined
        )
        
        ElMessage.success('Export completed successfully!')
        
        // Add to recent exports
        this.recentExports.unshift({
          export_name: response.data.export_name,
          export_path: response.data.export_path,
          timestamp: response.data.timestamp,
          files_created: response.data.files_created
        })
        
        // Keep only last 5 exports
        if (this.recentExports.length > 5) {
          this.recentExports = this.recentExports.slice(0, 5)
        }
        
        this.clearExportForm()
      } catch (error) {
        ElMessage.error('Export failed: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.exporting = false
      }
    },
    
    clearExportForm() {
      this.exportForm.exportName = ''
    },
    
    
    
    getDefaultPathForFolder(folderName) {
      // Provide a smart default based on the folder name and your known setup
      const userAgent = navigator.userAgent
      
      const currentUser = this.getCurrentUsername()
      
      // Special case for known folders
      if (folderName === 'ipambackup' && userAgent.includes('Mac')) {
        return `/Users/${currentUser}/tmp/ipambackup`
      }
      
      // General defaults based on OS
      if (userAgent.includes('Mac')) {
        return `/Users/${currentUser}/Desktop/${folderName}`
      } else if (userAgent.includes('Win')) {
        return `C:\\Users\\${currentUser}\\Desktop\\${folderName}`
      } else {
        return `/home/${currentUser}/Desktop/${folderName}`
      }
    },
    
    getSmartPathGuess(folderName) {
      // Provide multiple common path guesses based on folder name and OS
      const userAgent = navigator.userAgent
      const currentUser = this.getCurrentUsername()
      
      // Special cases for known folders
      if (folderName === 'ipambackup' && userAgent.includes('Mac')) {
        return `/Users/${currentUser}/tmp/ipambackup`
      }
      
      if (userAgent.includes('Mac')) {
        // Common macOS locations - prioritize Downloads since it's commonly used
        const commonPaths = [
          `/Users/${currentUser}/Downloads/${folderName}`,
          `/Users/${currentUser}/Desktop/${folderName}`,
          `/Users/${currentUser}/Documents/${folderName}`,
          `/Users/${currentUser}/${folderName}`,
          `/tmp/${folderName}`
        ]
        
        // For now, return Downloads as the most likely guess
        // In the future, we could try to detect based on recent browser downloads
        return `/Users/${currentUser}/Downloads/${folderName}`
      } else if (userAgent.includes('Win')) {
        return `C:\\Users\\${currentUser}\\Downloads\\${folderName}`
      } else {
        return `/home/${currentUser}/Downloads/${folderName}`
      }
    },
    
    getPathPlaceholder() {
      const userAgent = navigator.userAgent
      if (userAgent.includes('Win')) {
        return 'C:\\Users\\username\\Documents\\my-folder'
      } else if (userAgent.includes('Mac')) {
        return '/Users/username/Documents/my-folder'
      } else {
        return '/home/username/Documents/my-folder'
      }
    },
    
    
    showFolderHelp() {
      const userAgent = navigator.userAgent
      let helpMessage = 'Common folder paths:\n\n'
      
      if (userAgent.includes('Mac')) {
        helpMessage += '• Desktop: /Users/[username]/Desktop\n'
        helpMessage += '• Documents: /Users/[username]/Documents\n'
        helpMessage += '• Downloads: /Users/[username]/Downloads\n'
        helpMessage += '• Custom: /Users/[username]/my-exports\n\n'
        helpMessage += 'Example: /Users/wwang2/tmp/ipambackup'
      } else if (userAgent.includes('Win')) {
        helpMessage += '• Desktop: C:\\Users\\[username]\\Desktop\n'
        helpMessage += '• Documents: C:\\Users\\[username]\\Documents\n'
        helpMessage += '• Downloads: C:\\Users\\[username]\\Downloads\n'
        helpMessage += '• Custom: C:\\Users\\[username]\\my-exports\n\n'
        helpMessage += 'Example: C:\\Users\\john\\ipam-exports'
      } else {
        helpMessage += '• Desktop: /home/[username]/Desktop\n'
        helpMessage += '• Documents: /home/[username]/Documents\n'
        helpMessage += '• Downloads: /home/[username]/Downloads\n'
        helpMessage += '• Custom: /home/[username]/my-exports\n\n'
        helpMessage += 'Example: /home/john/ipam-exports'
      }
      
      helpMessage += '\n\nTip: Use the "User" button to set your username for better default paths!'
      
      ElMessageBox.alert(helpMessage, 'PC Folder Path Help', {
        confirmButtonText: 'Got it',
        type: 'info'
      })
    },
    
    
    async scanFolder() {
      if (!this.importForm.pcFolder.trim()) {
        ElMessage.warning('Please enter a PC folder path')
        return
      }
      
      this.scanning = true
      this.scanResults = null
      this.validationResults = null
      
      try {
        const response = await pcExportImportAPI.scanPCFolder(this.importForm.pcFolder)
        this.scanResults = response.data
        
        // Also validate the folder
        const validationResponse = await pcExportImportAPI.validatePCFolder(this.importForm.pcFolder)
        this.validationResults = validationResponse.data
        
      } catch (error) {
        ElMessage.error('Scan failed: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.scanning = false
      }
    },
    
    
    confirmImport(exportItem) {
      this.importCandidate = exportItem
      this.importDialogVisible = true
    },
    
    async performImport() {
      if (!this.importCandidate) return
      
      this.importing = true
      
      try {
        const response = await pcExportImportAPI.importFromPC(this.importCandidate.folder_path)
        ElMessage.success('Import completed successfully!')
        this.importDialogVisible = false
        
        // Clear results to force refresh
        this.scanResults = null
        this.validationResults = null
        
      } catch (error) {
        ElMessage.error('Import failed: ' + (error.response?.data?.detail || error.message))
      } finally {
        this.importing = false
      }
    },
    
    getBrowserCapabilityTitle() {
      return 'Manual Path Entry'
    },
    
    getBrowserCapabilityType() {
      return 'info'
    },
    
    getBrowserCapabilityMessage() {
      const userAgent = navigator.userAgent
      let examples = ''
      
      if (userAgent.includes('Mac')) {
        examples = '<strong>macOS examples:</strong><br>' +
                  '• /Users/john/Desktop/my-exports<br>' +
                  '• /Users/john/Downloads/ipam-backup<br>' +
                  '• /Users/john/Documents/exports'
      } else if (userAgent.includes('Win')) {
        examples = '<strong>Windows examples:</strong><br>' +
                  '• C:\\Users\\john\\Desktop\\my-exports<br>' +
                  '• C:\\Users\\john\\Downloads\\ipam-backup<br>' +
                  '• C:\\Users\\john\\Documents\\exports'
      } else {
        examples = '<strong>Linux examples:</strong><br>' +
                  '• /home/john/Desktop/my-exports<br>' +
                  '• /home/john/Downloads/ipam-backup<br>' +
                  '• /home/john/Documents/exports'
      }
      
      return '<p><strong>💡 Enter the full path to your folder manually</strong></p>' +
             '<p>Use the "User" button to set your username for better default paths.</p>' +
             '<p>' + examples + '</p>'
    },
    
    formatTimestamp(row) {
      const timestamp = row.timestamp
      if (!timestamp) return 'Unknown'
      
      try {
        const date = new Date(timestamp)
        return date.toLocaleString()
      } catch {
        return timestamp
      }
    }
  }
}
</script>

<style scoped>
.pc-export-import-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 10px 0;
  color: #409EFF;
}

.main-tabs {
  margin-top: 20px;
}

.form-help {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.recent-exports {
  margin-top: 15px;
}

.empty-state {
  text-align: center;
  padding: 20px;
}

.scan-results,
.validation-results {
  margin-top: 20px;
}

.exports-found h4 {
  margin: 15px 0 10px 0;
  color: #303133;
}


.import-warning {
  margin-bottom: 20px;
}

.import-warning ul {
  margin: 10px 0;
  padding-left: 20px;
}

.import-info {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.import-info h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.import-info p {
  margin: 5px 0;
  color: #606266;
}

.import-summary {
  margin-top: 10px;
}

.import-summary ul {
  margin: 5px 0;
  padding-left: 20px;
}

.import-summary li {
  margin: 3px 0;
}
</style>
