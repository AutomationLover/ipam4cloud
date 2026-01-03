#!/usr/bin/env python3
"""
FastAPI Backend for Prefix Management System
Provides REST API endpoints for the Vue.js frontend
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError, OperationalError, IntegrityError
import os
import sys
import uuid
from datetime import datetime

# Add the app directory to Python path to import models
sys.path.append('/app')
from models import DatabaseManager, PrefixManager, VRF, VPC, Prefix, IdempotencyRecord, Device42IPAddress
from data_export_import import DataExporter, DataImporter
from backup_restore import BackupManager
from pc_export_import import PCExportImportManager
from idempotency_service import IdempotencyService, IdempotencyManager
from middleware import setup_middleware

# Pydantic models for API
class PrefixResponse(BaseModel):
    prefix_id: str
    vrf_id: str
    cidr: str
    tags: Dict[str, Any]
    indentation_level: int
    parent_prefix_id: Optional[str]
    source: str
    routable: bool
    vpc_children_type_flag: bool
    vpc_id: Optional[str]
    created_at: datetime
    updated_at: datetime

class PrefixCreate(BaseModel):
    vrf_id: str
    cidr: str
    parent_prefix_id: Optional[str] = None
    tags: Optional[Dict[str, Any]] = {}
    routable: bool = True
    vpc_children_type_flag: bool = False
    request_id: Optional[str] = Field(None, description="Optional request ID for idempotency")

class PrefixUpdate(BaseModel):
    vrf_id: Optional[str] = None
    cidr: Optional[str] = None
    parent_prefix_id: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    routable: Optional[bool] = None
    vpc_children_type_flag: Optional[bool] = None

class VRFResponse(BaseModel):
    vrf_id: str
    description: Optional[str]
    tags: Dict[str, Any]
    routable_flag: bool
    is_default: bool

class VRFCreate(BaseModel):
    vrf_id: str
    description: Optional[str] = None
    tags: Optional[Dict[str, Any]] = {}
    routable_flag: bool = True
    is_default: bool = False
    request_id: Optional[str] = Field(None, description="Optional request ID for idempotency")

class VRFUpdate(BaseModel):
    description: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None
    routable_flag: Optional[bool] = None
    is_default: Optional[bool] = None

class VPCResponse(BaseModel):
    vpc_id: str
    description: Optional[str]
    provider: str
    provider_account_id: Optional[str]
    provider_vpc_id: str
    region: Optional[str]
    tags: Dict[str, Any]

class VPCCreate(BaseModel):
    description: str
    provider: str
    provider_account_id: str
    provider_vpc_id: str
    region: str
    tags: Optional[Dict[str, Any]] = {}
    request_id: Optional[str] = Field(None, description="Optional request ID for idempotency")

class VPCUpdate(BaseModel):
    description: Optional[str] = None
    provider_account_id: Optional[str] = None
    region: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None

class VPCAssociation(BaseModel):
    vpc_id: str
    vpc_prefix_cidr: str
    routable: bool
    parent_prefix_id: str

class SubnetAllocationRequest(BaseModel):
    vrf_id: str
    subnet_size: int = Field(..., ge=1, le=128, description="Subnet mask length (e.g., 24 for /24 IPv4, 64 for /64 IPv6)")
    tags: Optional[Dict[str, Any]] = Field(default={}, description="Tags to match parent prefixes (strict match)")
    routable: Optional[bool] = Field(default=True, description="Whether the allocated subnet should be routable")
    parent_prefix_id: Optional[str] = Field(default=None, description="Optional specific parent prefix ID")
    description: Optional[str] = Field(default=None, description="Description for the allocated subnet")
    vpc_children_type_flag: Optional[bool] = Field(default=False, description="If True, allocated subnet cannot have child CIDRs (final allocated). If False, can have manual child prefixes.")
    request_id: Optional[str] = Field(None, description="Optional request ID for idempotency")

class SubnetAllocationResponse(BaseModel):
    allocated_cidr: str
    parent_prefix_id: str
    prefix_id: str
    available_count: int
    parent_cidr: str
    tags: Dict[str, Any]
    routable: bool
    created_at: datetime

class TreeNode(BaseModel):
    prefix_id: str
    vrf_id: str
    cidr: str
    tags: Dict[str, Any]
    indentation_level: int
    parent_prefix_id: Optional[str]
    source: str
    routable: bool
    vpc_children_type_flag: bool
    vpc_id: Optional[str]
    children: List['TreeNode'] = []

TreeNode.model_rebuild()

# Initialize FastAPI app
app = FastAPI(title="Prefix Management API", version="1.0.0")

# Setup middleware (request ID, logging, error handling, performance monitoring)
setup_middleware(app, {
    'slow_request_threshold_ms': 1000.0,
    'collect_stats': True,
    'log_request_body': False,  # Set to True for debugging
    'log_response_body': False,  # Set to True for debugging
    'exclude_paths': ["/health", "/metrics", "/api/stats"],
    'request_id_header': "X-Request-ID",
    'generate_request_id': True
})

# CORS middleware for Vue.js frontends (admin + readonly portals)
# Allow all origins for flexibility (can be restricted in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins - works with any hostname/IP
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
database_url = os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@postgres:5432/prefix_management')
db_manager = DatabaseManager(database_url)
db_manager.create_tables()

# Initialize managers
prefix_manager = PrefixManager(db_manager)

# Initialize idempotency service
idempotency_service = IdempotencyService(db_manager)
idempotency_manager = IdempotencyManager(idempotency_service)

def get_prefix_manager():
    return prefix_manager

# Context manager for database sessions with HTTP error handling
@contextmanager
def get_db_session_with_http_error_handling(db_manager: DatabaseManager):
    """
    Context manager for database sessions that ensures proper cleanup and handles errors.
    
    Automatically converts database errors to HTTPException:
    - HTTPException: Passes through (handled by FastAPI)
    - IntegrityError: Converts to HTTP 400 (constraint violations)
    - SQLAlchemyError/OperationalError: Converts to HTTP 500 (database errors)
    - Other exceptions: Converts to HTTP 500 (internal server errors)
    """
    session = db_manager.get_session()
    try:
        yield session
    except HTTPException:
        # FastAPI handles HTTPException automatically, just re-raise
        raise
    except IntegrityError as e:
        # Database constraint violations (e.g., unique constraint, foreign key)
        raise HTTPException(status_code=400, detail=f"Database constraint violation: {str(e)}")
    except (SQLAlchemyError, OperationalError) as e:
        # Database connection or query errors
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    except Exception as e:
        # Other unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        session.close()

def is_auto_created_vrf(vrf_id: str) -> bool:
    """Check if a VRF ID represents an auto-created VRF"""
    import re
    
    # Legacy format: vrf:uuid
    if vrf_id.startswith('vrf:'):
        return True
    
    # New format: provider_account_vpcid (e.g., aws_123456789_vpc-abc123)
    provider_pattern = r'^(aws|azure|gcp|other)_[^_]+_[^_]+$'
    return bool(re.match(provider_pattern, vrf_id))

def apply_advanced_search(prefixes, search_query):
    """
    Apply advanced search filtering to prefixes.
    
    Supports:
    - Basic text search: "10.0.1" (searches in CIDR, prefix_id, tag values)
    - Tag-specific search: "AZ:us-east-1a" or "Name:prod-subnet"
    - CIDR pattern: "10.0.1.0/24" (exact match) or "10.0.1" (contains)
    - Multiple terms: "AZ:us-east-1a 10.0.1" (AND logic)
    """
    if not search_query or not search_query.strip():
        return prefixes
    
    import re
    import ipaddress
    
    # Split search query into terms
    terms = search_query.strip().split()
    filtered_prefixes = []
    
    for prefix in prefixes:
        matches_all_terms = True
        
        for term in terms:
            term_lower = term.lower()
            term_matches = False
            
            # Check if term is a tag-specific search (key:value format)
            if ':' in term and not term.startswith('http'):
                tag_key, tag_value = term.split(':', 1)
                tag_key = tag_key.strip().lower()
                tag_value = tag_value.strip().lower()
                
                # Search in tags with key:value matching
                for k, v in prefix.tags.items():
                    if (tag_key in k.lower() and tag_value in str(v).lower()):
                        term_matches = True
                        break
            else:
                # General search in CIDR, prefix_id, and all tag values
                cidr_str = str(prefix.cidr).lower()
                prefix_id_str = prefix.prefix_id.lower()
                
                # Check CIDR match (exact or contains)
                if term_lower in cidr_str:
                    term_matches = True
                # Check prefix ID match
                elif term_lower in prefix_id_str:
                    term_matches = True
                # Check if it's a CIDR pattern match
                else:
                    try:
                        # Try to parse as CIDR and check if prefix CIDR contains or is contained by search CIDR
                        if '/' in term:
                            search_network = ipaddress.ip_network(term, strict=False)
                            prefix_network = ipaddress.ip_network(str(prefix.cidr), strict=False)
                            if (search_network.subnet_of(prefix_network) or 
                                prefix_network.subnet_of(search_network) or
                                search_network == prefix_network):
                                term_matches = True
                    except (ipaddress.AddressValueError, ValueError):
                        pass
                
                # Search in tag values if not matched yet
                if not term_matches:
                    for tag_value in prefix.tags.values():
                        if term_lower in str(tag_value).lower():
                            term_matches = True
                            break
            
            # If this term doesn't match, the prefix doesn't match overall
            if not term_matches:
                matches_all_terms = False
                break
        
        # Add prefix if all terms match
        if matches_all_terms:
            filtered_prefixes.append(prefix)
    
    return filtered_prefixes

# Helper function to convert SQLAlchemy model to dict
def model_to_dict(model):
    if model is None:
        return None
    result = {}
    for column in model.__table__.columns:
        value = getattr(model, column.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        result[column.name] = value
    return result

# Helper function to build tree structure
def build_tree(prefixes: List[Prefix], parent_id: Optional[str] = None) -> List[TreeNode]:
    tree = []
    for prefix in prefixes:
        if prefix.parent_prefix_id == parent_id:
            children = build_tree(prefixes, prefix.prefix_id)
            node = TreeNode(
                prefix_id=prefix.prefix_id,
                vrf_id=prefix.vrf_id,
                cidr=str(prefix.cidr),
                tags=prefix.tags,
                indentation_level=prefix.indentation_level,
                parent_prefix_id=prefix.parent_prefix_id,
                source=prefix.source,
                routable=prefix.routable,
                vpc_children_type_flag=prefix.vpc_children_type_flag,
                vpc_id=str(prefix.vpc_id) if prefix.vpc_id else None,
                children=children
            )
            tree.append(node)
    return tree

@app.get("/")
async def root():
    return {"message": "Prefix Management API", "version": "1.0.0"}

# Prefix endpoints
@app.get("/api/prefixes", response_model=List[PrefixResponse])
async def get_prefixes(
    vrf_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    routable: Optional[bool] = Query(None),
    provider: Optional[str] = Query(None),
    provider_account_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_deleted: bool = Query(False, description="Include prefixes marked as deleted from AWS"),
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get all prefixes with optional filtering"""
    try:
        prefixes = pm.filter_prefixes(
            vrf_id=vrf_id,
            source=source,
            routable=routable,
            provider=provider,
            provider_account_id=provider_account_id
        )
        
        # Apply advanced search filter if provided
        if search:
            prefixes = apply_advanced_search(prefixes, search)
        
        # Filter out deleted prefixes unless explicitly requested
        if not include_deleted:
            prefixes = [p for p in prefixes if not p.tags.get('deleted_from_aws')]
        
        return [PrefixResponse(
            prefix_id=p.prefix_id,
            vrf_id=p.vrf_id,
            cidr=str(p.cidr),
            tags=p.tags,
            indentation_level=p.indentation_level,
            parent_prefix_id=p.parent_prefix_id,
            source=p.source,
            routable=p.routable,
            vpc_children_type_flag=p.vpc_children_type_flag,
            vpc_id=str(p.vpc_id) if p.vpc_id else None,
            created_at=p.created_at,
            updated_at=p.updated_at
        ) for p in prefixes]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prefixes/tree", response_model=List[TreeNode])
async def get_prefixes_tree(
    vrf_id: Optional[str] = Query(None),
    include_deleted: bool = Query(False, description="Include prefixes marked as deleted from AWS"),
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get prefixes in tree structure"""
    try:
        prefixes = pm.get_prefix_tree(vrf_id)
        
        # Filter out deleted prefixes unless explicitly requested
        if not include_deleted:
            prefixes = [p for p in prefixes if not p.tags.get('deleted_from_aws')]
        
        return build_tree(prefixes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prefixes", response_model=PrefixResponse)
async def create_prefix(
    prefix_data: PrefixCreate,
    request: Request,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Create a new manual prefix with idempotency support"""
    try:
        # Get request ID from header or request body
        request_id = prefix_data.request_id or getattr(request.state, 'request_id', None)
        
        # Prepare request parameters for idempotency check
        request_params = {
            'vrf_id': prefix_data.vrf_id,
            'cidr': prefix_data.cidr,
            'parent_prefix_id': prefix_data.parent_prefix_id,
            'tags': prefix_data.tags,
            'routable': prefix_data.routable,
            'vpc_children_type_flag': prefix_data.vpc_children_type_flag
        }
        
        def create_prefix_operation():
            prefix = pm.create_manual_prefix(
                vrf_id=prefix_data.vrf_id,
                cidr=prefix_data.cidr,
                parent_prefix_id=prefix_data.parent_prefix_id,
                tags=prefix_data.tags,
                routable=prefix_data.routable,
                vpc_children_type_flag=prefix_data.vpc_children_type_flag
            )
            return PrefixResponse(
                prefix_id=prefix.prefix_id,
                vrf_id=prefix.vrf_id,
                cidr=str(prefix.cidr),
                tags=prefix.tags,
                indentation_level=prefix.indentation_level,
                parent_prefix_id=prefix.parent_prefix_id,
                source=prefix.source,
                routable=prefix.routable,
                vpc_children_type_flag=prefix.vpc_children_type_flag,
                vpc_id=str(prefix.vpc_id) if prefix.vpc_id else None,
                created_at=prefix.created_at,
                updated_at=prefix.updated_at
            )
        
        # Process with idempotency
        response_data, status_code, actual_request_id = idempotency_manager.process_request(
            request_id=request_id,
            endpoint="/api/prefixes",
            method="POST",
            request_params=request_params,
            processor_func=create_prefix_operation
        )
        
        # Add request ID to response headers
        if actual_request_id:
            request.state.response_request_id = actual_request_id
        
        return response_data
        
    except ValueError as e:
        # Handle validation errors with clear messages
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/prefixes/{prefix_id}", response_model=PrefixResponse)
async def get_prefix(
    prefix_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get a specific prefix by ID"""
    try:
        prefix = pm.get_prefix_by_id(prefix_id)
        if not prefix:
            raise HTTPException(status_code=404, detail="Prefix not found")
        
        return PrefixResponse(
            prefix_id=prefix.prefix_id,
            vrf_id=prefix.vrf_id,
            cidr=str(prefix.cidr),
            tags=prefix.tags,
            indentation_level=prefix.indentation_level,
            parent_prefix_id=prefix.parent_prefix_id,
            source=prefix.source,
            routable=prefix.routable,
            vpc_children_type_flag=prefix.vpc_children_type_flag,
            vpc_id=str(prefix.vpc_id) if prefix.vpc_id else None,
            created_at=prefix.created_at,
            updated_at=prefix.updated_at
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/prefixes/{prefix_id}", response_model=PrefixResponse)
async def update_prefix(
    prefix_id: str,
    prefix_data: PrefixUpdate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Update a manual prefix (VPC-sourced prefixes cannot be updated)"""
    try:
        # Convert Pydantic model to dict, excluding None values
        update_data = {k: v for k, v in prefix_data.dict().items() if v is not None}
        
        prefix = pm.update_manual_prefix(prefix_id, **update_data)
        
        return PrefixResponse(
            prefix_id=prefix.prefix_id,
            vrf_id=prefix.vrf_id,
            cidr=str(prefix.cidr),
            tags=prefix.tags,
            indentation_level=prefix.indentation_level,
            parent_prefix_id=prefix.parent_prefix_id,
            source=prefix.source,
            routable=prefix.routable,
            vpc_children_type_flag=prefix.vpc_children_type_flag,
            vpc_id=str(prefix.vpc_id) if prefix.vpc_id else None,
            created_at=prefix.created_at,
            updated_at=prefix.updated_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/prefixes/{prefix_id}")
async def delete_prefix(
    prefix_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Delete a manual prefix (VPC-sourced prefixes cannot be deleted)"""
    try:
        success = pm.delete_manual_prefix(prefix_id)
        if success:
            return {"message": "Prefix deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete prefix")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prefixes/allocate-subnet", response_model=SubnetAllocationResponse)
async def allocate_subnet(
    allocation_request: SubnetAllocationRequest,
    request: Request,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """
    Allocate the first available subnet of specified size from matching parent prefixes.
    
    This endpoint implements AWS IPAM-style subnet allocation where users specify:
    - VRF and subnet size (e.g., /24)
    - Optional tags to match parent prefixes (strict match)
    - Optional specific parent prefix ID
    
    The system will find the first available subnet that doesn't overlap with existing allocations.
    
    This endpoint supports idempotency - if the same request_id is used with identical parameters,
    the same allocated subnet will be returned instead of allocating a new one.
    """
    try:
        # Get request ID from header or request body
        request_id = allocation_request.request_id or getattr(request.state, 'request_id', None)
        
        # Prepare request parameters for idempotency check
        request_params = {
            'vrf_id': allocation_request.vrf_id,
            'subnet_size': allocation_request.subnet_size,
            'tags': allocation_request.tags,
            'routable': allocation_request.routable,
            'parent_prefix_id': allocation_request.parent_prefix_id,
            'description': allocation_request.description,
            'vpc_children_type_flag': allocation_request.vpc_children_type_flag
        }
        
        def allocate_subnet_operation():
            result = pm.allocate_subnet(
                vrf_id=allocation_request.vrf_id,
                subnet_size=allocation_request.subnet_size,
                tags=allocation_request.tags,
                routable=allocation_request.routable,
                parent_prefix_id=allocation_request.parent_prefix_id,
                description=allocation_request.description,
                vpc_children_type_flag=allocation_request.vpc_children_type_flag
            )
            
            return SubnetAllocationResponse(
                allocated_cidr=result['allocated_cidr'],
                parent_prefix_id=result['parent_prefix_id'],
                prefix_id=result['prefix_id'],
                available_count=result['available_count'],
                parent_cidr=result['parent_cidr'],
                tags=result['tags'],
                routable=result['routable'],
                created_at=result['created_at']
            )
        
        # Process with idempotency
        response_data, status_code, actual_request_id = idempotency_manager.process_request(
            request_id=request_id,
            endpoint="/api/prefixes/allocate-subnet",
            method="POST",
            request_params=request_params,
            processor_func=allocate_subnet_operation
        )
        
        # Add request ID to response headers
        if actual_request_id:
            request.state.response_request_id = actual_request_id
        
        return response_data
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Subnet allocation failed: {str(e)}")

@app.get("/api/prefixes/{prefix_id}/available-subnets")
async def get_available_subnets(
    prefix_id: str,
    subnet_size: int = Query(..., ge=1, le=128, description="Subnet mask length (e.g., 24 for /24 IPv4, 64 for /64 IPv6)"),
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """
    Get all available subnets of specified size within a parent prefix.
    
    This endpoint helps users preview what subnets are available before allocation.
    Supports both IPv4 (1-32) and IPv6 (1-128) subnet sizes.
    """
    try:
        import ipaddress
        prefix = pm.get_prefix_by_id(prefix_id)
        if not prefix:
            raise HTTPException(status_code=404, detail="Prefix not found")
        
        if prefix.source != 'manual':
            raise HTTPException(status_code=400, detail="Can only allocate subnets from manual prefixes")
        
        available_subnets = pm.calculate_available_subnets(prefix, subnet_size)
        
        # Detect IP version for total_possible calculation
        parent_network = ipaddress.ip_network(str(prefix.cidr), strict=False)
        parent_mask = parent_network.prefixlen
        address_bits = parent_network.max_prefixlen  # 32 for IPv4, 128 for IPv6
        total_possible = 2 ** (subnet_size - parent_mask) if subnet_size >= parent_mask else 0
        
        return {
            "parent_prefix_id": prefix_id,
            "parent_cidr": str(prefix.cidr),
            "subnet_size": subnet_size,
            "available_subnets": available_subnets,
            "available_count": len(available_subnets),
            "total_possible": total_possible,
            "ip_version": parent_network.version  # 4 or 6
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prefixes/{prefix_id}/children", response_model=List[PrefixResponse])
async def get_prefix_children(
    prefix_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get children of a specific prefix"""
    try:
        children = pm.get_children_prefixes(prefix_id)
        return [PrefixResponse(
            prefix_id=p.prefix_id,
            vrf_id=p.vrf_id,
            cidr=str(p.cidr),
            tags=p.tags,
            indentation_level=p.indentation_level,
            parent_prefix_id=p.parent_prefix_id,
            source=p.source,
            routable=p.routable,
            vpc_children_type_flag=p.vpc_children_type_flag,
            vpc_id=str(p.vpc_id) if p.vpc_id else None,
            created_at=p.created_at,
            updated_at=p.updated_at
        ) for p in children]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prefixes/{prefix_id}/can-create-child")
async def can_create_child_prefix(
    prefix_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """
    Check if a child prefix can be created under this prefix.
    
    Rules:
    1. VPC-sourced prefixes cannot have child prefixes
    2. Manual prefixes with vpc_children_type_flag=True cannot have manual child prefixes (children are VPC subnets only)
    3. Manual prefixes with vpc_children_type_flag=False can have manual child prefixes (can be subdivided)
       This applies to all manual prefixes regardless of VPC association, allowing public IP blocks 
       (e.g., /26 in public-vrf) to be subdivided into smaller allocations (e.g., /28) for VPCs or projects.
    """
    try:
        prefix = pm.get_prefix_by_id(prefix_id)
        if not prefix:
            raise HTTPException(status_code=404, detail="Prefix not found")
        
        # Rule 1: VPC-sourced prefixes cannot have child prefixes
        if prefix.source == 'vpc':
            return {"can_create_child": False, "reason": "VPC-sourced prefixes cannot have child prefixes"}
        
        # Rule 2: Check vpc_children_type_flag
        # If True, this prefix's children are VPC subnets only (final allocated), cannot have manual child prefixes
        if prefix.vpc_children_type_flag:
            return {
                "can_create_child": False, 
                "reason": "Prefix has vpc_children_type_flag=True, meaning its children are VPC subnets only. Cannot create manual child prefixes."
            }
        
        # Rule 3: Manual prefixes with vpc_children_type_flag=False can have child prefixes
        # This allows subdivision of prefixes including public IP blocks (e.g., /26 -> /28)
        return {
            "can_create_child": True, 
            "reason": "Manual prefix with vpc_children_type_flag=False can have child prefixes (allows subdivision)"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# VRF endpoints
@app.get("/api/vrfs", response_model=List[VRFResponse])
async def get_vrfs(pm: PrefixManager = Depends(get_prefix_manager)):
    """Get all VRFs"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vrfs = session.query(VRF).all()
        return [VRFResponse(
            vrf_id=vrf.vrf_id,
            description=vrf.description,
            tags=vrf.tags,
            routable_flag=vrf.routable_flag,
            is_default=vrf.is_default
        ) for vrf in vrfs]

@app.post("/api/vrfs", response_model=VRFResponse)
async def create_vrf(
    vrf_data: VRFCreate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Create a new VRF"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        # Check if VRF ID already exists
        existing_vrf = session.query(VRF).filter(VRF.vrf_id == vrf_data.vrf_id).first()
        if existing_vrf:
            raise HTTPException(status_code=400, detail=f"VRF with ID '{vrf_data.vrf_id}' already exists")
        
        # If setting as default, unset other defaults
        if vrf_data.is_default:
            session.query(VRF).update({VRF.is_default: False})
        
        # Create new VRF
        vrf = VRF(
            vrf_id=vrf_data.vrf_id,
            description=vrf_data.description,
            tags=vrf_data.tags or {},
            routable_flag=vrf_data.routable_flag,
            is_default=vrf_data.is_default
        )
        
        session.add(vrf)
        session.commit()
        session.refresh(vrf)
        
        return VRFResponse(
            vrf_id=vrf.vrf_id,
            description=vrf.description,
            tags=vrf.tags,
            routable_flag=vrf.routable_flag,
            is_default=vrf.is_default
        )

@app.get("/api/vrfs/{vrf_id}", response_model=VRFResponse)
async def get_vrf(
    vrf_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get a specific VRF by ID"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vrf = session.query(VRF).filter(VRF.vrf_id == vrf_id).first()
        if not vrf:
            raise HTTPException(status_code=404, detail="VRF not found")
        
        return VRFResponse(
            vrf_id=vrf.vrf_id,
            description=vrf.description,
            tags=vrf.tags,
            routable_flag=vrf.routable_flag,
            is_default=vrf.is_default
        )

@app.put("/api/vrfs/{vrf_id}", response_model=VRFResponse)
async def update_vrf(
    vrf_id: str,
    vrf_data: VRFUpdate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Update an existing VRF"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vrf = session.query(VRF).filter(VRF.vrf_id == vrf_id).first()
        if not vrf:
            raise HTTPException(status_code=404, detail="VRF not found")
        
        # Prevent editing auto-created VRFs
        if is_auto_created_vrf(vrf_id):
            raise HTTPException(status_code=403, detail="Cannot edit auto-created VRF")
        
        # If setting as default, unset other defaults
        if vrf_data.is_default is True:
            session.query(VRF).filter(VRF.vrf_id != vrf_id).update({VRF.is_default: False})
        
        # Update fields if provided
        if vrf_data.description is not None:
            vrf.description = vrf_data.description
        if vrf_data.tags is not None:
            vrf.tags = vrf_data.tags
        if vrf_data.routable_flag is not None:
            vrf.routable_flag = vrf_data.routable_flag
        if vrf_data.is_default is not None:
            vrf.is_default = vrf_data.is_default
        
        session.commit()
        session.refresh(vrf)
        
        return VRFResponse(
            vrf_id=vrf.vrf_id,
            description=vrf.description,
            tags=vrf.tags,
            routable_flag=vrf.routable_flag,
            is_default=vrf.is_default
        )

@app.delete("/api/vrfs/{vrf_id}")
async def delete_vrf(
    vrf_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Delete a VRF (only if no prefixes are using it)"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vrf = session.query(VRF).filter(VRF.vrf_id == vrf_id).first()
        if not vrf:
            raise HTTPException(status_code=404, detail="VRF not found")
        
        # Prevent deleting auto-created VRFs
        if is_auto_created_vrf(vrf_id):
            raise HTTPException(status_code=403, detail="Cannot delete auto-created VRF")
        
        # Check if VRF is being used by any prefixes
        prefix_count = session.query(Prefix).filter(Prefix.vrf_id == vrf_id).count()
        if prefix_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete VRF '{vrf_id}' - it is being used by {prefix_count} prefix(es)"
            )
        
        # Prevent deletion of default VRF if it's the only one
        if vrf.is_default:
            total_vrfs = session.query(VRF).count()
            if total_vrfs == 1:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot delete the only VRF in the system"
                )
        
        session.delete(vrf)
        session.commit()
        
        return {"message": f"VRF '{vrf_id}' deleted successfully"}

# VPC endpoints
@app.get("/api/vpcs", response_model=List[VPCResponse])
async def get_vpcs(pm: PrefixManager = Depends(get_prefix_manager)):
    """Get all VPCs"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vpcs = session.query(VPC).all()
        return [VPCResponse(
            vpc_id=str(vpc.vpc_id),
            description=vpc.description,
            provider=vpc.provider,
            provider_account_id=vpc.provider_account_id,
            provider_vpc_id=vpc.provider_vpc_id,
            region=vpc.region,
            tags=vpc.tags
        ) for vpc in vpcs]

@app.get("/api/vpcs/{vpc_id}", response_model=VPCResponse)
async def get_vpc(vpc_id: str, pm: PrefixManager = Depends(get_prefix_manager)):
    """Get specific VPC by ID"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vpc = session.query(VPC).filter(VPC.vpc_id == vpc_id).first()
        if not vpc:
            raise HTTPException(status_code=404, detail="VPC not found")
        
        return VPCResponse(
            vpc_id=str(vpc.vpc_id),
            description=vpc.description,
            provider=vpc.provider,
            provider_account_id=vpc.provider_account_id,
            provider_vpc_id=vpc.provider_vpc_id,
            region=vpc.region,
            tags=vpc.tags
        )

@app.get("/api/vpcs/{vpc_id}/associations")
async def get_vpc_associations(vpc_id: str, pm: PrefixManager = Depends(get_prefix_manager)):
    """Get all prefix associations for a specific VPC"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        from models import VPCPrefixAssociation, Prefix
        
        # Get all associations for this VPC with prefix details
        associations = session.query(VPCPrefixAssociation, Prefix).join(
            Prefix, VPCPrefixAssociation.parent_prefix_id == Prefix.prefix_id
        ).filter(
            VPCPrefixAssociation.vpc_id == vpc_id
        ).all()
        
        result = []
        for association, prefix in associations:
            result.append({
                "association_id": str(association.association_id),
                "vpc_prefix_cidr": str(association.vpc_prefix_cidr),
                "routable": association.routable,
                "prefix_id": prefix.prefix_id,
                "prefix_cidr": str(prefix.cidr),
                "prefix_vrf_id": prefix.vrf_id,
                "prefix_tags": prefix.tags,
                "prefix_source": prefix.source
            })
        
        return result

@app.post("/api/vpcs", response_model=VPCResponse)
async def create_vpc(
    vpc_data: VPCCreate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Create a new VPC"""
    try:
        vpc = pm.create_vpc(
            description=vpc_data.description,
            provider=vpc_data.provider,
            provider_account_id=vpc_data.provider_account_id,
            provider_vpc_id=vpc_data.provider_vpc_id,
            region=vpc_data.region,
            tags=vpc_data.tags
        )
        return VPCResponse(
            vpc_id=str(vpc.vpc_id),
            description=vpc.description,
            provider=vpc.provider,
            provider_account_id=vpc.provider_account_id,
            provider_vpc_id=vpc.provider_vpc_id,
            region=vpc.region,
            tags=vpc.tags
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/vpcs/{vpc_id}", response_model=VPCResponse)
async def update_vpc(
    vpc_id: str,
    vpc_data: VPCUpdate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Update an existing VPC"""
    try:
        # Convert Pydantic model to dict, excluding None values
        update_data = {k: v for k, v in vpc_data.dict().items() if v is not None}
        
        vpc = pm.update_vpc(vpc_id, **update_data)
        
        return VPCResponse(
            vpc_id=str(vpc.vpc_id),
            description=vpc.description,
            provider=vpc.provider,
            provider_account_id=vpc.provider_account_id,
            provider_vpc_id=vpc.provider_vpc_id,
            region=vpc.region,
            tags=vpc.tags
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/vpcs/{vpc_id}")
async def delete_vpc(
    vpc_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Delete a VPC (only if no prefixes or associations are using it)"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vpc = session.query(VPC).filter(VPC.vpc_id == uuid.UUID(vpc_id)).first()
        if not vpc:
            raise HTTPException(status_code=404, detail="VPC not found")
        
        # Check if VPC is being used by any prefixes
        prefix_count = session.query(Prefix).filter(Prefix.vpc_id == uuid.UUID(vpc_id)).count()
        if prefix_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete VPC '{vpc.provider_vpc_id}' - it is being used by {prefix_count} prefix(es)"
            )
        
        # Check if VPC has any associations
        from models import VPCPrefixAssociation
        association_count = session.query(VPCPrefixAssociation).filter(
            VPCPrefixAssociation.vpc_id == uuid.UUID(vpc_id)
        ).count()
        if association_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete VPC '{vpc.provider_vpc_id}' - it has {association_count} prefix association(s)"
            )
        
        session.delete(vpc)
        session.commit()
        
        return {"message": f"VPC '{vpc.provider_vpc_id}' deleted successfully"}

@app.get("/api/prefixes/{prefix_id}/can-associate-vpc")
async def can_associate_vpc(
    prefix_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Check if a prefix can be associated with a VPC"""
    try:
        prefix = pm.get_prefix_by_id(prefix_id)
        if not prefix:
            raise HTTPException(status_code=404, detail="Prefix not found")
        
        # Rule 1: Prefixes whose source is cloud VPC cannot associate to VPC
        if prefix.source == 'vpc':
            return {
                "can_associate": False, 
                "reason": "Prefixes whose source is cloud VPC cannot associate to VPC"
            }
        
        # Rule 2: Routable prefixes can only associate to one VPC ID
        if prefix.routable:
            with get_db_session_with_http_error_handling(pm.db_manager) as session:
                from models import VPCPrefixAssociation
                existing_association = session.query(VPCPrefixAssociation).filter(
                    VPCPrefixAssociation.parent_prefix_id == prefix_id
                ).first()
                
                if existing_association:
                    return {
                        "can_associate": False,
                        "reason": "Routable prefixes can only associate to one VPC ID. This prefix is already associated.",
                        "existing_vpc_id": str(existing_association.vpc_id)
                    }
        
        return {
            "can_associate": True,
            "reason": "Non-routable prefixes can associate to multiple VPC IDs" if not prefix.routable else "Routable prefix not yet associated"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/prefixes/{prefix_id}/vpc-associations")
async def get_prefix_vpc_associations(
    prefix_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get all VPC associations for a specific prefix"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        from models import VPCPrefixAssociation, VPC
        
        # Get all associations for this prefix with VPC details
        associations = session.query(VPCPrefixAssociation, VPC).join(
            VPC, VPCPrefixAssociation.vpc_id == VPC.vpc_id
        ).filter(
            VPCPrefixAssociation.parent_prefix_id == prefix_id
        ).all()
        
        result = []
        for association, vpc in associations:
            result.append({
                "association_id": str(association.association_id),
                "vpc_id": str(association.vpc_id),
                "vpc_prefix_cidr": str(association.vpc_prefix_cidr),
                "routable": association.routable,
                "provider_vpc_id": vpc.provider_vpc_id,
                "provider": vpc.provider,
                "description": vpc.description,
                "region": vpc.region
            })
        
        return result

@app.delete("/api/vpc-associations/{association_id}")
async def remove_vpc_association(
    association_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Remove a VPC association and update prefix tags"""
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        from models import VPCPrefixAssociation, VPC
        
        # Get the association to be deleted
        association = session.query(VPCPrefixAssociation).filter(
            VPCPrefixAssociation.association_id == uuid.UUID(association_id)
        ).first()
        
        if not association:
            raise HTTPException(status_code=404, detail="VPC association not found")
        
        parent_prefix_id = association.parent_prefix_id
        vpc_id = association.vpc_id
        
        # Get the VPC to get provider_vpc_id
        vpc = session.query(VPC).filter(VPC.vpc_id == vpc_id).first()
        
        # Delete the association
        session.delete(association)
        session.commit()
        
        # Update prefix tags - remove the associated_vpc tag if this was the only association
        remaining_associations = session.query(VPCPrefixAssociation).filter(
            VPCPrefixAssociation.parent_prefix_id == parent_prefix_id
        ).count()
        
        if remaining_associations == 0:
            # Remove the associated_vpc tag completely
            prefix = pm.get_prefix_by_id(parent_prefix_id)
            if prefix and prefix.tags and 'associated_vpc' in prefix.tags:
                current_tags = prefix.tags.copy()
                del current_tags['associated_vpc']
                pm.update_manual_prefix(parent_prefix_id, tags=current_tags)
        
        return {
            "message": "VPC association removed successfully",
            "provider_vpc_id": vpc.provider_vpc_id if vpc else None,
            "tags_updated": remaining_associations == 0
        }

@app.post("/api/vpc-associations")
async def create_vpc_association(
    association_data: VPCAssociation,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Associate a VPC with a prefix with validation rules"""
    # Get the parent prefix to validate rules
    parent_prefix = pm.get_prefix_by_id(association_data.parent_prefix_id)
    if not parent_prefix:
        raise HTTPException(status_code=404, detail="Parent prefix not found")
    
    # Rule 1: Prefixes whose source is cloud VPC cannot associate to VPC
    if parent_prefix.source == 'vpc':
        raise HTTPException(
            status_code=400, 
            detail="Prefixes whose source is cloud VPC cannot associate to VPC"
        )
    
    # Check for existing associations
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        from models import VPCPrefixAssociation
        
        # Check if this exact VPC is already associated (prevent duplicates)
        duplicate_association = session.query(VPCPrefixAssociation).filter(
            VPCPrefixAssociation.parent_prefix_id == association_data.parent_prefix_id,
            VPCPrefixAssociation.vpc_id == uuid.UUID(association_data.vpc_id)
        ).first()
        
        if duplicate_association:
            raise HTTPException(
                status_code=400,
                detail="This VPC is already associated with this prefix."
            )
        
        # Rule 2: Routable prefixes can only associate to one VPC ID
        if parent_prefix.routable:
            existing_association = session.query(VPCPrefixAssociation).filter(
                VPCPrefixAssociation.parent_prefix_id == association_data.parent_prefix_id
            ).first()
            
            if existing_association:
                raise HTTPException(
                    status_code=400,
                    detail="Routable prefixes can only associate to one VPC ID. This prefix is already associated."
                )
    
    # Create the association
    association = pm.associate_vpc_with_prefix(
        vpc_id=uuid.UUID(association_data.vpc_id),
        vpc_prefix_cidr=association_data.vpc_prefix_cidr,
        routable=association_data.routable,
        parent_prefix_id=association_data.parent_prefix_id
    )
    
    # Rule 4: Add associated_vpc tag to the prefix using provider_vpc_id
    # Get the VPC to retrieve the provider_vpc_id
    with get_db_session_with_http_error_handling(pm.db_manager) as session:
        vpc = session.query(VPC).filter(VPC.vpc_id == uuid.UUID(association_data.vpc_id)).first()
        if not vpc:
            raise HTTPException(status_code=404, detail="VPC not found")
        
        current_tags = parent_prefix.tags.copy() if parent_prefix.tags else {}
        current_tags['associated_vpc'] = vpc.provider_vpc_id
        
        # Update the prefix with the new tag
        pm.update_manual_prefix(association_data.parent_prefix_id, tags=current_tags)
    
    return {
        "association_id": str(association.association_id), 
        "message": "VPC associated successfully",
        "tags_updated": True
    }

# Backup/Restore endpoints (Internal Docker storage)
@app.post("/api/backup")
async def create_backup(description: str = None):
    """Create a new internal backup"""
    try:
        backup_manager = BackupManager(db_manager)
        result = backup_manager.create_backup(description)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Backup created successfully",
                "backup_id": result["backup_id"],
                "backup_info": result["backup_info"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail=f"Backup failed: {result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backup failed: {str(e)}")

@app.get("/api/backups")
async def list_backups():
    """List all available backups"""
    try:
        backup_manager = BackupManager(db_manager)
        backups = backup_manager.list_backups()
        
        return {
            "status": "success",
            "backups": backups,
            "count": len(backups)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list backups: {str(e)}")

@app.post("/api/restore/{backup_id}")
async def restore_backup(backup_id: str):
    """Restore from a specific backup"""
    try:
        backup_manager = BackupManager(db_manager)
        result = backup_manager.restore_backup(backup_id)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": result["message"],
                "backup_id": backup_id,
                "restore_results": result["restore_results"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=f"Restore failed: {result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Restore failed: {str(e)}")

@app.delete("/api/backup/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete a specific backup"""
    try:
        backup_manager = BackupManager(db_manager)
        result = backup_manager.delete_backup(backup_id)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": result["message"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete backup: {str(e)}")

@app.get("/api/backup/{backup_id}")
async def get_backup_details(backup_id: str):
    """Get detailed information about a specific backup"""
    try:
        backup_manager = BackupManager(db_manager)
        result = backup_manager.get_backup_details(backup_id)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "backup_info": result["backup_info"]
            }
        else:
            raise HTTPException(status_code=404, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get backup details: {str(e)}")

# PC Export/Import endpoints (User's PC folders)
@app.post("/api/pc-export")
async def pc_export_data(pc_folder: str, export_name: str = None):
    """Export data to user's PC folder"""
    try:
        pc_manager = PCExportImportManager(db_manager)
        result = pc_manager.export_to_pc(pc_folder, export_name)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Data exported to PC successfully",
                "export_name": result["export_name"],
                "export_path": result["export_path"],
                "files_created": result["files_created"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PC export failed: {str(e)}")

@app.post("/api/pc-import")
async def pc_import_data(pc_folder: str):
    """Import data from user's PC folder"""
    try:
        pc_manager = PCExportImportManager(db_manager)
        result = pc_manager.import_from_pc(pc_folder)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": result["message"],
                "import_results": result["import_results"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PC import failed: {str(e)}")

@app.get("/api/pc-scan")
async def scan_pc_folder(pc_folder: str):
    """Scan user's PC folder for importable exports"""
    try:
        pc_manager = PCExportImportManager(db_manager)
        result = pc_manager.scan_pc_folder(pc_folder)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "pc_folder": result["pc_folder"],
                "exports_found": result["exports_found"],
                "valid_exports": result["valid_exports"],
                "total_items": result["total_items"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PC scan failed: {str(e)}")

@app.get("/api/pc-validate")
async def validate_pc_folder(pc_folder: str):
    """Validate that PC folder contains valid IPAM export"""
    try:
        pc_manager = PCExportImportManager(db_manager)
        result = pc_manager.validate_pc_export(pc_folder)
        
        if result["status"] == "success":
            return {
                "status": "success",
                "validation": result["validation"]
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PC validation failed: {str(e)}")


# Device42 IP Address endpoints
class IPAddressResponse(BaseModel):
    id: int
    device42_id: Optional[str]
    ip_address: str
    label: str
    subnet: Optional[str]
    type: Optional[str]
    available: Optional[bool]
    resource: Optional[str]
    notes: Optional[str]
    first_added: Optional[datetime]
    last_updated: Optional[datetime]
    port: Optional[str]
    cloud_account: Optional[str]
    is_public: Optional[bool]
    details: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

@app.get("/api/ip-addresses", response_model=List[IPAddressResponse])
async def get_ip_addresses(
    label: Optional[str] = Query(None, description="Filter by label"),
    ip_address: Optional[str] = Query(None, description="Filter by exact IP address"),
    exact: Optional[bool] = Query(False, description="If true, use exact match for label; if false, use partial match (contains)"),
    limit: Optional[int] = Query(100, description="Maximum number of results to return")
):
    """
    Query IP addresses by label or IP address.
    
    Label matching:
    - If exact=False (default): case-insensitive partial match (contains)
    - If exact=True: case-insensitive exact match
    
    URLs can be shared with label and exact query parameters for easy sharing.
    Examples:
    - /api/ip-addresses?label=nat-gateway-prod&exact=true (exact match)
    - /api/ip-addresses?label=nat-gateway-prod&exact=false (partial match, default)
    - /api/ip-addresses (no label - returns all IP addresses)
    """
    try:
        with get_db_session_with_http_error_handling(db_manager) as session:
            query = session.query(Device42IPAddress)
            
            # Filter by label if provided
            if label:
                if exact:
                    # Exact match (case-insensitive, no wildcards)
                    query = query.filter(Device42IPAddress.label.ilike(label))
                else:
                    # Partial match (contains, case-insensitive)
                    query = query.filter(Device42IPAddress.label.ilike(f'%{label}%'))
            
            # Filter by exact IP address if provided
            if ip_address:
                query = query.filter(Device42IPAddress.ip_address == ip_address)
            
            # Order by label and IP address for consistent results
            query = query.order_by(Device42IPAddress.label, Device42IPAddress.ip_address)
            
            # Apply limit
            if limit:
                query = query.limit(limit)
            
            ip_addresses = query.all()
            
            return [IPAddressResponse(
                id=ip.id,
                device42_id=ip.device42_id,
                ip_address=str(ip.ip_address),
                label=ip.label,
                subnet=ip.subnet,
                type=ip.type,
                available=ip.available,
                resource=ip.resource,
                notes=ip.notes,
                first_added=ip.first_added,
                last_updated=ip.last_updated,
                port=ip.port,
                cloud_account=ip.cloud_account,
                is_public=ip.is_public,
                details=ip.details or {},
                created_at=ip.created_at,
                updated_at=ip.updated_at
            ) for ip in ip_addresses]
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query IP addresses: {str(e)}")

@app.get("/api/ip-addresses/labels", response_model=List[str])
async def get_ip_address_labels(
    search: Optional[str] = Query(None, description="Search labels (case-insensitive partial match)")
):
    """
    Get list of all unique labels.
    Useful for autocomplete or label browsing.
    """
    try:
        with get_db_session_with_http_error_handling(db_manager) as session:
            query = session.query(Device42IPAddress.label).distinct()
            
            if search:
                query = query.filter(Device42IPAddress.label.ilike(f'%{search}%'))
            
            query = query.order_by(Device42IPAddress.label)
            
            labels = [row[0] for row in query.all()]
            return labels
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get labels: {str(e)}")

# Idempotency management endpoints
@app.get("/api/idempotency/stats")
async def get_idempotency_stats():
    """Get statistics about idempotency records"""
    try:
        stats = idempotency_service.get_record_stats()
        return {
            "status": "success",
            "stats": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get idempotency stats: {str(e)}")

@app.post("/api/idempotency/cleanup")
async def cleanup_expired_idempotency_records():
    """Manually trigger cleanup of expired idempotency records"""
    try:
        deleted_count = idempotency_service.cleanup_expired_records()
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Cleaned up {deleted_count} expired idempotency records"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

# Health check
@app.get("/health")
async def health_check():
    try:
        with get_db_session_with_http_error_handling(db_manager) as session:
            session.execute(text("SELECT 1"))
        
        # Check idempotency service
        idempotency_stats = idempotency_service.get_record_stats()
        
        return {
            "status": "healthy", 
            "database": "connected",
            "idempotency": {
                "service": "available",
                "active_records": idempotency_stats.get("active_records", 0)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Health check failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
