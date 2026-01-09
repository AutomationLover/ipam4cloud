# HTTP Request Timeout Settings

## Overview

This document describes the HTTP request timeout configuration for the IPAM4Cloud frontend API client and the rationale behind these settings.

## Default Timeout

**30 seconds** - Applied to most API calls by default.

This default aligns with industry best practices and cloud provider limits:
- [AWS API Gateway](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html) synchronous integration timeout: **29 seconds maximum**
- Common industry standard: **10-30 seconds** for standard REST API operations
- [Axios documentation](https://axios-http.com/docs/req_config): Default is `0` (no timeout), but recommends setting explicit timeouts

## Long-Running Operations

Specific operations override the default with longer timeouts:

### Backup/Restore Operations (5 minutes)
- `backupAPI.createBackup()` - Database export operations
- `backupAPI.restoreBackup()` - Database import operations

**Rationale**: Full database exports/imports can take 30+ seconds with large datasets.

### PC Export/Import Operations
- `pcExportImportAPI.exportToPC()` - **5 minutes** - File I/O operations
- `pcExportImportAPI.importFromPC()` - **5 minutes** - File I/O + database import
- `pcExportImportAPI.scanPCFolder()` - **2 minutes** - Scanning folders with many files

**Rationale**: File system operations and data migrations require extended time for completion.

### Large Prefix Queries (2 minutes)
- `prefixAPI.getPrefixes()` - Complex queries with filters
- `prefixAPI.getPrefixesTree()` - Building large tree structures
- `prefixAPI.allocateSubnet()` - Searching through many prefixes
- `prefixAPI.getAvailableSubnets()` - Calculating available subnets (IPv6 can have millions)

**Rationale**: Complex database queries and calculations can take significant time with large datasets.

### File Uploads (10 minutes)
- `device42API.uploadSubnets()` - CSV file upload and processing
- `device42API.uploadIPAddresses()` - CSV file upload and processing

**Rationale**: Large CSV files (8MB+) require extended time for upload and server-side processing.

## Implementation

Timeouts are configured in `containers/frontend/src/api/index.js`:

```javascript
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds default
  // ...
})
```

Individual operations override the default:

```javascript
getPrefixes: (params = {}) => api.get('/api/prefixes', { 
  params,
  timeout: 120000 // 2 minutes override
})
```

## References

- [AWS API Gateway Execution Service Limits](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-execution-service-limits-table.html)
- [AWS API Gateway Quotas](https://docs.aws.amazon.com/apigateway/latest/developerguide/limits.html)
- [Axios Request Config Documentation](https://axios-http.com/docs/req_config)

