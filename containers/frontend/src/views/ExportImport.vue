<template>
  <div class="export-import-container">
    <!-- Header -->
    <div class="header-section">
      <h1 class="page-title">
        <i class="fas fa-exchange-alt"></i>
        Data Export & Import
      </h1>
      <p class="page-description">
        Export your IPAM data for backup or migration, and import data from previous exports.
      </p>
    </div>

    <!-- Action Cards -->
    <div class="action-cards">
      <!-- Export Card -->
      <div class="action-card export-card">
        <div class="card-header">
          <i class="fas fa-download"></i>
          <h2>Export Data</h2>
        </div>
        <div class="card-content">
          <p>Export all system data including VRFs, VPCs, Prefixes, and Associations to JSON files.</p>
          
          <div class="form-group">
            <label for="exportDir">Export Directory:</label>
            <input 
              id="exportDir"
              v-model="exportDir" 
              type="text" 
              placeholder="exports"
              class="form-input"
            />
            <small class="help-text">Directory where export files will be saved</small>
          </div>

          <div class="export-info" v-if="lastExportInfo">
            <h4>Last Export:</h4>
            <p><strong>Date:</strong> {{ formatDate(lastExportInfo.timestamp) }}</p>
            <p><strong>Files:</strong> {{ Object.keys(lastExportInfo.exported_files || {}).length }}</p>
          </div>

          <button 
            @click="performExport" 
            :disabled="exportLoading"
            class="btn btn-primary btn-large"
          >
            <i class="fas fa-download" v-if="!exportLoading"></i>
            <i class="fas fa-spinner fa-spin" v-if="exportLoading"></i>
            {{ exportLoading ? 'Exporting...' : 'Export Data' }}
          </button>
        </div>
      </div>

      <!-- Import Card -->
      <div class="action-card import-card">
        <div class="card-header">
          <i class="fas fa-upload"></i>
          <h2>Import Data</h2>
        </div>
        <div class="card-content">
          <p>Import data from a previous export using the manifest file.</p>
          
          <div class="form-group">
            <label for="manifestFile">Manifest File:</label>
            <input 
              id="manifestFile"
              type="file" 
              @change="handleFileSelect"
              accept=".json"
              class="form-input file-input"
            />
            <small class="help-text">Select the export_manifest_*.json file from your export</small>
          </div>

          <div class="selected-file" v-if="selectedFile">
            <i class="fas fa-file-alt"></i>
            <span>{{ selectedFile.name }}</span>
            <button @click="clearSelectedFile" class="btn-clear">
              <i class="fas fa-times"></i>
            </button>
          </div>

          <div class="import-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <strong>Warning:</strong> Import will add data to the current system. 
            Existing data with the same IDs will be skipped.
          </div>

          <button 
            @click="performImport" 
            :disabled="importLoading || !selectedFile"
            class="btn btn-secondary btn-large"
          >
            <i class="fas fa-upload" v-if="!importLoading"></i>
            <i class="fas fa-spinner fa-spin" v-if="importLoading"></i>
            {{ importLoading ? 'Importing...' : 'Import Data' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Available Exports -->
    <div class="exports-section">
      <div class="section-header">
        <h2>
          <i class="fas fa-archive"></i>
          Available Exports
        </h2>
        <button @click="refreshExports" :disabled="exportsLoading" class="btn btn-outline">
          <i class="fas fa-sync-alt" :class="{ 'fa-spin': exportsLoading }"></i>
          Refresh
        </button>
      </div>

      <div v-if="exportsLoading" class="loading-state">
        <i class="fas fa-spinner fa-spin"></i>
        Loading exports...
      </div>

      <div v-else-if="exports.length === 0" class="empty-state">
        <i class="fas fa-inbox"></i>
        <h3>No Exports Found</h3>
        <p>Create your first export using the Export Data card above.</p>
      </div>

      <div v-else class="exports-grid">
        <div 
          v-for="exportItem in exports" 
          :key="exportItem.manifest_file"
          class="export-item"
        >
          <div class="export-header">
            <i class="fas fa-file-archive"></i>
            <div class="export-info">
              <h3>{{ formatDate(exportItem.timestamp) }}</h3>
              <p class="export-path">{{ exportItem.manifest_file }}</p>
            </div>
          </div>

          <div class="export-summary">
            <div class="summary-item">
              <span class="label">VRFs:</span>
              <span class="value">{{ exportItem.summary?.total_vrfs || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="label">VPCs:</span>
              <span class="value">{{ exportItem.summary?.total_vpcs || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="label">Prefixes:</span>
              <span class="value">{{ exportItem.summary?.total_prefixes || 0 }}</span>
            </div>
          </div>

          <div class="export-files">
            <h4>Files:</h4>
            <div class="file-list">
              <div 
                v-for="(filePath, fileType) in exportItem.files" 
                :key="fileType"
                class="file-item"
              >
                <i class="fas fa-file-code"></i>
                <span class="file-type">{{ fileType }}</span>
                <button 
                  @click="downloadFile(filePath)" 
                  class="btn btn-sm btn-outline"
                  title="Download file"
                >
                  <i class="fas fa-download"></i>
                </button>
              </div>
            </div>
          </div>

          <div class="export-actions">
            <button 
              @click="useForImport(exportItem.manifest_file)"
              class="btn btn-sm btn-primary"
            >
              <i class="fas fa-upload"></i>
              Use for Import
            </button>
            <button 
              @click="downloadFile(exportItem.manifest_file)"
              class="btn btn-sm btn-outline"
            >
              <i class="fas fa-download"></i>
              Download Manifest
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Status Messages -->
    <div v-if="statusMessage" :class="['status-message', statusMessage.type]">
      <i :class="getStatusIcon(statusMessage.type)"></i>
      <div class="message-content">
        <strong>{{ statusMessage.title }}</strong>
        <p>{{ statusMessage.message }}</p>
      </div>
      <button @click="clearStatusMessage" class="btn-close">
        <i class="fas fa-times"></i>
      </button>
    </div>
  </div>
</template>

<script>
import { exportImportAPI } from '@/api'

export default {
  name: 'ExportImport',
  data() {
    return {
      // Export state
      exportDir: 'exports',
      exportLoading: false,
      lastExportInfo: null,
      
      // Import state
      selectedFile: null,
      importLoading: false,
      
      // Exports list
      exports: [],
      exportsLoading: false,
      
      // Status
      statusMessage: null
    }
  },
  
  mounted() {
    this.refreshExports()
  },
  
  methods: {
    async performExport() {
      this.exportLoading = true
      this.clearStatusMessage()
      
      try {
        const response = await exportImportAPI.exportData(this.exportDir)
        
        this.lastExportInfo = response.data
        this.showStatusMessage('success', 'Export Successful', 
          `Data exported successfully to ${this.exportDir}. ${Object.keys(response.data.exported_files || {}).length} files created.`)
        
        // Refresh the exports list
        await this.refreshExports()
        
      } catch (error) {
        console.error('Export failed:', error)
        this.showStatusMessage('error', 'Export Failed', 
          error.response?.data?.detail || 'An error occurred during export.')
      } finally {
        this.exportLoading = false
      }
    },
    
    async performImport() {
      if (!this.selectedFile) {
        this.showStatusMessage('warning', 'No File Selected', 'Please select a manifest file to import.')
        return
      }
      
      this.importLoading = true
      this.clearStatusMessage()
      
      try {
        // For now, we'll use the file name as the manifest path
        // In a real implementation, you'd upload the file first
        const manifestPath = `${this.exportDir}/${this.selectedFile.name}`
        
        const response = await exportImportAPI.importData(manifestPath)
        
        this.showStatusMessage('success', 'Import Successful', 
          'Data imported successfully. The system has been updated with the imported data.')
        
        // Clear the selected file
        this.clearSelectedFile()
        
      } catch (error) {
        console.error('Import failed:', error)
        this.showStatusMessage('error', 'Import Failed', 
          error.response?.data?.detail || 'An error occurred during import.')
      } finally {
        this.importLoading = false
      }
    },
    
    async refreshExports() {
      this.exportsLoading = true
      
      try {
        const response = await exportImportAPI.listExports(this.exportDir)
        this.exports = response.data.exports || []
      } catch (error) {
        console.error('Failed to load exports:', error)
        this.exports = []
      } finally {
        this.exportsLoading = false
      }
    },
    
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        this.selectedFile = file
      }
    },
    
    clearSelectedFile() {
      this.selectedFile = null
      // Clear the file input
      const fileInput = document.getElementById('manifestFile')
      if (fileInput) {
        fileInput.value = ''
      }
    },
    
    useForImport(manifestFile) {
      // Create a mock file object for the UI
      this.selectedFile = {
        name: manifestFile.split('/').pop()
      }
      
      // Scroll to import section
      const importCard = document.querySelector('.import-card')
      if (importCard) {
        importCard.scrollIntoView({ behavior: 'smooth' })
      }
    },
    
    downloadFile(filePath) {
      exportImportAPI.downloadExport(filePath)
    },
    
    showStatusMessage(type, title, message) {
      this.statusMessage = { type, title, message }
      
      // Auto-clear success messages after 5 seconds
      if (type === 'success') {
        setTimeout(() => {
          this.clearStatusMessage()
        }, 5000)
      }
    },
    
    clearStatusMessage() {
      this.statusMessage = null
    },
    
    getStatusIcon(type) {
      const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
      }
      return icons[type] || 'fas fa-info-circle'
    },
    
    formatDate(timestamp) {
      if (!timestamp) return 'Unknown'
      
      // Handle different timestamp formats
      let date
      if (timestamp.includes('_')) {
        // Format: 20241220_143022
        const [datePart, timePart] = timestamp.split('_')
        const year = datePart.substring(0, 4)
        const month = datePart.substring(4, 6)
        const day = datePart.substring(6, 8)
        const hour = timePart.substring(0, 2)
        const minute = timePart.substring(2, 4)
        const second = timePart.substring(4, 6)
        
        date = new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`)
      } else {
        date = new Date(timestamp)
      }
      
      return date.toLocaleString()
    }
  }
}
</script>

<style scoped>
.export-import-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.header-section {
  text-align: center;
  margin-bottom: 40px;
}

.page-title {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-title i {
  margin-right: 15px;
  color: #3498db;
}

.page-description {
  font-size: 1.1rem;
  color: #7f8c8d;
  max-width: 600px;
  margin: 0 auto;
}

.action-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin-bottom: 50px;
}

.action-card {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.2s ease;
}

.action-card:hover {
  transform: translateY(-2px);
}

.card-header {
  background: linear-gradient(135deg, #3498db, #2980b9);
  color: white;
  padding: 20px;
  display: flex;
  align-items: center;
}

.export-card .card-header {
  background: linear-gradient(135deg, #27ae60, #229954);
}

.import-card .card-header {
  background: linear-gradient(135deg, #e74c3c, #c0392b);
}

.card-header i {
  font-size: 1.5rem;
  margin-right: 15px;
}

.card-header h2 {
  margin: 0;
  font-size: 1.3rem;
}

.card-content {
  padding: 25px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: #2c3e50;
}

.form-input {
  width: 100%;
  padding: 12px;
  border: 2px solid #ecf0f1;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: #3498db;
}

.file-input {
  padding: 8px;
}

.help-text {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-top: 5px;
  display: block;
}

.selected-file {
  display: flex;
  align-items: center;
  background: #ecf0f1;
  padding: 10px;
  border-radius: 6px;
  margin-bottom: 15px;
}

.selected-file i {
  margin-right: 10px;
  color: #3498db;
}

.btn-clear {
  margin-left: auto;
  background: none;
  border: none;
  color: #e74c3c;
  cursor: pointer;
  padding: 5px;
}

.export-info {
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
}

.export-info h4 {
  margin: 0 0 10px 0;
  color: #2c3e50;
}

.export-info p {
  margin: 5px 0;
  color: #5a6c7d;
}

.import-warning {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
  padding: 15px;
  border-radius: 6px;
  margin-bottom: 20px;
  display: flex;
  align-items: flex-start;
}

.import-warning i {
  margin-right: 10px;
  margin-top: 2px;
  color: #f39c12;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

.btn i {
  margin-right: 8px;
}

.btn-large {
  padding: 15px 30px;
  font-size: 1.1rem;
  width: 100%;
  justify-content: center;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-secondary {
  background: #e74c3c;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #c0392b;
}

.btn-outline {
  background: transparent;
  border: 2px solid #3498db;
  color: #3498db;
}

.btn-outline:hover:not(:disabled) {
  background: #3498db;
  color: white;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.9rem;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.exports-section {
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.section-header {
  background: #f8f9fa;
  padding: 20px;
  border-bottom: 1px solid #ecf0f1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header h2 {
  margin: 0;
  color: #2c3e50;
}

.section-header i {
  margin-right: 10px;
  color: #3498db;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #7f8c8d;
}

.empty-state i {
  font-size: 3rem;
  margin-bottom: 20px;
  color: #bdc3c7;
}

.empty-state h3 {
  margin-bottom: 10px;
  color: #5a6c7d;
}

.exports-grid {
  display: grid;
  gap: 20px;
  padding: 20px;
}

.export-item {
  border: 1px solid #ecf0f1;
  border-radius: 8px;
  padding: 20px;
  background: #fafbfc;
}

.export-header {
  display: flex;
  align-items: center;
  margin-bottom: 15px;
}

.export-header i {
  font-size: 1.5rem;
  color: #3498db;
  margin-right: 15px;
}

.export-info h3 {
  margin: 0;
  color: #2c3e50;
}

.export-path {
  margin: 5px 0 0 0;
  color: #7f8c8d;
  font-size: 0.9rem;
  font-family: monospace;
}

.export-summary {
  display: flex;
  gap: 20px;
  margin-bottom: 15px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px;
  background: white;
  border-radius: 6px;
  min-width: 80px;
}

.summary-item .label {
  font-size: 0.8rem;
  color: #7f8c8d;
  margin-bottom: 5px;
}

.summary-item .value {
  font-size: 1.2rem;
  font-weight: 600;
  color: #2c3e50;
}

.export-files {
  margin-bottom: 20px;
}

.export-files h4 {
  margin: 0 0 10px 0;
  color: #2c3e50;
  font-size: 1rem;
}

.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: white;
  border-radius: 4px;
  border: 1px solid #ecf0f1;
}

.file-item i {
  margin-right: 10px;
  color: #3498db;
}

.file-type {
  flex: 1;
  font-family: monospace;
  font-size: 0.9rem;
}

.export-actions {
  display: flex;
  gap: 10px;
}

.status-message {
  position: fixed;
  top: 20px;
  right: 20px;
  max-width: 400px;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: flex-start;
  z-index: 1000;
}

.status-message.success {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.status-message.error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.status-message.warning {
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  color: #856404;
}

.status-message i {
  margin-right: 15px;
  margin-top: 2px;
  font-size: 1.2rem;
}

.message-content {
  flex: 1;
}

.message-content strong {
  display: block;
  margin-bottom: 5px;
}

.message-content p {
  margin: 0;
  font-size: 0.9rem;
}

.btn-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 5px;
  margin-left: 10px;
}

@media (max-width: 768px) {
  .action-cards {
    grid-template-columns: 1fr;
  }
  
  .export-summary {
    flex-wrap: wrap;
  }
  
  .export-actions {
    flex-direction: column;
  }
}
</style>
