# Prefix Management Web Application

A complete web-based prefix management system with Vue.js frontend and FastAPI backend, implementing all requirements from the frontend specification.

## 🎯 Features Implemented

### ✅ Prefix View (All Requirements Met)
- **List View**: Sortable table with all prefix information
- **Tree View**: Hierarchical display with expand/collapse functionality
- **Filtering**: VRF, source (manual/VPC), routable status, cloud provider, account ID
- **Search**: Search by prefix, tags, or combined criteria
- **Actions**: Create child prefixes and associate prefixes with VPCs

### ✅ VRF View
- **List all VRFs** with descriptions, tags, and routable flags
- **Prefix counts** per VRF with direct navigation to filtered prefix view
- **Default VRF identification**

### ✅ VPC View  
- **List all VPCs** from different cloud providers (AWS, Azure, GCP)
- **Create new VPCs** with full metadata
- **Subnet counts** per VPC with navigation to VPC subnets
- **Provider-specific styling** and account information

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vue.js        │    │   FastAPI       │    │   PostgreSQL    │
│   Frontend      │◄──►│   Backend       │◄──►│   Database      │
│   (Port 8080)   │    │   (Port 8000)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Frontend (Vue.js 3)
- **Element Plus UI**: Modern, responsive components
- **Vue Router**: Multi-page navigation
- **Axios**: HTTP client for API communication
- **Real-time filtering**: Debounced search with instant results

### Backend (FastAPI)
- **REST API**: Complete CRUD operations
- **Pydantic models**: Request/response validation
- **SQLAlchemy ORM**: Database abstraction
- **CORS enabled**: Cross-origin requests for frontend

### Database (PostgreSQL 15)
- **Complete schema**: All tables, triggers, and constraints
- **Demo data**: Pre-loaded with hierarchical prefix examples
- **CIDR support**: Native IP address handling

## 🚀 Quick Start

### Option 1: One-Command Startup
```bash
cd containers/
./run_web_app.sh
```

### Option 2: Manual Startup
```bash
cd containers/
docker-compose up -d postgres
sleep 10
docker-compose up -d backend frontend
docker-compose run --rm app python main.py  # Load demo data
```

## 📱 Access Points

Once running, access the application at:

- **🌐 Frontend**: http://localhost:8080
- **🔧 Backend API**: http://localhost:8000
- **📚 API Documentation**: http://localhost:8000/docs
- **🗄️ Database**: localhost:5432 (prefix_user/prefix_pass)

## 🎮 Using the Application

### 1. Home Dashboard
- Overview statistics (total prefixes, VRFs, etc.)
- Quick navigation to main features
- System health indicators

### 2. Prefix Management
**List View:**
- Filter by VRF, source, routable status
- Search across prefixes and tags
- Sort by CIDR or other columns
- Create child prefixes with one click
- Associate prefixes with VPCs

**Tree View:**
- Hierarchical visualization
- Expand/collapse nodes
- Visual indicators for routable/non-routable
- Source type badges (Manual/VPC)
- Inline actions for each node

### 3. VRF Management
- View all Virtual Routing and Forwarding instances
- See prefix counts per VRF
- Navigate directly to VRF-filtered prefix view
- Identify default VRF

### 4. VPC Management
- Multi-cloud VPC listing (AWS, Azure, GCP)
- Create new VPCs with metadata
- View subnet counts per VPC
- Provider-specific visual styling

## 🔧 API Endpoints

### Prefixes
- `GET /api/prefixes` - List prefixes with filtering
- `GET /api/prefixes/tree` - Tree structure
- `POST /api/prefixes` - Create new prefix
- `GET /api/prefixes/{id}/children` - Get child prefixes

### VRFs
- `GET /api/vrfs` - List all VRFs

### VPCs
- `GET /api/vpcs` - List all VPCs
- `POST /api/vpcs` - Create new VPC
- `POST /api/vpc-associations` - Associate VPC with prefix

## 📊 Demo Data

The application comes pre-loaded with demo data:

```
VRF: prod-vrf
├── 10.0.0.0/8 (Manual, Routable)
    └── 10.0.0.0/12 (Manual, Routable)
        ├── 10.0.0.0/16 (Manual, Routable) → AWS VPC
        │   ├── 10.0.1.0/24 (VPC, Routable)
        │   ├── 10.0.2.0/24 (VPC, Routable)
        │   └── 10.0.10.0/24 (VPC, Routable)
        └── 10.1.0.0/16 (Manual, Non-routable) → AWS VPC

VRF: vrf:vpc-uuid (Auto-created for non-routable VPC)
├── 10.1.1.0/24 (VPC, Non-routable)
└── 10.1.2.0/24 (VPC, Non-routable)
```

## 🛠️ Development

### File Structure
```
containers/
├── frontend/                 # Vue.js application
│   ├── src/
│   │   ├── views/           # Main pages
│   │   ├── api/             # API client
│   │   └── router/          # Navigation
│   ├── package.json
│   └── Dockerfile
├── backend/                  # FastAPI application
│   ├── main.py              # API endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── app/                      # Shared models
│   └── models.py            # SQLAlchemy models
├── init/                     # Database initialization
│   ├── 01_schema.sql        # Complete schema
│   └── 02_seed_data.sql     # Default VRF
├── docker-compose.yml        # Multi-container setup
└── run_web_app.sh           # Startup script
```

### Adding New Features

1. **Backend**: Add endpoints in `backend/main.py`
2. **Frontend**: Create components in `frontend/src/views/`
3. **Database**: Modify schema in `init/01_schema.sql`
4. **API Client**: Update `frontend/src/api/index.js`

### Debugging

```bash
# View logs
docker-compose logs -f frontend
docker-compose logs -f backend
docker-compose logs -f postgres

# Access containers
docker-compose exec backend bash
docker-compose exec frontend sh
docker-compose exec postgres psql -U prefix_user -d prefix_management
```

## 🧪 Testing Features

### Manual Testing Checklist

**Prefix Management:**
- ✅ List view with sorting and filtering
- ✅ Tree view with expand/collapse
- ✅ Search functionality across prefixes and tags
- ✅ Create child prefixes
- ✅ Associate prefixes with VPCs
- ✅ Filter by VRF, source, routable status

**VRF Management:**
- ✅ List all VRFs with metadata
- ✅ Show prefix counts per VRF
- ✅ Navigate to VRF-filtered prefix view

**VPC Management:**
- ✅ List VPCs from multiple providers
- ✅ Create new VPCs with validation
- ✅ Show subnet counts per VPC
- ✅ Navigate to VPC subnet view

## 🔒 Production Considerations

For production deployment, consider:

1. **Security**: Add authentication/authorization
2. **Environment**: Use environment-specific configurations
3. **SSL/TLS**: Enable HTTPS for frontend and backend
4. **Database**: Use managed PostgreSQL service
5. **Monitoring**: Add logging and health checks
6. **Scaling**: Use container orchestration (Kubernetes)

## 🛑 Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears data)
docker-compose down -v
```

## 🎉 Success!

The Prefix Management Web Application successfully implements all requirements:

- ✅ **Vue.js frontend** with modern UI components
- ✅ **Complete prefix management** with list and tree views
- ✅ **Advanced filtering and search** capabilities
- ✅ **VRF and VPC management** views
- ✅ **Prefix creation and VPC association** features
- ✅ **Containerized deployment** with Docker Compose
- ✅ **Demo data** showcasing all functionality

The application is ready for use and can be extended with additional features as needed!

