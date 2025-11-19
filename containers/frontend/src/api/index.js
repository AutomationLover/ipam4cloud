import axios from 'axios'

const API_BASE_URL = process.env.VUE_APP_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
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
  getPrefixes: (params = {}) => api.get('/api/prefixes', { params }),
  
  // Get prefixes in tree structure
  getPrefixesTree: (vrfId = null) => {
    const params = vrfId ? { vrf_id: vrfId } : {}
    return api.get('/api/prefixes/tree', { params })
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
  allocateSubnet: (data) => api.post('/api/prefixes/allocate-subnet', data),
  
  // Get available subnets in a parent prefix
  getAvailableSubnets: (prefixId, subnetSize) => api.get(`/api/prefixes/${prefixId}/available-subnets`, {
    params: { subnet_size: subnetSize }
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
  createBackup: (description) => api.post('/api/backup', null, { params: { description } }),
  
  // List all backups
  listBackups: () => api.get('/api/backups'),
  
  // Restore from backup
  restoreBackup: (backupId) => api.post(`/api/restore/${backupId}`),
  
  // Delete backup
  deleteBackup: (backupId) => api.delete(`/api/backup/${backupId}`),
  
  // Get backup details
  getBackupDetails: (backupId) => api.get(`/api/backup/${backupId}`)
}

// PC Export/Import API (User's PC folders)
export const pcExportImportAPI = {
  // Export to PC folder
  exportToPC: (pcFolder, exportName) => api.post('/api/pc-export', null, { 
    params: { pc_folder: pcFolder, export_name: exportName } 
  }),
  
  // Import from PC folder
  importFromPC: (pcFolder) => api.post('/api/pc-import', null, { 
    params: { pc_folder: pcFolder } 
  }),
  
  // Scan PC folder for exports
  scanPCFolder: (pcFolder) => api.get('/api/pc-scan', { 
    params: { pc_folder: pcFolder } 
  }),
  
  // Validate PC folder export
  validatePCFolder: (pcFolder) => api.get('/api/pc-validate', { 
    params: { pc_folder: pcFolder } 
  })
}


export default api
