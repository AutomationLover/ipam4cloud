<template>
  <div class="export-import-container">
    <!-- Header -->
    <div class="header-section">
      <h1 class="page-title">
        <i class="fas fa-eye"></i>
        Data Export Viewer
      </h1>
      <p class="page-description">
        View available data exports. This is a read-only interface.
      </p>
    </div>

    <!-- Read-only Notice -->
    <div class="readonly-notice">
      <i class="fas fa-info-circle"></i>
      <div>
        <strong>Read-Only Mode</strong>
        <p>You can view available exports but cannot create new exports or import data. Use the admin interface for full functionality.</p>
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
        <p>No export files are currently available.</p>
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
            <div class="summary-item">
              <span class="label">Manual:</span>
              <span class="value">{{ exportItem.summary?.manual_prefixes || 0 }}</span>
            </div>
            <div class="summary-item">
              <span class="label">VPC:</span>
              <span class="value">{{ exportItem.summary?.vpc_prefixes || 0 }}</span>
            </div>
          </div>

          <div class="export-files">
            <h4>Export Files:</h4>
            <div class="file-list">
              <div 
                v-for="(filePath, fileType) in exportItem.files" 
                :key="fileType"
                class="file-item"
              >
                <i class="fas fa-file-code"></i>
                <span class="file-type">{{ fileType }}</span>
                <span class="file-size">{{ getFileSize(filePath) }}</span>
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
              @click="downloadFile(exportItem.manifest_file)"
              class="btn btn-sm btn-primary"
            >
              <i class="fas fa-download"></i>
              Download Manifest
            </button>
            <button 
              @click="viewExportDetails(exportItem)"
              class="btn btn-sm btn-outline"
            >
              <i class="fas fa-info-circle"></i>
              View Details
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Export Details Modal -->
    <div v-if="selectedExport" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Export Details</h3>
          <button @click="closeModal" class="btn-close">
            <i class="fas fa-times"></i>
          </button>
        </div>
        <div class="modal-body">
          <div class="detail-section">
            <h4>Export Information</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Timestamp:</span>
                <span class="value">{{ formatDate(selectedExport.timestamp) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Manifest File:</span>
                <span class="value">{{ selectedExport.manifest_file }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h4>Data Summary</h4>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Total VRFs:</span>
                <span class="value">{{ selectedExport.summary?.total_vrfs || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Total VPCs:</span>
                <span class="value">{{ selectedExport.summary?.total_vpcs || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Total Prefixes:</span>
                <span class="value">{{ selectedExport.summary?.total_prefixes || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Manual Prefixes:</span>
                <span class="value">{{ selectedExport.summary?.manual_prefixes || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">VPC Prefixes:</span>
                <span class="value">{{ selectedExport.summary?.vpc_prefixes || 0 }}</span>
              </div>
              <div class="detail-item">
                <span class="label">VPC Associations:</span>
                <span class="value">{{ selectedExport.summary?.vpc_associations || 0 }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h4>Export Files</h4>
            <div class="file-details">
              <div 
                v-for="(filePath, fileType) in selectedExport.files" 
                :key="fileType"
                class="file-detail-item"
              >
                <div class="file-info">
                  <i class="fas fa-file-code"></i>
                  <div>
                    <strong>{{ fileType }}</strong>
                    <p>{{ filePath }}</p>
                  </div>
                </div>
                <button 
                  @click="downloadFile(filePath)" 
                  class="btn btn-sm btn-outline"
                >
                  <i class="fas fa-download"></i>
                  Download
                </button>
              </div>
            </div>
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
      // Exports list
      exports: [],
      exportsLoading: false,
      
      // Modal
      selectedExport: null,
      
      // Status
      statusMessage: null
    }
  },
  
  mounted() {
    this.refreshExports()
  },
  
  methods: {
    async refreshExports() {
      this.exportsLoading = true
      
      try {
        const response = await exportImportAPI.listExports('exports')
        this.exports = response.data.exports || []
      } catch (error) {
        console.error('Failed to load exports:', error)
        this.exports = []
        this.showStatusMessage('error', 'Load Failed', 'Failed to load export list.')
      } finally {
        this.exportsLoading = false
      }
    },
    
    downloadFile(filePath) {
      try {
        exportImportAPI.downloadExport(filePath)
        this.showStatusMessage('success', 'Download Started', 'File download has been initiated.')
      } catch (error) {
        this.showStatusMessage('error', 'Download Failed', 'Failed to start file download.')
      }
    },
    
    viewExportDetails(exportItem) {
      this.selectedExport = exportItem
    },
    
    closeModal() {
      this.selectedExport = null
    },
    
    getFileSize(filePath) {
      // This would need to be implemented on the backend
      // For now, return a placeholder
      return 'Unknown'
    },
    
    showStatusMessage(type, title, message) {
      this.statusMessage = { type, title, message }
      
      // Auto-clear success messages after 3 seconds
      if (type === 'success') {
        setTimeout(() => {
          this.clearStatusMessage()
        }, 3000)
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
  margin-bottom: 30px;
}

.page-title {
  font-size: 2.5rem;
  color: #2c3e50;
  margin-bottom: 10px;
}

.page-title i {
  margin-right: 15px;
  color: #7f8c8d;
}

.page-description {
  font-size: 1.1rem;
  color: #7f8c8d;
  max-width: 600px;
  margin: 0 auto;
}

.readonly-notice {
  background: #e8f4fd;
  border: 1px solid #bee5eb;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
  display: flex;
  align-items: flex-start;
}

.readonly-notice i {
  font-size: 1.5rem;
  color: #17a2b8;
  margin-right: 15px;
  margin-top: 2px;
}

.readonly-notice strong {
  display: block;
  margin-bottom: 5px;
  color: #0c5460;
}

.readonly-notice p {
  margin: 0;
  color: #0c5460;
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
  color: #7f8c8d;
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
  color: #7f8c8d;
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
  gap: 15px;
  margin-bottom: 15px;
  flex-wrap: wrap;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 12px;
  background: white;
  border-radius: 6px;
  min-width: 70px;
}

.summary-item .label {
  font-size: 0.75rem;
  color: #7f8c8d;
  margin-bottom: 3px;
}

.summary-item .value {
  font-size: 1.1rem;
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
  color: #7f8c8d;
}

.file-type {
  flex: 1;
  font-family: monospace;
  font-size: 0.9rem;
}

.file-size {
  font-size: 0.8rem;
  color: #7f8c8d;
  margin-right: 10px;
}

.export-actions {
  display: flex;
  gap: 10px;
}

.btn {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

.btn i {
  margin-right: 6px;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.8rem;
}

.btn-primary {
  background: #7f8c8d;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #6c757d;
}

.btn-outline {
  background: transparent;
  border: 2px solid #7f8c8d;
  color: #7f8c8d;
}

.btn-outline:hover:not(:disabled) {
  background: #7f8c8d;
  color: white;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #ecf0f1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  color: #2c3e50;
}

.btn-close {
  background: none;
  border: none;
  color: #7f8c8d;
  cursor: pointer;
  padding: 5px;
  font-size: 1.2rem;
}

.modal-body {
  padding: 20px;
}

.detail-section {
  margin-bottom: 25px;
}

.detail-section h4 {
  margin: 0 0 15px 0;
  color: #2c3e50;
  border-bottom: 2px solid #ecf0f1;
  padding-bottom: 8px;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
}

.detail-item {
  display: flex;
  flex-direction: column;
}

.detail-item .label {
  font-size: 0.9rem;
  color: #7f8c8d;
  margin-bottom: 5px;
}

.detail-item .value {
  font-weight: 600;
  color: #2c3e50;
}

.file-details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.file-detail-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #ecf0f1;
}

.file-info {
  display: flex;
  align-items: center;
  flex: 1;
}

.file-info i {
  margin-right: 12px;
  color: #7f8c8d;
  font-size: 1.2rem;
}

.file-info strong {
  display: block;
  margin-bottom: 3px;
  color: #2c3e50;
}

.file-info p {
  margin: 0;
  font-size: 0.9rem;
  color: #7f8c8d;
  font-family: monospace;
}

.status-message {
  position: fixed;
  top: 20px;
  right: 20px;
  max-width: 400px;
  padding: 15px;
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

.status-message i {
  margin-right: 12px;
  margin-top: 2px;
  font-size: 1.1rem;
}

.message-content {
  flex: 1;
}

.message-content strong {
  display: block;
  margin-bottom: 3px;
}

.message-content p {
  margin: 0;
  font-size: 0.9rem;
}

@media (max-width: 768px) {
  .export-summary {
    justify-content: center;
  }
  
  .export-actions {
    flex-direction: column;
  }
  
  .detail-grid {
    grid-template-columns: 1fr;
  }
  
  .modal-content {
    width: 95%;
    margin: 10px;
  }
}
</style>
