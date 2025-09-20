<template>
  <div class="vpcs">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VPC Management</span>
          <el-button type="primary" @click="showCreateDialog = true">
            <el-icon><Plus /></el-icon>
            Create VPC
          </el-button>
        </div>
      </template>
      
      <el-table
        :data="vpcs"
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column label="Provider VPC ID" width="150">
          <template #default="scope">
            <router-link 
              :to="`/vpcs/${scope.row.vpc_id}`"
              class="vpc-link"
            >
              <el-text type="primary">{{ scope.row.provider_vpc_id }}</el-text>
            </router-link>
          </template>
        </el-table-column>
        <el-table-column label="Internal UUID" width="200">
          <template #default="scope">
            <div class="uuid-display">
              <el-text size="small" type="info">{{ scope.row.vpc_id }}</el-text>
              <el-tooltip content="Copy Internal VPC UUID" placement="top">
                <el-button 
                  size="small" 
                  text 
                  @click="copyToClipboard(scope.row.vpc_id)"
                  style="margin-left: 4px; padding: 0;"
                >
                  <el-icon size="12"><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="Provider" width="100">
          <template #default="scope">
            <el-tag :type="getProviderType(scope.row.provider)">
              {{ scope.row.provider.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="provider_account_id" label="Account ID" width="150" />
        <el-table-column prop="region" label="Region" width="120" />
        <el-table-column prop="description" label="Description" min-width="200" />
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
        <el-table-column label="Subnets" width="100">
          <template #default="scope">
            <el-button 
              size="small" 
              type="primary" 
              @click="viewSubnets(scope.row.vpc_id)"
            >
              {{ getSubnetCount(scope.row.vpc_id) }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="Actions" width="160">
          <template #default="scope">
            <el-button 
              size="small" 
              type="warning" 
              @click="editVPC(scope.row)"
            >
              <el-icon><Edit /></el-icon>
              Edit
            </el-button>
            <el-button 
              size="small" 
              type="danger" 
              @click="deleteVPC(scope.row)"
            >
              <el-icon><Delete /></el-icon>
              Delete
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- Create VPC Dialog -->
    <el-dialog v-model="showCreateDialog" title="Create New VPC" width="600px">
      <el-form :model="newVPC" :rules="vpcRules" ref="vpcForm" label-width="140px">
        <el-form-item label="Provider" prop="provider">
          <el-select v-model="newVPC.provider" placeholder="Select Provider">
            <el-option label="AWS" value="aws" />
            <el-option label="Azure" value="azure" />
            <el-option label="GCP" value="gcp" />
            <el-option label="Other" value="other" />
          </el-select>
        </el-form-item>
        <el-form-item label="Provider VPC ID" prop="provider_vpc_id">
          <el-input v-model="newVPC.provider_vpc_id" placeholder="e.g., vpc-0123456789abcdef0" />
        </el-form-item>
        <el-form-item label="Account ID" prop="provider_account_id">
          <el-input v-model="newVPC.provider_account_id" placeholder="e.g., 123456789012" />
        </el-form-item>
        <el-form-item label="Region" prop="region">
          <el-input v-model="newVPC.region" placeholder="e.g., us-east-1" />
        </el-form-item>
        <el-form-item label="Description" prop="description">
          <el-input v-model="newVPC.description" placeholder="VPC description" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input
            v-model="tagsInput"
            type="textarea"
            placeholder="JSON format: {&quot;env&quot;: &quot;prod&quot;, &quot;team&quot;: &quot;ops&quot;}"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">Cancel</el-button>
        <el-button type="primary" @click="createVPC" :loading="creating">Create</el-button>
      </template>
    </el-dialog>

    <!-- Edit VPC Dialog -->
    <el-dialog v-model="showEditDialog" title="Edit VPC" width="600px">
      <el-form :model="editVPCData" :rules="editVpcRules" ref="editVpcForm" label-width="140px">
        <el-form-item label="Provider">
          <el-tag :type="getProviderType(editVPCData.provider)">
            {{ editVPCData.provider ? editVPCData.provider.toUpperCase() : '' }}
          </el-tag>
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">Provider cannot be changed</span>
        </el-form-item>
        <el-form-item label="Provider VPC ID">
          <el-input v-model="editVPCData.provider_vpc_id" disabled />
          <span style="color: #909399; font-size: 12px;">VPC ID cannot be changed</span>
        </el-form-item>
        <el-form-item label="Account ID" prop="provider_account_id">
          <el-input v-model="editVPCData.provider_account_id" placeholder="e.g., 123456789012" />
        </el-form-item>
        <el-form-item label="Region" prop="region">
          <el-input v-model="editVPCData.region" placeholder="e.g., us-east-1" />
        </el-form-item>
        <el-form-item label="Description" prop="description">
          <el-input v-model="editVPCData.description" placeholder="VPC description" />
        </el-form-item>
        <el-form-item label="Tags">
          <el-input
            v-model="editTagsInput"
            type="textarea"
            placeholder="JSON format: {&quot;env&quot;: &quot;prod&quot;, &quot;team&quot;: &quot;ops&quot;}"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">Cancel</el-button>
        <el-button type="primary" @click="updateVPC" :loading="updating">Update</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { Plus, Edit, Delete, CopyDocument } from '@element-plus/icons-vue'
import { vpcAPI, prefixAPI } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'VPCs',
  components: {
    Plus, Edit, Delete, CopyDocument
  },
  data() {
    return {
      loading: false,
      creating: false,
      updating: false,
      vpcs: [],
      subnetCounts: {},
      showCreateDialog: false,
      showEditDialog: false,
      selectedVPC: null,
      newVPC: {
        provider: '',
        provider_vpc_id: '',
        provider_account_id: '',
        region: '',
        description: '',
        tags: {}
      },
      editVPCData: {
        provider: '',
        provider_vpc_id: '',
        provider_account_id: '',
        region: '',
        description: '',
        tags: {}
      },
      tagsInput: '{}',
      editTagsInput: '{}',
      vpcRules: {
        provider: [{ required: true, message: 'Please select a provider', trigger: 'change' }],
        provider_vpc_id: [{ required: true, message: 'Please enter provider VPC ID', trigger: 'blur' }],
        provider_account_id: [{ required: true, message: 'Please enter account ID', trigger: 'blur' }],
        region: [{ required: true, message: 'Please enter region', trigger: 'blur' }],
        description: [{ required: true, message: 'Please enter description', trigger: 'blur' }]
      },
      editVpcRules: {
        provider_account_id: [{ required: true, message: 'Please enter account ID', trigger: 'blur' }],
        region: [{ required: true, message: 'Please enter region', trigger: 'blur' }],
        description: [{ required: true, message: 'Please enter description', trigger: 'blur' }]
      }
    }
  },
  async mounted() {
    await this.loadVPCs()
    await this.loadSubnetCounts()
  },
  methods: {
    async loadVPCs() {
      this.loading = true
      try {
        const response = await vpcAPI.getVPCs()
        this.vpcs = response.data
      } catch (error) {
        ElMessage.error('Failed to load VPCs')
        console.error(error)
      } finally {
        this.loading = false
      }
    },
    
    async loadSubnetCounts() {
      try {
        const response = await prefixAPI.getPrefixes({ source: 'vpc' })
        const vpcPrefixes = response.data
        
        // Count subnets per VPC
        this.subnetCounts = {}
        vpcPrefixes.forEach(prefix => {
          if (prefix.vpc_id) {
            if (!this.subnetCounts[prefix.vpc_id]) {
              this.subnetCounts[prefix.vpc_id] = 0
            }
            this.subnetCounts[prefix.vpc_id]++
          }
        })
      } catch (error) {
        console.error('Failed to load subnet counts:', error)
      }
    },
    
    getProviderType(provider) {
      const types = {
        aws: 'warning',
        azure: 'primary',
        gcp: 'success',
        other: 'info'
      }
      return types[provider] || 'info'
    },
    
    getSubnetCount(vpcId) {
      return this.subnetCounts[vpcId] || 0
    },
    
    viewSubnets(vpcId) {
      this.$router.push({
        path: '/prefixes',
        query: { 
          source: 'vpc',
          search: vpcId
        }
      })
    },
    
    async createVPC() {
      try {
        await this.$refs.vpcForm.validate()
        
        // Parse tags
        try {
          this.newVPC.tags = JSON.parse(this.tagsInput)
        } catch (e) {
          ElMessage.error('Invalid JSON format for tags')
          return
        }
        
        this.creating = true
        await vpcAPI.createVPC(this.newVPC)
        ElMessage.success('VPC created successfully')
        this.showCreateDialog = false
        await this.loadVPCs()
        
        // Reset form
        this.newVPC = {
          provider: '',
          provider_vpc_id: '',
          provider_account_id: '',
          region: '',
          description: '',
          tags: {}
        }
        this.tagsInput = '{}'
      } catch (error) {
        ElMessage.error('Failed to create VPC')
        console.error(error)
      } finally {
        this.creating = false
      }
    },

    editVPC(vpc) {
      this.selectedVPC = vpc
      this.editVPCData = {
        provider: vpc.provider,
        provider_vpc_id: vpc.provider_vpc_id,
        provider_account_id: vpc.provider_account_id,
        region: vpc.region,
        description: vpc.description,
        tags: { ...vpc.tags }
      }
      this.editTagsInput = JSON.stringify(vpc.tags, null, 2)
      this.showEditDialog = true
    },

    async updateVPC() {
      try {
        await this.$refs.editVpcForm.validate()
        
        // Parse tags
        try {
          this.editVPCData.tags = JSON.parse(this.editTagsInput)
        } catch (e) {
          ElMessage.error('Invalid JSON format for tags')
          return
        }
        
        this.updating = true
        
        // Prepare update data (exclude provider and provider_vpc_id as they can't be changed)
        const updateData = {
          provider_account_id: this.editVPCData.provider_account_id,
          region: this.editVPCData.region,
          description: this.editVPCData.description,
          tags: this.editVPCData.tags
        }
        
        await vpcAPI.updateVPC(this.selectedVPC.vpc_id, updateData)
        ElMessage.success('VPC updated successfully')
        this.showEditDialog = false
        await this.loadVPCs()
      } catch (error) {
        ElMessage.error('Failed to update VPC: ' + (error.response?.data?.detail || error.message))
        console.error(error)
      } finally {
        this.updating = false
      }
    },

    async deleteVPC(vpc) {
      try {
        await ElMessageBox.confirm(
          `Are you sure you want to delete VPC "${vpc.provider_vpc_id}"? This action cannot be undone.`,
          'Confirm Delete',
          {
            confirmButtonText: 'Delete',
            cancelButtonText: 'Cancel',
            type: 'warning',
            confirmButtonClass: 'el-button--danger'
          }
        )
        
        await vpcAPI.deleteVPC(vpc.vpc_id)
        ElMessage.success('VPC deleted successfully')
        await this.loadVPCs()
        await this.loadSubnetCounts()
      } catch (error) {
        if (error !== 'cancel') {
          ElMessage.error('Failed to delete VPC: ' + (error.response?.data?.detail || error.message))
          console.error(error)
        }
      }
    },

    async copyToClipboard(text) {
      try {
        await navigator.clipboard.writeText(text)
        ElMessage.success(`Copied to clipboard: ${text}`)
      } catch (error) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea')
        textArea.value = text
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        ElMessage.success(`Copied to clipboard: ${text}`)
      }
    }
  }
}
</script>

<style scoped>
.vpcs {
  max-width: 1400px;
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

.uuid-display {
  display: flex;
  align-items: center;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 11px;
}

.uuid-display .el-text {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Clickable VPC ID styles */
.vpc-link {
  text-decoration: none;
  cursor: pointer;
}

.vpc-link:hover {
  text-decoration: underline;
}
</style>

