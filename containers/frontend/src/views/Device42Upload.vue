<template>
  <div class="device42-upload-container">
    <el-card class="page-header">
      <h1>📤 Device42 CSV Upload</h1>
      <p>Upload Device42 subnet and IP address CSV files to import data into the system</p>
    </el-card>

    <el-row :gutter="20" class="upload-section">
      <!-- Subnet Upload -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>📋 Upload Device42 Subnets CSV</span>
          </template>
          
          <el-upload
            ref="subnetUploadRef"
            :auto-upload="false"
            :on-change="handleSubnetFileChange"
            :file-list="subnetFileList"
            accept=".csv"
            :limit="1"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              Drop CSV file here or <em>click to upload</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                CSV files only (device42_subnet.csv)
              </div>
            </template>
          </el-upload>
          
          <div v-if="subnetFile" style="margin-top: 10px; margin-bottom: 10px;">
            <el-text type="info">File size: {{ subnetFileSize }}</el-text>
            <el-text v-if="subnetFile.size > 5 * 1024 * 1024" type="warning" style="margin-left: 10px;">
              ⚠️ Large file - processing may take several minutes
            </el-text>
          </div>
          
          <el-progress 
            v-if="uploadingSubnets" 
            :percentage="subnetUploadProgress" 
            :status="subnetUploadProgress === 100 ? 'success' : undefined"
            style="margin-top: 10px"
          />
          
          <el-button 
            type="primary" 
            @click="uploadSubnets"
            :loading="uploadingSubnets"
            :disabled="!subnetFile"
            style="margin-top: 20px; width: 100%"
            icon="Upload"
          >
            {{ uploadingSubnets ? 'Uploading & Processing...' : 'Upload Subnets CSV' }}
          </el-button>
          
          <div v-if="subnetUploadResult" class="upload-result" :class="subnetUploadResult.status">
            <el-alert
              :title="subnetUploadResult.message"
              :type="subnetUploadResult.status === 'success' ? 'success' : 'error'"
              :closable="false"
              style="margin-top: 20px"
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- IP Address Upload -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>📋 Upload Device42 IP Addresses CSV</span>
          </template>
          
          <el-upload
            ref="ipAddressUploadRef"
            :auto-upload="false"
            :on-change="handleIPAddressFileChange"
            :file-list="ipAddressFileList"
            accept=".csv"
            :limit="1"
            drag
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              Drop CSV file here or <em>click to upload</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                CSV files only (device42_ipaddress.csv)
              </div>
            </template>
          </el-upload>
          
          <div v-if="ipAddressFile" style="margin-top: 10px; margin-bottom: 10px;">
            <el-text type="info">File size: {{ ipAddressFileSize }}</el-text>
            <el-text v-if="ipAddressFile.size > 5 * 1024 * 1024" type="warning" style="margin-left: 10px;">
              ⚠️ Large file - processing may take several minutes
            </el-text>
          </div>
          
          <el-progress 
            v-if="uploadingIPAddresses" 
            :percentage="ipAddressUploadProgress" 
            :status="ipAddressUploadProgress === 100 ? 'success' : undefined"
            style="margin-top: 10px"
          />
          
          <el-button 
            type="primary" 
            @click="uploadIPAddresses"
            :loading="uploadingIPAddresses"
            :disabled="!ipAddressFile"
            style="margin-top: 20px; width: 100%"
            icon="Upload"
          >
            {{ uploadingIPAddresses ? 'Uploading & Processing...' : 'Upload IP Addresses CSV' }}
          </el-button>
          
          <div v-if="ipAddressUploadResult" class="upload-result" :class="ipAddressUploadResult.status">
            <el-alert
              :title="ipAddressUploadResult.message"
              :type="ipAddressUploadResult.status === 'success' ? 'success' : 'error'"
              :closable="false"
              style="margin-top: 20px"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Instructions -->
    <el-card class="instructions-card" style="margin-top: 20px">
      <template #header>
        <span>ℹ️ Instructions</span>
      </template>
      <div class="instructions-content">
        <h3>File Requirements:</h3>
        <ul>
          <li><strong>Subnet CSV:</strong> Must contain columns: Network, Mask_Bits, VRF_Group, Notes, Name, Description</li>
          <li><strong>IP Address CSV:</strong> Must contain columns: IP_Address, Label, Subnet, Available, Notes, etc.</li>
          <li>Only IP addresses with non-empty Label values will be imported</li>
          <li>Files are processed immediately upon upload</li>
        </ul>
        <h3>Notes:</h3>
        <ul>
          <li>Device42 data is no longer loaded automatically on system startup</li>
          <li>Upload files through this interface to import Device42 data</li>
          <li>Duplicate entries will be handled automatically (updated if they exist)</li>
        </ul>
      </div>
    </el-card>
  </div>
</template>

<script>
import { UploadFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { device42API } from '../api'

export default {
  name: 'Device42Upload',
  components: {
    UploadFilled
  },
  data() {
    return {
      subnetFile: null,
      subnetFileList: [],
      uploadingSubnets: false,
      subnetUploadResult: null,
      subnetUploadProgress: 0,
      
      ipAddressFile: null,
      ipAddressFileList: [],
      uploadingIPAddresses: false,
      ipAddressUploadResult: null,
      ipAddressUploadProgress: 0
    }
  },
  computed: {
    subnetFileSize() {
      if (!this.subnetFile) return ''
      const size = this.subnetFile.size
      if (size < 1024) return size + ' B'
      if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB'
      return (size / (1024 * 1024)).toFixed(2) + ' MB'
    },
    ipAddressFileSize() {
      if (!this.ipAddressFile) return ''
      const size = this.ipAddressFile.size
      if (size < 1024) return size + ' B'
      if (size < 1024 * 1024) return (size / 1024).toFixed(2) + ' KB'
      return (size / (1024 * 1024)).toFixed(2) + ' MB'
    }
  },
  methods: {
    handleSubnetFileChange(file, fileList) {
      this.subnetFile = file.raw
      this.subnetFileList = fileList
      this.subnetUploadResult = null
    },
    
    handleIPAddressFileChange(file, fileList) {
      this.ipAddressFile = file.raw
      this.ipAddressFileList = fileList
      this.ipAddressUploadResult = null
    },
    
    async uploadSubnets() {
      if (!this.subnetFile) {
        ElMessage.warning('Please select a CSV file first')
        return
      }
      
      this.uploadingSubnets = true
      this.subnetUploadResult = null
      this.subnetUploadProgress = 0
      
      try {
        const formData = new FormData()
        formData.append('file', this.subnetFile)
        
        // Show progress during upload (note: this only tracks upload, not processing)
        const onUploadProgress = (progressEvent) => {
          if (progressEvent.total) {
            // Upload progress (0-50%), processing happens after upload (50-100%)
            this.subnetUploadProgress = Math.min(50, Math.round((progressEvent.loaded * 50) / progressEvent.total))
          }
        }
        
        // Start a timer to simulate processing progress after upload completes
        const progressTimer = setInterval(() => {
          if (this.subnetUploadProgress < 90) {
            this.subnetUploadProgress += 2
          }
        }, 1000)
        
        const response = await device42API.uploadSubnets(formData, onUploadProgress)
        
        clearInterval(progressTimer)
        this.subnetUploadProgress = 100
        
        this.subnetUploadResult = {
          status: 'success',
          message: response.data.message || 'Subnets uploaded successfully!'
        }
        
        ElMessage.success('Device42 subnets uploaded and processed successfully!')
        
        // Clear file selection
        this.subnetFile = null
        this.subnetFileList = []
        this.$refs.subnetUploadRef.clearFiles()
        
        // Reset progress after 3 seconds
        setTimeout(() => {
          this.subnetUploadProgress = 0
        }, 3000)
        
      } catch (error) {
        const errorMsg = error.response?.data?.detail || error.message || 'Failed to upload subnets'
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          this.subnetUploadResult = {
            status: 'error',
            message: 'Upload timeout - file may be too large or processing is taking too long. Please try again or contact support.'
          }
        } else {
          this.subnetUploadResult = {
            status: 'error',
            message: errorMsg
          }
        }
        ElMessage.error('Failed to upload subnets: ' + errorMsg)
        this.subnetUploadProgress = 0
      } finally {
        this.uploadingSubnets = false
      }
    },
    
    async uploadIPAddresses() {
      if (!this.ipAddressFile) {
        ElMessage.warning('Please select a CSV file first')
        return
      }
      
      this.uploadingIPAddresses = true
      this.ipAddressUploadResult = null
      this.ipAddressUploadProgress = 0
      
      try {
        const formData = new FormData()
        formData.append('file', this.ipAddressFile)
        
        // Show progress during upload (note: this only tracks upload, not processing)
        const onUploadProgress = (progressEvent) => {
          if (progressEvent.total) {
            // Upload progress (0-50%), processing happens after upload (50-100%)
            this.ipAddressUploadProgress = Math.min(50, Math.round((progressEvent.loaded * 50) / progressEvent.total))
          }
        }
        
        // Start a timer to simulate processing progress after upload completes
        const progressTimer = setInterval(() => {
          if (this.ipAddressUploadProgress < 90) {
            this.ipAddressUploadProgress += 2
          }
        }, 1000)
        
        const response = await device42API.uploadIPAddresses(formData, onUploadProgress)
        
        clearInterval(progressTimer)
        this.ipAddressUploadProgress = 100
        
        this.ipAddressUploadResult = {
          status: 'success',
          message: response.data.message || 'IP addresses uploaded successfully!'
        }
        
        ElMessage.success('Device42 IP addresses uploaded and processed successfully!')
        
        // Clear file selection
        this.ipAddressFile = null
        this.ipAddressFileList = []
        this.$refs.ipAddressUploadRef.clearFiles()
        
        // Reset progress after 3 seconds
        setTimeout(() => {
          this.ipAddressUploadProgress = 0
        }, 3000)
        
      } catch (error) {
        const errorMsg = error.response?.data?.detail || error.message || 'Failed to upload IP addresses'
        if (error.code === 'ECONNABORTED' || error.message.includes('timeout')) {
          this.ipAddressUploadResult = {
            status: 'error',
            message: 'Upload timeout - file may be too large or processing is taking too long. Please try again or contact support.'
          }
        } else {
          this.ipAddressUploadResult = {
            status: 'error',
            message: errorMsg
          }
        }
        ElMessage.error('Failed to upload IP addresses: ' + errorMsg)
        this.ipAddressUploadProgress = 0
      } finally {
        this.uploadingIPAddresses = false
      }
    }
  }
}
</script>

<style scoped>
.device42-upload-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 10px 0;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #606266;
}

.upload-section {
  margin-bottom: 20px;
}

.upload-result {
  margin-top: 20px;
}

.instructions-card {
  margin-top: 20px;
}

.instructions-content h3 {
  margin-top: 0;
  color: #303133;
}

.instructions-content ul {
  margin: 10px 0;
  padding-left: 20px;
}

.instructions-content li {
  margin-bottom: 8px;
  color: #606266;
}
</style>

