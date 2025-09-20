<template>
  <div class="backup-restore-container">
    <el-card class="page-header">
      <h1>🔄 Backup & Restore System</h1>
      <p>Manage internal system backups with timeline restore functionality</p>
    </el-card>

    <!-- Action Buttons -->
    <el-row :gutter="20" class="action-section">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>📦 Create Backup</span>
          </template>
          <el-form @submit.prevent="createBackup">
            <el-form-item label="Description">
              <el-input
                v-model="newBackupDescription"
                placeholder="Optional backup description..."
                maxlength="200"
                show-word-limit
              />
            </el-form-item>
            <el-form-item>
              <el-button 
                type="primary" 
                @click="createBackup"
                :loading="creating"
                icon="Plus"
              >
                Create Backup
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>📊 Backup Statistics</span>
          </template>
          <div class="stats">
            <div class="stat-item">
              <span class="stat-label">Total Backups:</span>
              <span class="stat-value">{{ backups.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Total Size:</span>
              <span class="stat-value">{{ totalSize }} MB</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Latest Backup:</span>
              <span class="stat-value">{{ latestBackup }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Backup Timeline -->
    <el-card class="backup-timeline">
      <template #header>
        <div class="card-header">
          <span>📅 Backup Timeline</span>
          <el-button 
            @click="loadBackups" 
            :loading="loading"
            icon="Refresh"
            size="small"
          >
            Refresh
          </el-button>
        </div>
      </template>

      <div v-if="loading" class="loading-container">
        <el-skeleton :rows="3" animated />
      </div>

      <div v-else-if="backups.length === 0" class="empty-state">
        <el-empty description="No backups found">
          <el-button type="primary" @click="createBackup">Create First Backup</el-button>
        </el-empty>
      </div>

      <div v-else class="backup-list">
        <el-timeline>
          <el-timeline-item
            v-for="backup in backups"
            :key="backup.backup_id"
            :timestamp="formatTimestamp(backup.timestamp)"
            :type="getTimelineType(backup)"
            size="large"
          >
            <el-card class="backup-item" :class="{ 'latest-backup': isLatestBackup(backup) }">
              <div class="backup-header">
                <div class="backup-info">
                  <h3>{{ backup.description }}</h3>
                  <div class="backup-meta">
                    <el-tag size="small" type="info">{{ backup.backup_id }}</el-tag>
                    <el-tag size="small" :type="backup.status === 'completed' ? 'success' : 'warning'">
                      {{ backup.status }}
                    </el-tag>
                    <el-tag size="small" v-if="backup.restore_tested" type="success">
                      Restore Tested
                    </el-tag>
                  </div>
                </div>
                <div class="backup-actions">
                  <el-button-group>
                    <el-button 
                      size="small" 
                      @click="showBackupDetails(backup)"
                      icon="View"
                    >
                      Details
                    </el-button>
                    <el-button 
                      size="small" 
                      type="success"
                      @click="confirmRestore(backup)"
                      icon="RefreshRight"
                      :disabled="restoring"
                    >
                      Restore
                    </el-button>
                    <el-button 
                      size="small" 
                      type="danger"
                      @click="confirmDelete(backup)"
                      icon="Delete"
                      :disabled="backup.backup_id === restoringBackupId"
                    >
                      Delete
                    </el-button>
                  </el-button-group>
                </div>
              </div>
              
              <div class="backup-details">
                <div class="detail-item">
                  <span class="label">Size:</span>
                  <span class="value">{{ formatSize(backup.size) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Age:</span>
                  <span class="value">{{ backup.age_days }} days</span>
                </div>
                <div class="detail-item">
                  <span class="label">Type:</span>
                  <span class="value">{{ backup.backup_type || 'full' }}</span>
                </div>
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-card>

    <!-- Backup Details Dialog -->
    <el-dialog
      v-model="detailsDialogVisible"
      title="Backup Details"
      width="60%"
    >
      <div v-if="selectedBackup" class="backup-details-dialog">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Backup ID">
            {{ selectedBackup.backup_id }}
          </el-descriptions-item>
          <el-descriptions-item label="Description">
            {{ selectedBackup.description }}
          </el-descriptions-item>
          <el-descriptions-item label="Created">
            {{ formatTimestamp(selectedBackup.timestamp) }}
          </el-descriptions-item>
          <el-descriptions-item label="Status">
            <el-tag :type="selectedBackup.status === 'completed' ? 'success' : 'warning'">
              {{ selectedBackup.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Size">
            {{ formatSize(selectedBackup.size) }}
          </el-descriptions-item>
          <el-descriptions-item label="Age">
            {{ selectedBackup.age_days }} days
          </el-descriptions-item>
          <el-descriptions-item label="Restore Tested">
            <el-tag :type="selectedBackup.restore_tested ? 'success' : 'info'">
              {{ selectedBackup.restore_tested ? 'Yes' : 'No' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="Type">
            {{ selectedBackup.backup_type || 'full' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedBackup.files" class="files-section">
          <h4>Backup Files:</h4>
          <el-table :data="Object.entries(selectedBackup.files)" size="small">
            <el-table-column prop="0" label="Data Type" />
            <el-table-column prop="1" label="File Path" />
          </el-table>
        </div>
      </div>
    </el-dialog>

    <!-- Restore Confirmation Dialog -->
    <el-dialog
      v-model="restoreDialogVisible"
      title="Confirm Restore"
      width="50%"
    >
      <div class="restore-warning">
        <el-alert
          title="Warning: This will replace all current data!"
          type="warning"
          :closable="false"
          show-icon
        >
          <p>Restoring from backup will:</p>
          <ul>
            <li>Replace all current VRFs, VPCs, and Prefixes</li>
            <li>Remove any data not present in the backup</li>
            <li>This action cannot be undone</li>
          </ul>
          <p><strong>Consider creating a backup of current state first!</strong></p>
        </el-alert>
        
        <div v-if="backupToRestore" class="restore-info">
          <h4>Restore from:</h4>
          <p><strong>{{ backupToRestore.description }}</strong></p>
          <p>Created: {{ formatTimestamp(backupToRestore.timestamp) }}</p>
          <p>Size: {{ formatSize(backupToRestore.size) }}</p>
        </div>
      </div>
      
      <template #footer>
        <el-button @click="restoreDialogVisible = false">Cancel</el-button>
        <el-button 
          type="danger" 
          @click="performRestore"
          :loading="restoring"
        >
          Restore Now
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { backupAPI } from '@/api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'BackupRestore',
  data() {
    return {
      backups: [],
      loading: false,
      creating: false,
      restoring: false,
      newBackupDescription: '',
      detailsDialogVisible: false,
      restoreDialogVisible: false,
      selectedBackup: null,
      backupToRestore: null,
      restoringBackupId: null
    }
  },
  computed: {
    totalSize() {
      const total = this.backups.reduce((sum, backup) => sum + (backup.size || 0), 0)
      return this.formatSize(total, false)
    },
    latestBackup() {
      if (this.backups.length === 0) return 'None'
      const latest = this.backups[0]
      return this.formatTimestamp(latest.timestamp, true)
    }
  },
  mounted() {
    this.loadBackups()
  },
  methods: {
    async loadBackups() {
      this.loading = true
      try {
        const response = await backupAPI.listBackups()
        this.backups = response.data.backups || []
      } catch (error) {
        ElMessage.error('Failed to load backups: ' + error.message)
      } finally {
        this.loading = false
      }
    },
    
    async createBackup() {
      this.creating = true
      try {
        const response = await backupAPI.createBackup(this.newBackupDescription || undefined)
        ElMessage.success('Backup created successfully!')
        this.newBackupDescription = ''
        await this.loadBackups()
      } catch (error) {
        ElMessage.error('Failed to create backup: ' + error.message)
      } finally {
        this.creating = false
      }
    },
    
    async showBackupDetails(backup) {
      try {
        const response = await backupAPI.getBackupDetails(backup.backup_id)
        this.selectedBackup = response.data.backup_info
        this.detailsDialogVisible = true
      } catch (error) {
        ElMessage.error('Failed to load backup details: ' + error.message)
      }
    },
    
    confirmRestore(backup) {
      this.backupToRestore = backup
      this.restoreDialogVisible = true
    },
    
    async performRestore() {
      if (!this.backupToRestore) return
      
      this.restoring = true
      this.restoringBackupId = this.backupToRestore.backup_id
      
      try {
        const response = await backupAPI.restoreBackup(this.backupToRestore.backup_id)
        ElMessage.success('Restore completed successfully!')
        this.restoreDialogVisible = false
        await this.loadBackups()
      } catch (error) {
        ElMessage.error('Restore failed: ' + error.message)
      } finally {
        this.restoring = false
        this.restoringBackupId = null
      }
    },
    
    async confirmDelete(backup) {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete backup "${backup.description}"? This action cannot be undone.`,
          'Confirm Delete',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning'
          }
        )
        
        await backupAPI.deleteBackup(backup.backup_id)
        ElMessage.success('Backup deleted successfully!')
        await this.loadBackups()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete backup: ' + error.message)
        }
      }
    },
    
    formatTimestamp(timestamp, short = false) {
      const date = new Date(timestamp)
      if (short) {
        return date.toLocaleDateString()
      }
      return date.toLocaleString()
    },
    
    formatSize(bytes, withUnit = true) {
      if (!bytes) return withUnit ? '0 B' : '0'
      
      // Convert bytes to the most appropriate unit
      if (bytes < 1024) {
        // Less than 1 KB, show in bytes
        return withUnit ? `${bytes} B` : bytes.toString()
      } else if (bytes < 1024 * 1024) {
        // Less than 1 MB, show in KB
        const kb = bytes / 1024
        const formatted = kb.toFixed(1)
        return withUnit ? `${formatted} KB` : formatted
      } else {
        // 1 MB or more, show in MB
        const mb = bytes / (1024 * 1024)
        const formatted = mb.toFixed(1)
        return withUnit ? `${formatted} MB` : formatted
      }
    },
    
    getTimelineType(backup) {
      if (backup.status === 'completed') return 'success'
      if (backup.status === 'failed') return 'danger'
      return 'primary'
    },
    
    isLatestBackup(backup) {
      return this.backups.length > 0 && this.backups[0].backup_id === backup.backup_id
    }
  }
}
</script>

<style scoped>
.backup-restore-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 10px 0;
  color: #409EFF;
}

.action-section {
  margin-bottom: 20px;
}

.stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
}

.stat-label {
  font-weight: 500;
  color: #666;
}

.stat-value {
  font-weight: bold;
  color: #409EFF;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.loading-container {
  padding: 20px;
}

.empty-state {
  text-align: center;
  padding: 40px;
}

.backup-list {
  padding: 20px 0;
}

.backup-item {
  margin-bottom: 10px;
}

.backup-item.latest-backup {
  border: 2px solid #67C23A;
}

.backup-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
}

.backup-info h3 {
  margin: 0 0 8px 0;
  color: #303133;
}

.backup-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.backup-details {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.detail-item {
  display: flex;
  gap: 5px;
}

.detail-item .label {
  font-weight: 500;
  color: #666;
}

.detail-item .value {
  color: #303133;
}

.backup-details-dialog {
  padding: 10px 0;
}

.files-section {
  margin-top: 20px;
}

.files-section h4 {
  margin-bottom: 10px;
  color: #303133;
}

.restore-warning {
  margin-bottom: 20px;
}

.restore-warning ul {
  margin: 10px 0;
  padding-left: 20px;
}

.restore-info {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.restore-info h4 {
  margin: 0 0 10px 0;
  color: #303133;
}

.restore-info p {
  margin: 5px 0;
  color: #606266;
}
</style>
