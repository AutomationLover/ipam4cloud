<template>
  <div class="vrfs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VRF Management</span>
          <el-button 
            type="primary" 
            @click="openCreateDialog"
            :icon="Plus"
          >
            Create VRF
          </el-button>
        </div>
      </template>
      
      <el-table
        :data="vrfs"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column label="VRF ID" width="250">
          <template #default="scope">
            <div class="vrf-id-cell">
              <span>{{ scope.row.vrf_id }}</span>
              <el-tag 
                v-if="isAutoCreatedVRF(scope.row.vrf_id)" 
                size="small" 
                type="info"
                class="auto-created-tag"
              >
                Auto-created
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="Description" min-width="200" />
        <el-table-column label="Default" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.is_default" type="warning">Default</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="Routable" width="100">
          <template #default="scope">
            <el-icon v-if="scope.row.routable_flag" color="green"><Check /></el-icon>
            <el-icon v-else color="red"><Close /></el-icon>
          </template>
        </el-table-column>
        <el-table-column label="Tags" min-width="200">
          <template #default="scope">
            <el-tag
              v-for="(value, key) in scope.row.tags"
              :key="key"
              size="small"
              class="tag-item"
            >
              {{ key }}: {{ value }}
            </el-tag>
            <span v-if="Object.keys(scope.row.tags).length === 0" class="no-tags">No tags</span>
          </template>
        </el-table-column>
        <el-table-column label="Prefix Count" width="120">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewPrefixes(scope.row.vrf_id)"
            >
              {{ getPrefixCount(scope.row.vrf_id) }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="180">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="editVRF(scope.row)"
              :icon="Edit"
              :disabled="isAutoCreatedVRF(scope.row.vrf_id)"
            >
              Edit
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteVRF(scope.row)"
              :icon="Delete"
              :disabled="isAutoCreatedVRF(scope.row.vrf_id) || (scope.row.is_default && vrfs.length === 1)"
            >
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create/Edit VRF Dialog -->
    <el-dialog
      :title="isEditing ? 'Edit VRF' : 'Create VRF'"
      v-model="showDialog"
      width="600px"
      @close="resetForm"
    >
      <el-form
        :model="vrfForm"
        :rules="vrfRules"
        ref="vrfFormRef"
        label-width="120px"
      >
        <el-form-item label="VRF ID" prop="vrf_id">
          <el-input
            v-model="vrfForm.vrf_id"
            placeholder="Enter VRF ID (e.g., default, prod, dev)"
            :disabled="isEditing"
          />
        </el-form-item>
        
        <el-form-item label="Description" prop="description">
          <el-input
            v-model="vrfForm.description"
            placeholder="Enter VRF description"
            type="textarea"
            :rows="2"
          />
        </el-form-item>
        
        <el-form-item label="Routable">
          <el-switch
            v-model="vrfForm.routable_flag"
            active-text="Yes"
            inactive-text="No"
          />
        </el-form-item>
        
        <el-form-item label="Default VRF">
          <el-switch
            v-model="vrfForm.is_default"
            active-text="Yes"
            inactive-text="No"
          />
          <div class="form-help-text">
            Only one VRF can be set as default. Setting this will unset other defaults.
          </div>
        </el-form-item>
        
        <el-form-item label="Tags">
          <div class="tags-editor">
            <div v-for="(tag, index) in vrfForm.tagList" :key="index" class="tag-input-row">
              <el-input
                v-model="tag.key"
                placeholder="Key"
                style="width: 40%"
                @input="updateTags"
              />
              <span class="tag-separator">:</span>
              <el-input
                v-model="tag.value"
                placeholder="Value"
                style="width: 40%"
                @input="updateTags"
              />
              <el-button
                type="danger"
                size="small"
                @click="removeTag(index)"
                :icon="Delete"
                circle
              />
            </div>
            <el-button
              type="primary"
              size="small"
              @click="addTag"
              :icon="Plus"
            >
              Add Tag
            </el-button>
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDialog = false">Cancel</el-button>
          <el-button 
            type="primary" 
            @click="saveVRF"
            :loading="saving"
          >
            {{ isEditing ? 'Update' : 'Create' }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { Check, Close, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { vrfAPI, prefixAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'VRFs',
  components: {
    Check,
    Close,
    Plus,
    Edit,
    Delete
  },
  data() {
    return {
      loading: false,
      saving: false,
      vrfs: [],
      prefixCounts: {},
      showDialog: false,
      isEditing: false,
      vrfForm: {
        vrf_id: '',
        description: '',
        routable_flag: true,
        is_default: false,
        tags: {},
        tagList: []
      },
      vrfRules: {
        vrf_id: [
          { required: true, message: 'VRF ID is required', trigger: 'blur' },
          { min: 1, max: 50, message: 'VRF ID must be 1-50 characters', trigger: 'blur' },
          { pattern: /^[a-zA-Z0-9_-]+$/, message: 'VRF ID can only contain letters, numbers, underscores, and hyphens', trigger: 'blur' }
        ]
      }
    }
  },
  async mounted() {
    await this.loadVRFs()
    await this.loadPrefixCounts()
  },
  methods: {
    async loadVRFs() {
      this.loading = true
      try {
        const response = await vrfAPI.getVRFs()
        this.vrfs = response.data
      } catch (error) {
        ElMessage.error('Failed to load VRFs')
        console.error(error)
      } finally {
        this.loading = false
      }
    },
    
    async loadPrefixCounts() {
      try {
        const response = await prefixAPI.getPrefixes()
        const prefixes = response.data
        
        // Count prefixes per VRF
        this.prefixCounts = {}
        prefixes.forEach(prefix => {
          if (!this.prefixCounts[prefix.vrf_id]) {
            this.prefixCounts[prefix.vrf_id] = 0
          }
          this.prefixCounts[prefix.vrf_id]++
        })
      } catch (error) {
        console.error('Failed to load prefix counts:', error)
      }
    },
    
    getPrefixCount(vrfId) {
      return this.prefixCounts[vrfId] || 0
    },
    
    viewPrefixes(vrfId) {
      this.$router.push({
        path: '/prefixes',
        query: { vrf_id: vrfId }
      })
    },

    openCreateDialog() {
      this.isEditing = false
      this.resetForm()
      this.showDialog = true
    },

    editVRF(vrf) {
      this.isEditing = true
      this.vrfForm = {
        vrf_id: vrf.vrf_id,
        description: vrf.description || '',
        routable_flag: vrf.routable_flag,
        is_default: vrf.is_default,
        tags: { ...vrf.tags },
        tagList: this.tagsToList(vrf.tags)
      }
      this.showDialog = true
    },

    async deleteVRF(vrf) {
      // Check if VRF has prefixes
      const prefixCount = this.getPrefixCount(vrf.vrf_id)
      if (prefixCount > 0) {
        ElMessage.error(`Cannot delete VRF '${vrf.vrf_id}' - it is being used by ${prefixCount} prefix(es)`)
        return
      }

      // Confirm deletion
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete VRF '${vrf.vrf_id}'?`,
          'Confirm Deletion',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning'
          }
        )

        await vrfAPI.deleteVRF(vrf.vrf_id)
        ElMessage.success(`VRF '${vrf.vrf_id}' deleted successfully`)
        await this.loadVRFs()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error(error.response?.data?.detail || 'Failed to delete VRF')
          console.error(error)
        }
      }
    },

    async saveVRF() {
      try {
        await this.$refs.vrfFormRef.validate()
        this.saving = true

        const vrfData = {
          vrf_id: this.vrfForm.vrf_id,
          description: this.vrfForm.description || null,
          routable_flag: this.vrfForm.routable_flag,
          is_default: this.vrfForm.is_default,
          tags: this.vrfForm.tags
        }

        if (this.isEditing) {
          await vrfAPI.updateVRF(this.vrfForm.vrf_id, {
            description: vrfData.description,
            routable_flag: vrfData.routable_flag,
            is_default: vrfData.is_default,
            tags: vrfData.tags
          })
          ElMessage.success('VRF updated successfully')
        } else {
          await vrfAPI.createVRF(vrfData)
          ElMessage.success('VRF created successfully')
        }

        this.showDialog = false
        await this.loadVRFs()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || `Failed to ${this.isEditing ? 'update' : 'create'} VRF`)
        console.error(error)
      } finally {
        this.saving = false
      }
    },

    resetForm() {
      this.vrfForm = {
        vrf_id: '',
        description: '',
        routable_flag: true,
        is_default: false,
        tags: {},
        tagList: []
      }
      this.$nextTick(() => {
        this.$refs.vrfFormRef?.clearValidate()
      })
    },

    tagsToList(tags) {
      return Object.entries(tags || {}).map(([key, value]) => ({ key, value }))
    },

    updateTags() {
      this.vrfForm.tags = {}
      this.vrfForm.tagList.forEach(tag => {
        if (tag.key && tag.value) {
          this.vrfForm.tags[tag.key] = tag.value
        }
      })
    },

    addTag() {
      this.vrfForm.tagList.push({ key: '', value: '' })
    },

    removeTag(index) {
      this.vrfForm.tagList.splice(index, 1)
      this.updateTags()
    },

    isAutoCreatedVRF(vrfId) {
      // Auto-created VRFs have the format "vrf:uuid" (legacy) or "provider_account_vpcid" (new)
      if (vrfId.startsWith('vrf:')) {
        return true
      }
      
      // Check for new format: provider_account_vpcid (e.g., aws_123456789_vpc-abc123)
      const providerPattern = /^(aws|azure|gcp|other)_[^_]+_[^_]+$/
      return providerPattern.test(vrfId)
    }
  }
}
</script>

<style scoped>
.vrfs {
  max-width: 1200px;
  margin: 0 auto;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tag-item {
  margin-right: 5px;
  margin-bottom: 5px;
}

.no-tags {
  color: #909399;
  font-style: italic;
}

.form-help-text {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

.tags-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  padding: 10px;
  background-color: #fafafa;
}

.tag-input-row {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
}

.tag-separator {
  color: #909399;
  font-weight: bold;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.vrf-id-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auto-created-tag {
  font-size: 10px;
}
</style>
