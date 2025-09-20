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
  getPrefixVPCAssociations: (prefixId) => api.get(`/api/prefixes/${prefixId}/vpc-associations`)
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

// Export/Import API (Read-only)
export const exportImportAPI = {
  // List available exports
  listExports: (exportDir = 'exports') => api.get(`/api/exports?export_dir=${exportDir}`),
  
  // Download export file
  downloadExport: (filePath) => {
    // Create a download link for the file
    const link = document.createElement('a')
    link.href = `${API_BASE_URL}/api/download?file=${encodeURIComponent(filePath)}`
    link.download = filePath.split('/').pop()
    link.target = '_blank'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}

export default api
