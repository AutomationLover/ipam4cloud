#!/usr/bin/env python3
"""
FastAPI Backend for Prefix Management System
Provides REST API endpoints for the Vue.js frontend
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import sys
import uuid
from datetime import datetime

# Add the app directory to Python path to import models
sys.path.append('/app')
from models import DatabaseManager, PrefixManager, VRF, VPC, Prefix

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

# CORS middleware for Vue.js frontends (admin + readonly portals)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # Admin Portal
        "http://localhost:8081",  # Read-Only Portal
        "http://localhost:3000"   # Development fallback
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection
database_url = os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@postgres:5432/prefix_management')
db_manager = DatabaseManager(database_url)
prefix_manager = PrefixManager(db_manager)

def get_prefix_manager():
    return prefix_manager

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
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get prefixes in tree structure"""
    try:
        prefixes = pm.get_prefix_tree(vrf_id)
        return build_tree(prefixes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/prefixes", response_model=PrefixResponse)
async def create_prefix(
    prefix_data: PrefixCreate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Create a new manual prefix"""
    try:
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
    """Check if a child prefix can be created under this prefix"""
    try:
        prefix = pm.get_prefix_by_id(prefix_id)
        if not prefix:
            raise HTTPException(status_code=404, detail="Prefix not found")
        
        # Rule 1: VPC-sourced prefixes cannot have child prefixes
        if prefix.source == 'vpc':
            return {"can_create_child": False, "reason": "VPC-sourced prefixes cannot have child prefixes"}
        
        # Rule 2: Manual prefixes associated with VPC cannot have child prefixes
        if prefix.source == 'manual':
            is_associated = pm.is_prefix_associated_with_vpc(prefix_id)
            if is_associated:
                return {"can_create_child": False, "reason": "Manual prefixes associated with VPC cannot have child prefixes"}
        
        # Rule 3: Manual prefixes not associated with VPC can have child prefixes
        return {"can_create_child": True, "reason": "Manual prefix not associated with VPC"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# VRF endpoints
@app.get("/api/vrfs", response_model=List[VRFResponse])
async def get_vrfs(pm: PrefixManager = Depends(get_prefix_manager)):
    """Get all VRFs"""
    try:
        session = pm.db_manager.get_session()
        try:
            vrfs = session.query(VRF).all()
            return [VRFResponse(
                vrf_id=vrf.vrf_id,
                description=vrf.description,
                tags=vrf.tags,
                routable_flag=vrf.routable_flag,
                is_default=vrf.is_default
            ) for vrf in vrfs]
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vrfs", response_model=VRFResponse)
async def create_vrf(
    vrf_data: VRFCreate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Create a new VRF"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vrfs/{vrf_id}", response_model=VRFResponse)
async def get_vrf(
    vrf_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Get a specific VRF by ID"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/vrfs/{vrf_id}", response_model=VRFResponse)
async def update_vrf(
    vrf_id: str,
    vrf_data: VRFUpdate,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Update an existing VRF"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/vrfs/{vrf_id}")
async def delete_vrf(
    vrf_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Delete a VRF (only if no prefixes are using it)"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# VPC endpoints
@app.get("/api/vpcs", response_model=List[VPCResponse])
async def get_vpcs(pm: PrefixManager = Depends(get_prefix_manager)):
    """Get all VPCs"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vpcs/{vpc_id}", response_model=VPCResponse)
async def get_vpc(vpc_id: str, pm: PrefixManager = Depends(get_prefix_manager)):
    """Get specific VPC by ID"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/vpcs/{vpc_id}/associations")
async def get_vpc_associations(vpc_id: str, pm: PrefixManager = Depends(get_prefix_manager)):
    """Get all prefix associations for a specific VPC"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            session = pm.db_manager.get_session()
            try:
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
            finally:
                session.close()
        
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
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/vpc-associations/{association_id}")
async def remove_vpc_association(
    association_id: str,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Remove a VPC association and update prefix tags"""
    try:
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vpc-associations")
async def create_vpc_association(
    association_data: VPCAssociation,
    pm: PrefixManager = Depends(get_prefix_manager)
):
    """Associate a VPC with a prefix with validation rules"""
    try:
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
        session = pm.db_manager.get_session()
        try:
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
        finally:
            session.close()
        
        # Create the association
        association = pm.associate_vpc_with_prefix(
            vpc_id=uuid.UUID(association_data.vpc_id),
            vpc_prefix_cidr=association_data.vpc_prefix_cidr,
            routable=association_data.routable,
            parent_prefix_id=association_data.parent_prefix_id
        )
        
        # Rule 4: Add associated_vpc tag to the prefix using provider_vpc_id
        # Get the VPC to retrieve the provider_vpc_id
        session = pm.db_manager.get_session()
        try:
            vpc = session.query(VPC).filter(VPC.vpc_id == uuid.UUID(association_data.vpc_id)).first()
            if not vpc:
                raise HTTPException(status_code=404, detail="VPC not found")
            
            current_tags = parent_prefix.tags.copy() if parent_prefix.tags else {}
            current_tags['associated_vpc'] = vpc.provider_vpc_id
            
            # Update the prefix with the new tag
            pm.update_manual_prefix(association_data.parent_prefix_id, tags=current_tags)
        finally:
            session.close()
        
        return {
            "association_id": str(association.association_id), 
            "message": "VPC associated successfully",
            "tags_updated": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    try:
        session = db_manager.get_session()
        session.execute("SELECT 1")
        session.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
