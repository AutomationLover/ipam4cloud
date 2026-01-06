<template>
  <div class="ip-addresses">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>IP Address Query</span>
          <el-button type="info" @click="copyShareableUrl" :disabled="!currentLabel">
            <el-icon><Link /></el-icon>
            Copy Shareable URL
          </el-button>
        </div>
      </template>
      
      <!-- Search Section -->
      <el-row :gutter="20" class="filters">
        <el-col :span="12">
          <el-autocomplete
            v-model="labelQuery"
            :fetch-suggestions="searchLabels"
            placeholder="Enter label to search (e.g., nat-gateway-prod)"
            clearable
            @select="handleLabelSelect"
            @clear="handleLabelClear"
            style="width: 100%"
            :trigger-on-focus="true"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
            <template #default="{ item }">
              <div class="label-suggestion">
                <span class="label-text">{{ item.value }}</span>
                <span class="label-count" v-if="item.count">({{ item.count }} IPs)</span>
              </div>
            </template>
          </el-autocomplete>
        </el-col>
        <el-col :span="6">
          <el-radio-group v-model="matchMode" @change="handleMatchModeChange" style="margin-right: 10px;">
            <el-radio-button :label="false">Contains</el-radio-button>
            <el-radio-button :label="true">Exact</el-radio-button>
          </el-radio-group>
          <el-button type="primary" @click="searchIPAddresses" :loading="loading">
            <el-icon><Search /></el-icon>
            Search
          </el-button>
        </el-col>
        <el-col :span="6">
          <el-button @click="clearSearch" v-if="currentLabel">
            Clear
          </el-button>
        </el-col>
      </el-row>
      
      <!-- Match Mode Info -->
      <el-alert
        v-if="currentLabel"
        :title="matchMode ? 'Exact Match Mode' : 'Partial Match Mode (Contains)'"
        :description="matchMode ? `Showing only IP addresses with label exactly matching: ${currentLabel}` : `Showing IP addresses with labels containing: ${currentLabel}`"
        type="info"
        :closable="false"
        style="margin-top: 10px; margin-bottom: 10px;"
      />
      
      <!-- Results Section -->
      <el-divider v-if="ipAddresses.length > 0 || loading" />
      
      <div v-if="loading" class="loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>Loading IP addresses...</span>
      </div>
      
      <div v-else-if="ipAddresses.length === 0 && currentLabel" class="empty-state">
        <el-empty description="No IP addresses found for this label" />
      </div>
      
      <div v-else-if="ipAddresses.length === 0 && !currentLabel && !loading" class="empty-state">
        <el-empty description="No IP addresses found in database" />
      </div>
      
      <div v-else-if="ipAddresses.length > 0">
        <div class="results-header">
          <h3>
            <span v-if="totalCount > 0">
              {{ currentLabel ? 'Found' : 'Showing' }} {{ totalCount }} total IP address{{ totalCount !== 1 ? 'es' : '' }}
              <span v-if="totalCount > pageSize">
                (showing {{ ipAddresses.length }} on page {{ currentPage }} of {{ Math.ceil(totalCount / pageSize) }})
              </span>
            </span>
            <span v-else>
              {{ ipAddresses.length }} IP address{{ ipAddresses.length !== 1 ? 'es' : '' }}
            </span>
            <span v-if="currentLabel">
              for label: <strong>{{ currentLabel }}</strong>
              <el-tag :type="matchMode ? 'success' : 'info'" size="small" style="margin-left: 8px;">
                {{ matchMode ? 'Exact Match' : 'Contains' }}
              </el-tag>
            </span>
            <span v-else-if="!currentLabel && totalCount > 0">
              (all IP addresses)
            </span>
          </h3>
          <el-button-group>
            <el-button size="small" @click="exportToCSV" :disabled="ipAddresses.length === 0">
              <el-icon><Download /></el-icon>
              Export CSV
            </el-button>
            <el-button size="small" @click="copyShareableUrl" v-if="currentLabel">
              <el-icon><Link /></el-icon>
              Share URL
            </el-button>
          </el-button-group>
        </div>
        
        <el-table
          :data="ipAddresses"
          stripe
          border
          style="width: 100%"
          :default-sort="{ prop: 'ip_address', order: 'ascending' }"
          @sort-change="handleSortChange"
        >
          <el-table-column prop="ip_address" label="IP Address" sortable width="150">
            <template #default="{ row }">
              <el-tag type="primary">{{ row.ip_address }}</el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="label" label="Label" sortable min-width="250">
            <template #default="{ row }">
              <el-tag>{{ row.label }}</el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="subnet" label="Subnet" sortable width="200" />
          
          <el-table-column prop="notes" label="Notes" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.notes" class="notes-cell">
                {{ row.notes }}
                <el-tag v-if="extractTicketId(row.notes)" type="warning" size="small" style="margin-left: 8px;">
                  {{ extractTicketId(row.notes) }}
                </el-tag>
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="available" label="Available" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.available ? 'success' : 'danger'" size="small">
                {{ row.available ? 'Yes' : 'No' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="is_public" label="Public" width="100" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.is_public !== null" :type="row.is_public ? 'warning' : 'info'" size="small">
                {{ row.is_public ? 'Yes' : 'No' }}
              </el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="resource" label="Resource" width="150" show-overflow-tooltip />
          
          <el-table-column prop="cloud_account" label="Cloud Account" width="150" show-overflow-tooltip />
          
          <el-table-column prop="last_updated" label="Last Updated" width="180" sortable>
            <template #default="{ row }">
              <span v-if="row.last_updated">
                {{ formatDate(row.last_updated) }}
              </span>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
        </el-table>
        
        <el-pagination
          v-if="totalCount >= pageSize"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="totalCount"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
          style="margin-top: 20px; justify-content: center;"
        />
      </div>
      
      <!-- This section removed - we now show all IP addresses by default -->
    </el-card>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Loading, Download, Link } from '@element-plus/icons-vue'
import { ipAddressAPI } from '../api'

export default {
  name: 'IPAddresses',
  components: {
    Search,
    Loading,
    Download,
    Link
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    
    const labelQuery = ref('')
    const currentLabel = ref('')
    const matchMode = ref(false) // false = contains (partial), true = exact
    const ipAddresses = ref([])
    const loading = ref(false)
    const labelSuggestions = ref([])
    const currentPage = ref(1)
    const pageSize = ref(100)
    const totalCount = ref(0)
    
      // Check for label and exact parameter in URL query parameter
    onMounted(() => {
      const labelFromUrl = route.query.label
      const exactFromUrl = route.query.exact
      const pageFromUrl = route.query.page
      
      // Parse page parameter if provided
      if (pageFromUrl) {
        const pageNum = parseInt(pageFromUrl, 10)
        if (pageNum > 0) {
          currentPage.value = pageNum
        }
      }
      
      if (labelFromUrl) {
        labelQuery.value = labelFromUrl
        currentLabel.value = labelFromUrl
        
        // Parse exact parameter (can be 'true', 'false', or boolean)
        if (exactFromUrl !== undefined) {
          matchMode.value = exactFromUrl === 'true' || exactFromUrl === true
        }
        
        searchIPAddresses()
      } else {
        // Load all IP addresses if no label is provided
        loadAllIPAddresses()
      }
    })
    
    // Watch for URL changes
    watch(() => route.query.label, (newLabel) => {
      if (newLabel && newLabel !== currentLabel.value) {
        labelQuery.value = newLabel
        currentLabel.value = newLabel
        const exactFromUrl = route.query.exact
        if (exactFromUrl !== undefined) {
          matchMode.value = exactFromUrl === 'true' || exactFromUrl === true
        }
        const pageFromUrl = route.query.page
        if (pageFromUrl) {
          const pageNum = parseInt(pageFromUrl, 10)
          if (pageNum > 0) {
            currentPage.value = pageNum
          }
        } else {
          currentPage.value = 1
        }
        searchIPAddresses()
      }
    })
    
    watch(() => route.query.exact, (newExact) => {
      if (newExact !== undefined && route.query.label) {
        matchMode.value = newExact === 'true' || newExact === true
        currentPage.value = 1 // Reset to first page when changing match mode
        searchIPAddresses()
      }
    })
    
    watch(() => route.query.page, (newPage) => {
      if (newPage) {
        const pageNum = parseInt(newPage, 10)
        if (pageNum > 0 && pageNum !== currentPage.value) {
          currentPage.value = pageNum
          if (currentLabel.value) {
            searchIPAddresses()
          } else {
            loadAllIPAddresses()
          }
        }
      }
    })
    
    const handleMatchModeChange = () => {
      if (currentLabel.value) {
        currentPage.value = 1 // Reset to first page when changing match mode
        searchIPAddresses()
      }
    }
    
    const searchLabels = async (queryString, cb) => {
      try {
        const labels = await ipAddressAPI.getLabels(queryString || '')
        const suggestions = labels.map(label => ({
          value: label,
          count: null // Could be enhanced to show count
        }))
        cb(suggestions)
      } catch (error) {
        console.error('Error fetching labels:', error)
        ElMessage.error('Failed to fetch label suggestions')
        cb([])
      }
    }
    
    const handleLabelSelect = (item) => {
      labelQuery.value = item.value
      currentPage.value = 1 // Reset to first page when selecting a label
      searchIPAddresses()
    }
    
    const handleLabelClear = () => {
      currentLabel.value = ''
      labelQuery.value = ''
      matchMode.value = false
      currentPage.value = 1 // Reset to first page when clearing
      loadAllIPAddresses()
    }
    
    const loadAllIPAddresses = async () => {
      loading.value = true
      currentLabel.value = ''
      updateUrl('', false)
      
      try {
        const offset = (currentPage.value - 1) * pageSize.value
        const response = await ipAddressAPI.getIPAddresses(null, null, pageSize.value, false, offset)
        ipAddresses.value = response.data
        
        // Get total count from response header
        // Axios normalizes headers to lowercase
        const totalCountHeader = response.headers['x-total-count']
        if (totalCountHeader) {
          totalCount.value = parseInt(totalCountHeader, 10)
          console.log('Total count from header:', totalCount.value, 'for page', currentPage.value)
        } else {
          console.warn('X-Total-Count header not found. Available headers:', Object.keys(response.headers || {}))
          // Fallback: if we got a full page, assume there are more
          // Otherwise use response data length
          if (response.data.length === pageSize.value) {
            // Likely more pages exist, set a minimum total
            totalCount.value = Math.max(pageSize.value + 1, response.data.length)
          } else {
            totalCount.value = response.data.length
          }
        }
        
        if (ipAddresses.value.length > 0) {
          ElMessage.success(`Loaded ${totalCount.value} total IP address(es), showing ${ipAddresses.value.length} on page ${currentPage.value}`)
        }
      } catch (error) {
        console.error('Error loading IP addresses:', error)
        ElMessage.error('Failed to load IP addresses: ' + (error.response?.data?.detail || error.message))
        ipAddresses.value = []
        totalCount.value = 0
      } finally {
        loading.value = false
      }
    }
    
    const searchIPAddresses = async () => {
      if (!labelQuery.value || !labelQuery.value.trim()) {
        // If no label provided, load all IP addresses
        currentPage.value = 1 // Reset to first page
        loadAllIPAddresses()
        return
      }
      
      loading.value = true
      currentLabel.value = labelQuery.value.trim()
      updateUrl(currentLabel.value, matchMode.value)
      
      try {
        const offset = (currentPage.value - 1) * pageSize.value
        const response = await ipAddressAPI.getIPAddresses(currentLabel.value, null, pageSize.value, matchMode.value, offset)
        ipAddresses.value = response.data
        
        // Get total count from response header
        // Axios normalizes headers to lowercase
        const totalCountHeader = response.headers['x-total-count']
        if (totalCountHeader) {
          totalCount.value = parseInt(totalCountHeader, 10)
          console.log('Total count from header:', totalCount.value, 'for label:', currentLabel.value)
        } else {
          console.warn('X-Total-Count header not found. Available headers:', Object.keys(response.headers || {}))
          // Fallback: if we got a full page, assume there are more
          // Otherwise use response data length
          if (response.data.length === pageSize.value) {
            // Likely more pages exist, set a minimum total
            totalCount.value = Math.max(pageSize.value + 1, response.data.length)
          } else {
            totalCount.value = response.data.length
          }
        }
        
        if (ipAddresses.value.length === 0) {
          ElMessage.info(`No IP addresses found for label: ${currentLabel.value} (${matchMode.value ? 'exact' : 'partial'} match)`)
        } else {
          ElMessage.success(`Found ${totalCount.value} total IP address(es), showing ${ipAddresses.value.length} on page ${currentPage.value} (${matchMode.value ? 'exact' : 'partial'} match)`)
        }
      } catch (error) {
        console.error('Error searching IP addresses:', error)
        ElMessage.error('Failed to search IP addresses: ' + (error.response?.data?.detail || error.message))
        ipAddresses.value = []
        totalCount.value = 0
      } finally {
        loading.value = false
      }
    }
    
    const clearSearch = () => {
      labelQuery.value = ''
      currentLabel.value = ''
      matchMode.value = false
      currentPage.value = 1 // Reset to first page when clearing search
      loadAllIPAddresses()
    }
    
    const updateUrl = (label, exact = false) => {
      const query = {}
      if (label) {
        query.label = label
        query.exact = exact.toString()
      }
      if (currentPage.value > 1) {
        query.page = currentPage.value.toString()
      }
      router.push({ query })
    }
    
    const copyShareableUrl = () => {
      if (!currentLabel.value) {
        ElMessage.warning('No label selected to share')
        return
      }
      
      const url = new URL(window.location.href)
      url.searchParams.set('label', currentLabel.value)
      url.searchParams.set('exact', matchMode.value.toString())
      const shareableUrl = url.toString()
      
      navigator.clipboard.writeText(shareableUrl).then(() => {
        ElMessage.success('Shareable URL copied to clipboard!')
      }).catch(() => {
        ElMessage.error('Failed to copy URL to clipboard')
      })
    }
    
    const exportToCSV = () => {
      if (ipAddresses.value.length === 0) {
        ElMessage.warning('No data to export')
        return
      }
      
      const headers = ['IP Address', 'Label', 'Subnet', 'Notes', 'Available', 'Public', 'Resource', 'Cloud Account', 'Last Updated']
      const rows = ipAddresses.value.map(ip => [
        ip.ip_address,
        ip.label,
        ip.subnet || '',
        ip.notes || '',
        ip.available ? 'Yes' : 'No',
        ip.is_public ? 'Yes' : 'No',
        ip.resource || '',
        ip.cloud_account || '',
        ip.last_updated ? formatDate(ip.last_updated) : ''
      ])
      
      const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      ].join('\n')
      
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
      const link = document.createElement('a')
      const url = URL.createObjectURL(blob)
      link.setAttribute('href', url)
      link.setAttribute('download', `ip_addresses_${currentLabel.value || 'all'}_${new Date().toISOString().split('T')[0]}.csv`)
      link.style.visibility = 'hidden'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      
      ElMessage.success('CSV exported successfully')
    }
    
    const extractTicketId = (notes) => {
      if (!notes) return null
      const match = notes.match(/NET-\d+/i)
      return match ? match[0] : null
    }
    
    const formatDate = (dateString) => {
      if (!dateString) return '-'
      const date = new Date(dateString)
      return date.toLocaleString()
    }
    
    const handleSortChange = ({ prop, order }) => {
      // Client-side sorting
      if (order) {
        ipAddresses.value.sort((a, b) => {
          const aVal = a[prop] || ''
          const bVal = b[prop] || ''
          const comparison = aVal > bVal ? 1 : aVal < bVal ? -1 : 0
          return order === 'ascending' ? comparison : -comparison
        })
      }
    }
    
    const handlePageChange = (page) => {
      currentPage.value = page
      // Fetch data for the new page
      if (currentLabel.value) {
        searchIPAddresses()
      } else {
        loadAllIPAddresses()
      }
      // Scroll to top after page change
      window.scrollTo({ top: 0, behavior: 'smooth' })
    }
    
    const focusSearch = () => {
      // Focus on the search input
      const input = document.querySelector('.el-autocomplete input')
      if (input) input.focus()
    }
    
      return {
        labelQuery,
        currentLabel,
        matchMode,
        ipAddresses,
        loading,
        labelSuggestions,
        currentPage,
        pageSize,
        totalCount,
        searchLabels,
        handleLabelSelect,
        handleLabelClear,
        handleMatchModeChange,
        loadAllIPAddresses,
        searchIPAddresses,
        clearSearch,
        copyShareableUrl,
        exportToCSV,
        extractTicketId,
        formatDate,
        handleSortChange,
        handlePageChange,
        focusSearch
      }
  }
}
</script>

<style scoped>
.ip-addresses {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.filters {
  margin-bottom: 20px;
}

.label-suggestion {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label-text {
  flex: 1;
}

.label-count {
  color: #909399;
  font-size: 12px;
  margin-left: 10px;
}

.loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  gap: 10px;
}

.empty-state {
  padding: 40px;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.results-header h3 {
  margin: 0;
  color: #303133;
}

.results-header h3 strong {
  color: #409eff;
}

.notes-cell {
  display: flex;
  align-items: center;
}

.text-muted {
  color: #909399;
}

.initial-state {
  padding: 60px 20px;
}

.el-table {
  margin-top: 20px;
}

.el-pagination {
  display: flex;
  justify-content: center;
}
</style>

