import axios from 'axios'

// Dynamically determine API URL based on current host
// If VUE_APP_API_URL is set and not empty, use it; otherwise use same host with port 8000
function getApiBaseUrl() {
  const envUrl = process.env.VUE_APP_API_URL
  if (envUrl && envUrl.trim() !== '') {
    return envUrl
  }
  
  // Use current hostname and port 8000 (backend port)
  // This works whether accessing via localhost, IP address, or hostname
  const protocol = window.location.protocol
  const hostname = window.location.hostname
  return `${protocol}//${hostname}:8000`
}

const API_BASE_URL = getApiBaseUrl()

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds default timeout for most API calls (can be overridden per-request)
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const prefixAPI = {
  // Get all prefixes with optional filters
  getPrefixes: (params = {}) => api.get('/api/prefixes', { 
    params,
    timeout: 120000 // 2 minutes for large prefix queries with complex filters
  }),
  
  // Get prefixes in tree structure
  getPrefixesTree: (params = {}) => {
    return api.get('/api/prefixes/tree', { 
      params,
      timeout: 120000 // 2 minutes for building large tree structures
    })
  },
  
  // Get specific prefix by ID
  getPrefix: (prefixId) => api.get(`/api/prefixes/${prefixId}`),
  
  // Create new prefix
  createPrefix: (data) => api.post('/api/prefixes', data),
  
  // Update existing prefix (manual only)
  updatePrefix: (prefixId, data) => api.put(`/api/prefixes/${prefixId}`, data),
  
  // Delete prefix (manual only)
  deletePrefix: (prefixId) => api.delete(`/api/prefixes/${prefixId}`),
  
  // Get children of a prefix
  getPrefixChildren: (prefixId) => api.get(`/api/prefixes/${prefixId}/children`),
  
  // Check if prefix can create child
  canCreateChild: (prefixId) => api.get(`/api/prefixes/${prefixId}/can-create-child`),
  
  // Check if prefix can associate with VPC
  canAssociateVPC: (prefixId) => api.get(`/api/prefixes/${prefixId}/can-associate-vpc`),
  
  // Get VPC associations for a prefix
  getPrefixVPCAssociations: (prefixId) => api.get(`/api/prefixes/${prefixId}/vpc-associations`),
  
  // Subnet allocation (AWS IPAM-style)
  allocateSubnet: (data) => api.post('/api/prefixes/allocate-subnet', data, {
    timeout: 120000 // 2 minutes for searching through many prefixes
  }),
  
  // Get available subnets in a parent prefix
  getAvailableSubnets: (prefixId, subnetSize) => api.get(`/api/prefixes/${prefixId}/available-subnets`, {
    params: { subnet_size: subnetSize },
    timeout: 120000 // 2 minutes for calculating available subnets (IPv6 can have millions)
  })
}

export const vrfAPI = {
  // Get all VRFs
  getVRFs: () => api.get('/api/vrfs'),
  
  // Get specific VRF by ID
  getVRF: (vrfId) => api.get(`/api/vrfs/${vrfId}`),
  
  // Create new VRF
  createVRF: (data) => api.post('/api/vrfs', data),
  
  // Update existing VRF
  updateVRF: (vrfId, data) => api.put(`/api/vrfs/${vrfId}`, data),
  
  // Delete VRF
  deleteVRF: (vrfId) => api.delete(`/api/vrfs/${vrfId}`)
}

export const vpcAPI = {
  // Get all VPCs
  getVPCs: () => api.get('/api/vpcs'),
  
  // Get specific VPC by ID
  getVPC: (vpcId) => api.get(`/api/vpcs/${vpcId}`),
  
  // Get VPC associations (prefix associations for this VPC)
  getVPCAssociations: (vpcId) => api.get(`/api/vpcs/${vpcId}/associations`),
  
  // Create new VPC
  createVPC: (data) => api.post('/api/vpcs', data),
  
  // Update existing VPC
  updateVPC: (vpcId, data) => api.put(`/api/vpcs/${vpcId}`, data),
  
  // Delete VPC
  deleteVPC: (vpcId) => api.delete(`/api/vpcs/${vpcId}`),
  
  // Create VPC association
  createVPCAssociation: (data) => api.post('/api/vpc-associations', data),
  
  // Remove VPC association
  removeVPCAssociation: (associationId) => api.delete(`/api/vpc-associations/${associationId}`)
}

export const healthAPI = {
  // Health check
  check: () => api.get('/health')
}

// Backup/Restore API (Internal Docker storage)
export const backupAPI = {
  // Create a new backup
  createBackup: (description) => api.post('/api/backup', null, { 
    params: { description },
    timeout: 300000 // 5 minutes for exporting entire database
  }),
  
  // List all backups
  listBackups: () => api.get('/api/backups'),
  
  // Restore from backup
  restoreBackup: (backupId) => api.post(`/api/restore/${backupId}`, null, {
    timeout: 300000 // 5 minutes for importing entire database
  }),
  
  // Delete backup
  deleteBackup: (backupId) => api.delete(`/api/backup/${backupId}`),
  
  // Get backup details
  getBackupDetails: (backupId) => api.get(`/api/backup/${backupId}`)
}

// PC Export/Import API (User's PC folders)
export const pcExportImportAPI = {
  // Export to PC folder
  exportToPC: (pcFolder, exportName) => api.post('/api/pc-export', null, { 
    params: { pc_folder: pcFolder, export_name: exportName },
    timeout: 300000 // 5 minutes for file I/O operations
  }),
  
  // Import from PC folder
  importFromPC: (pcFolder) => api.post('/api/pc-import', null, { 
    params: { pc_folder: pcFolder },
    timeout: 300000 // 5 minutes for file I/O + database import
  }),
  
  // Scan PC folder for exports
  scanPCFolder: (pcFolder) => api.get('/api/pc-scan', { 
    params: { pc_folder: pcFolder },
    timeout: 120000 // 2 minutes for scanning folders with many files
  }),
  
  // Validate PC folder export
  validatePCFolder: (pcFolder) => api.get('/api/pc-validate', { 
    params: { pc_folder: pcFolder } 
  })
}

// Device42 CSV Upload API
export const device42API = {
  // Upload Device42 subnets CSV
  uploadSubnets: (formData, onUploadProgress) => {
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 600000, // 10 minutes for large file uploads and processing
      onUploadProgress: onUploadProgress || (() => {})
    }
    return api.post('/api/device42/upload-subnets', formData, config)
  },
  
  // Upload Device42 IP addresses CSV
  uploadIPAddresses: (formData, onUploadProgress) => {
    const config = {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      timeout: 600000, // 10 minutes for large file uploads and processing
      onUploadProgress: onUploadProgress || (() => {})
    }
    return api.post('/api/device42/upload-ipaddresses', formData, config)
  }
}

// Device42 IP Address API
export const ipAddressAPI = {
  // Get IP addresses by label (supports exact and partial match)
  // If label is null/empty, returns all IP addresses
  // Supports pagination with offset and limit
  getIPAddresses: (label = null, ipAddress = null, limit = 100, exact = false, offset = 0) => {
    const params = {}
    if (label) params.label = label
    if (ipAddress) params.ip_address = ipAddress
    if (limit) params.limit = limit
    // Always include offset (can be 0 for first page)
    params.offset = offset
    // Only set exact if label is provided
    if (label) params.exact = exact
    return api.get('/api/ip-addresses', { params })
  },
  
  // Get list of all unique labels
  getLabels: (search = null) => {
    const params = {}
    if (search) params.search = search
    return api.get('/api/ip-addresses/labels', { params })
  }
}


export default api
