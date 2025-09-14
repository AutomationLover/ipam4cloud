from sqlalchemy import create_engine, Column, String, Boolean, Integer, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, CIDR, JSONB
from sqlalchemy.sql import func
import uuid
import json
from typing import Optional, List, Dict, Any
import ipaddress

Base = declarative_base()

class VRF(Base):
    __tablename__ = 'vrf'
    
    vrf_id = Column(String, primary_key=True)
    description = Column(Text)
    tags = Column(JSONB, default={}, nullable=False)
    routable_flag = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    prefixes = relationship("Prefix", back_populates="vrf")
    
    def __repr__(self):
        return f"<VRF(vrf_id='{self.vrf_id}', description='{self.description}', is_default={self.is_default})>"

class VPC(Base):
    __tablename__ = 'vpc'
    
    vpc_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    description = Column(Text)
    provider = Column(String, nullable=False)  # cloud_provider enum
    provider_account_id = Column(String)
    provider_vpc_id = Column(String, nullable=False)
    region = Column(String)
    tags = Column(JSONB, default={}, nullable=False)
    
    # Relationships
    prefixes = relationship("Prefix", back_populates="vpc")
    associations = relationship("VPCPrefixAssociation", back_populates="vpc")
    
    __table_args__ = (
        UniqueConstraint('provider', 'provider_account_id', 'provider_vpc_id'),
    )
    
    def __repr__(self):
        return f"<VPC(vpc_id='{self.vpc_id}', provider='{self.provider}', provider_vpc_id='{self.provider_vpc_id}')>"

class Prefix(Base):
    __tablename__ = 'prefix'
    
    prefix_id = Column(String, primary_key=True)
    vrf_id = Column(String, ForeignKey('vrf.vrf_id', ondelete='RESTRICT'), nullable=False)
    cidr = Column(CIDR, nullable=False)
    tags = Column(JSONB, default={}, nullable=False)
    indentation_level = Column(Integer, default=0, nullable=False)
    parent_prefix_id = Column(String, ForeignKey('prefix.prefix_id', ondelete='RESTRICT'))
    source = Column(String, nullable=False)  # prefix_source enum
    routable = Column(Boolean, nullable=False)
    vpc_children_type_flag = Column(Boolean, default=False, nullable=False)
    vpc_id = Column(UUID(as_uuid=True), ForeignKey('vpc.vpc_id', ondelete='SET NULL'))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    vrf = relationship("VRF", back_populates="prefixes")
    vpc = relationship("VPC", back_populates="prefixes")
    parent = relationship("Prefix", remote_side=[prefix_id], backref="children")
    
    __table_args__ = (
        UniqueConstraint('vrf_id', 'cidr'),
        CheckConstraint(
            "((source = 'vpc' AND vpc_id IS NOT NULL) OR (source = 'manual' AND vpc_id IS NULL))",
            name='vpc_fields_when_vpc_source'
        ),
    )
    
    def __repr__(self):
        return f"<Prefix(prefix_id='{self.prefix_id}', cidr='{self.cidr}', source='{self.source}', routable={self.routable})>"

class VPCPrefixAssociation(Base):
    __tablename__ = 'vpc_prefix_association'
    
    association_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vpc_id = Column(UUID(as_uuid=True), ForeignKey('vpc.vpc_id', ondelete='CASCADE'), nullable=False)
    vpc_prefix_cidr = Column(CIDR, nullable=False)
    routable = Column(Boolean, nullable=False)
    parent_prefix_id = Column(String, ForeignKey('prefix.prefix_id'), nullable=False)
    
    # Relationships
    vpc = relationship("VPC", back_populates="associations")
    parent_prefix = relationship("Prefix")
    
    __table_args__ = (
        UniqueConstraint('vpc_id', 'vpc_prefix_cidr'),
    )
    
    def __repr__(self):
        return f"<VPCPrefixAssociation(vpc_id='{self.vpc_id}', vpc_prefix_cidr='{self.vpc_prefix_cidr}', routable={self.routable})>"

class DatabaseManager:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        return self.SessionLocal()
    
    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)

class PrefixManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def create_manual_prefix(self, vrf_id: str, cidr: str, parent_prefix_id: Optional[str] = None, 
                           tags: Optional[Dict[str, Any]] = None, routable: bool = True,
                           vpc_children_type_flag: bool = False) -> Prefix:
        """Create a manual prefix entry"""
        session = self.db_manager.get_session()
        try:
            # Generate prefix_id based on the format: manual-vrfid-prefix-id
            cidr_formatted = cidr.replace('/', '-').replace('.', '-')
            prefix_id = f"manual-{vrf_id}-{cidr_formatted}"
            
            prefix = Prefix(
                prefix_id=prefix_id,
                vrf_id=vrf_id,
                cidr=cidr,
                tags=tags or {},
                parent_prefix_id=parent_prefix_id,
                source='manual',
                routable=routable,
                vpc_children_type_flag=vpc_children_type_flag
            )
            
            session.add(prefix)
            session.commit()
            session.refresh(prefix)
            return prefix
        finally:
            session.close()
    
    def create_public_ip_prefix(self, vpc_id: uuid.UUID, cidr: str, tags: Optional[Dict[str, Any]] = None) -> Prefix:
        """Create a public IP prefix entry for a VPC following the vpc-subnet-prefix format"""
        session = self.db_manager.get_session()
        try:
            # Generate prefix_id in format: vpcid-subnet-prefix (for public IPs)
            cidr_formatted = cidr.replace('/', '-').replace('.', '-')
            prefix_id = f"{vpc_id}-subnet-{cidr_formatted}"
            
            prefix = Prefix(
                prefix_id=prefix_id,
                vrf_id='public-vrf',  # All public IPs go to public-vrf
                cidr=cidr,
                tags=tags or {},
                parent_prefix_id=None,  # Public IPs have no parent (indentation level 0)
                source='vpc',  # Source is VPC since it's associated with a VPC
                routable=True,  # Public IPs are always routable
                vpc_children_type_flag=True,  # This is a VPC-related prefix
                vpc_id=vpc_id  # Associate with the VPC
            )
            
            session.add(prefix)
            session.commit()
            session.refresh(prefix)
            return prefix
        finally:
            session.close()
    
    def create_standalone_public_ip_prefix(self, cidr: str, tags: Optional[Dict[str, Any]] = None) -> Prefix:
        """Create a standalone public IP prefix entry (not associated with any VPC)"""
        session = self.db_manager.get_session()
        try:
            # Generate prefix_id for standalone public IPs
            cidr_formatted = cidr.replace('/', '-').replace('.', '-')
            prefix_id = f"public-ip-{cidr_formatted}"
            
            prefix = Prefix(
                prefix_id=prefix_id,
                vrf_id='public-vrf',  # All public IPs go to public-vrf
                cidr=cidr,
                tags=tags or {},
                parent_prefix_id=None,  # Public IPs have no parent (indentation level 0)
                source='manual',  # Source is manual for standalone IPs
                routable=True,  # Public IPs are always routable
                vpc_children_type_flag=False,  # Not VPC-specific
                vpc_id=None  # No VPC association
            )
            
            session.add(prefix)
            session.commit()
            session.refresh(prefix)
            return prefix
        finally:
            session.close()
    
    def create_vpc(self, description: str, provider: str, provider_account_id: str,
                   provider_vpc_id: str, region: str, tags: Optional[Dict[str, Any]] = None) -> VPC:
        """Create a VPC entry"""
        session = self.db_manager.get_session()
        try:
            vpc = VPC(
                description=description,
                provider=provider,
                provider_account_id=provider_account_id,
                provider_vpc_id=provider_vpc_id,
                region=region,
                tags=tags or {}
            )
            
            session.add(vpc)
            session.commit()
            session.refresh(vpc)
            return vpc
        finally:
            session.close()
    
    def update_vpc(self, vpc_id: str, **kwargs) -> VPC:
        """Update a VPC entry"""
        session = self.db_manager.get_session()
        try:
            vpc = session.query(VPC).filter(VPC.vpc_id == uuid.UUID(vpc_id)).first()
            if not vpc:
                raise ValueError(f"VPC {vpc_id} not found")
            
            # Update only provided fields
            for key, value in kwargs.items():
                if value is not None and hasattr(vpc, key):
                    setattr(vpc, key, value)
            
            session.commit()
            session.refresh(vpc)
            return vpc
        finally:
            session.close()
    
    def associate_vpc_with_prefix(self, vpc_id: uuid.UUID, vpc_prefix_cidr: str, 
                                 routable: bool, parent_prefix_id: str) -> VPCPrefixAssociation:
        """Associate a VPC with a prefix"""
        session = self.db_manager.get_session()
        try:
            association = VPCPrefixAssociation(
                vpc_id=vpc_id,
                vpc_prefix_cidr=vpc_prefix_cidr,
                routable=routable,
                parent_prefix_id=parent_prefix_id
            )
            
            session.add(association)
            session.commit()
            session.refresh(association)
            return association
        finally:
            session.close()
    
    def upsert_vpc_subnet(self, vpc_id: uuid.UUID, subnet_cidr: str, 
                         tags: Optional[Dict[str, Any]] = None) -> str:
        """Simulate the upsert_vpc_subnet stored procedure"""
        session = self.db_manager.get_session()
        try:
            # Call the stored procedure
            result = session.execute(
                text("SELECT upsert_vpc_subnet(:vpc_id, :subnet_cidr, :tags)"),
                {
                    'vpc_id': vpc_id,
                    'subnet_cidr': subnet_cidr,
                    'tags': json.dumps(tags or {})
                }
            )
            prefix_id = result.fetchone()[0]
            session.commit()
            return prefix_id
        finally:
            session.close()
    
    def get_prefix_tree(self, vrf_id: Optional[str] = None) -> List[Prefix]:
        """Get prefixes in tree order"""
        session = self.db_manager.get_session()
        try:
            query = session.query(Prefix).order_by(Prefix.vrf_id, Prefix.indentation_level, Prefix.cidr)
            if vrf_id:
                query = query.filter(Prefix.vrf_id == vrf_id)
            return query.all()
        finally:
            session.close()
    
    def get_children_prefixes(self, parent_prefix_id: str) -> List[Prefix]:
        """Get all children of a specific prefix"""
        session = self.db_manager.get_session()
        try:
            return session.query(Prefix).filter(
                Prefix.parent_prefix_id == parent_prefix_id
            ).order_by(Prefix.cidr).all()
        finally:
            session.close()
    
    def query_prefix_by_cidr(self, vrf_id: str, cidr: str) -> Optional[Prefix]:
        """Query a specific prefix by CIDR"""
        session = self.db_manager.get_session()
        try:
            return session.query(Prefix).filter(
                Prefix.vrf_id == vrf_id,
                Prefix.cidr == cidr
            ).first()
        finally:
            session.close()
    
    def filter_prefixes(self, vrf_id: Optional[str] = None, routable: Optional[bool] = None,
                       source: Optional[str] = None, provider: Optional[str] = None,
                       provider_account_id: Optional[str] = None) -> List[Prefix]:
        """Filter prefixes by various criteria"""
        session = self.db_manager.get_session()
        try:
            query = session.query(Prefix)
            
            if vrf_id:
                query = query.filter(Prefix.vrf_id == vrf_id)
            if routable is not None:
                query = query.filter(Prefix.routable == routable)
            if source:
                query = query.filter(Prefix.source == source)
            
            if provider or provider_account_id:
                query = query.join(VPC)
                if provider:
                    query = query.filter(VPC.provider == provider)
                if provider_account_id:
                    query = query.filter(VPC.provider_account_id == provider_account_id)
            
            return query.order_by(Prefix.cidr).all()
        finally:
            session.close()
    
    def update_manual_prefix(self, prefix_id: str, **kwargs) -> Prefix:
        """Update a manual prefix (only manual prefixes can be updated)"""
        session = self.db_manager.get_session()
        try:
            prefix = session.query(Prefix).filter(Prefix.prefix_id == prefix_id).first()
            if not prefix:
                raise ValueError(f"Prefix {prefix_id} not found")
            
            if prefix.source != 'manual':
                raise ValueError(f"Cannot update VPC-sourced prefix {prefix_id}")
            
            # Update only provided fields
            for key, value in kwargs.items():
                if value is not None and hasattr(prefix, key):
                    setattr(prefix, key, value)
            
            session.commit()
            session.refresh(prefix)
            return prefix
        finally:
            session.close()
    
    def delete_manual_prefix(self, prefix_id: str) -> bool:
        """Delete a manual prefix (only manual prefixes can be deleted)"""
        session = self.db_manager.get_session()
        try:
            prefix = session.query(Prefix).filter(Prefix.prefix_id == prefix_id).first()
            if not prefix:
                raise ValueError(f"Prefix {prefix_id} not found")
            
            if prefix.source != 'manual':
                raise ValueError(f"Cannot delete VPC-sourced prefix {prefix_id}")
            
            # Check if prefix has children
            children = session.query(Prefix).filter(Prefix.parent_prefix_id == prefix_id).count()
            if children > 0:
                raise ValueError(f"Cannot delete prefix {prefix_id} - it has {children} child prefixes")
            
            session.delete(prefix)
            session.commit()
            return True
        finally:
            session.close()
    
    def get_prefix_by_id(self, prefix_id: str) -> Optional[Prefix]:
        """Get a specific prefix by ID"""
        session = self.db_manager.get_session()
        try:
            return session.query(Prefix).filter(Prefix.prefix_id == prefix_id).first()
        finally:
            session.close()
    
    def is_prefix_associated_with_vpc(self, prefix_id: str) -> bool:
        """Check if a manual prefix is associated with any VPC"""
        session = self.db_manager.get_session()
        try:
            from models import VPCPrefixAssociation
            association = session.query(VPCPrefixAssociation).filter(
                VPCPrefixAssociation.parent_prefix_id == prefix_id
            ).first()
            return association is not None
        finally:
            session.close()

    def print_tree_view(self, vrf_id: Optional[str] = None):
        """Print a tree view of prefixes"""
        prefixes = self.get_prefix_tree(vrf_id)
        
        print(f"\n=== Prefix Tree {'for VRF: ' + vrf_id if vrf_id else '(All VRFs)'} ===")
        current_vrf = None
        
        for prefix in prefixes:
            if current_vrf != prefix.vrf_id:
                current_vrf = prefix.vrf_id
                print(f"\nVRF: {prefix.vrf_id}")
                print("-" * 50)
            
            indent = "  " * prefix.indentation_level
            source_marker = "[M]" if prefix.source == 'manual' else "[V]"
            routable_marker = "✓" if prefix.routable else "✗"
            
            print(f"{indent}{source_marker} {prefix.cidr} ({routable_marker}) - {prefix.prefix_id}")
            
            if prefix.tags:
                tag_str = ", ".join([f"{k}:{v}" for k, v in prefix.tags.items()])
                print(f"{indent}    Tags: {tag_str}")
