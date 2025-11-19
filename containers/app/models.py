from sqlalchemy import create_engine, Column, String, Boolean, Integer, DateTime, Text, ForeignKey, UniqueConstraint, CheckConstraint, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, CIDR, JSONB
from sqlalchemy.sql import func
import uuid
import json
from typing import Optional, List, Dict, Any
import ipaddress
from datetime import datetime

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
        # Validate for conflicts before creating
        self.validate_prefix_conflicts(vrf_id, cidr, parent_prefix_id)
        
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

    def find_matching_parent_prefixes(self, vrf_id: str, tags: Dict[str, Any], 
                                     parent_prefix_id: Optional[str] = None) -> List[Prefix]:
        """Find parent prefixes that match the given tags (strict match)"""
        session = self.db_manager.get_session()
        try:
            query = session.query(Prefix).filter(
                Prefix.vrf_id == vrf_id,
                Prefix.source == 'manual'  # Only manual prefixes can be parents for allocation
            )
            
            # If specific parent is provided, use only that
            if parent_prefix_id:
                query = query.filter(Prefix.prefix_id == parent_prefix_id)
            
            all_prefixes = query.all()
            
            # Filter by strict tag matching
            matching_prefixes = []
            for prefix in all_prefixes:
                if self._tags_match_strictly(prefix.tags, tags):
                    matching_prefixes.append(prefix)
            
            return matching_prefixes
        finally:
            session.close()
    
    def _tags_match_strictly(self, prefix_tags: Dict[str, Any], required_tags: Dict[str, Any]) -> bool:
        """Check if prefix tags contain all required tags with exact values"""
        if not required_tags:  # If no tags required, any prefix matches
            return True
        
        for key, value in required_tags.items():
            if key not in prefix_tags or prefix_tags[key] != value:
                return False
        return True
    
    def calculate_available_subnets(self, parent_prefix: Prefix, subnet_size: int) -> List[str]:
        """Calculate all possible subnets of given size within parent prefix"""
        try:
            parent_network = ipaddress.ip_network(str(parent_prefix.cidr), strict=False)
            
            # Generate all possible subnets of the requested size
            possible_subnets = list(parent_network.subnets(new_prefix=subnet_size))
            
            # Get existing child prefixes
            session = self.db_manager.get_session()
            try:
                children = session.query(Prefix).filter(
                    Prefix.parent_prefix_id == parent_prefix.prefix_id
                ).all()
                
                # Convert existing children to networks for overlap checking
                existing_networks = []
                for child in children:
                    try:
                        existing_networks.append(ipaddress.ip_network(str(child.cidr), strict=False))
                    except ValueError:
                        continue  # Skip invalid CIDRs
                
                # Find available subnets (no overlap with existing)
                available_subnets = []
                for subnet in possible_subnets:
                    is_available = True
                    for existing in existing_networks:
                        if subnet.overlaps(existing):
                            is_available = False
                            break
                    if is_available:
                        available_subnets.append(str(subnet))
                
                return available_subnets
            finally:
                session.close()
                
        except (ValueError, ipaddress.AddressValueError) as e:
            raise ValueError(f"Invalid parent CIDR {parent_prefix.cidr}: {e}")
    
    def validate_prefix_conflicts(self, vrf_id: str, cidr: str, parent_prefix_id: Optional[str] = None) -> None:
        """
        Validate that a new prefix doesn't conflict with existing prefixes.
        
        Checks for:
        1. Exact duplicate CIDR in same VRF
        2. Overlapping CIDRs with sibling prefixes (same parent)
        
        Args:
            vrf_id: VRF ID where prefix will be created
            cidr: CIDR block to validate
            parent_prefix_id: Parent prefix ID (None for root prefixes)
            
        Raises:
            ValueError: If conflicts are found
        """
        session = self.db_manager.get_session()
        try:
            import ipaddress
            
            # Parse the new CIDR
            try:
                new_network = ipaddress.ip_network(cidr, strict=False)
            except (ValueError, ipaddress.AddressValueError) as e:
                raise ValueError(f"Invalid CIDR format '{cidr}': {e}")
            
            # Check 1: Exact duplicate in same VRF
            existing_exact = session.query(Prefix).filter(
                Prefix.vrf_id == vrf_id,
                Prefix.cidr == cidr
            ).first()
            
            if existing_exact:
                raise ValueError(f"Prefix {cidr} already exists in VRF {vrf_id}")
            
            # Check 2: Overlapping with sibling prefixes (same parent)
            if parent_prefix_id:
                # Get all sibling prefixes (same parent)
                siblings = session.query(Prefix).filter(
                    Prefix.vrf_id == vrf_id,
                    Prefix.parent_prefix_id == parent_prefix_id
                ).all()
            else:
                # Get all root prefixes in same VRF (no parent)
                siblings = session.query(Prefix).filter(
                    Prefix.vrf_id == vrf_id,
                    Prefix.parent_prefix_id.is_(None)
                ).all()
            
            # Check for overlaps with siblings
            for sibling in siblings:
                try:
                    sibling_network = ipaddress.ip_network(str(sibling.cidr), strict=False)
                except (ValueError, ipaddress.AddressValueError):
                    # Skip invalid existing CIDRs
                    continue
                
                # Check if networks overlap
                if new_network.overlaps(sibling_network):
                    raise ValueError(
                        f"Prefix {cidr} overlaps with existing sibling prefix {sibling.cidr} "
                        f"under the same parent"
                    )
                    
        finally:
            session.close()

    def allocate_subnet(self, vrf_id: str, subnet_size: int, tags: Optional[Dict[str, Any]] = None,
                       routable: bool = True, parent_prefix_id: Optional[str] = None,
                       description: Optional[str] = None) -> Dict[str, Any]:
        """
        Allocate the first available subnet of specified size from matching parent prefixes.
        
        Args:
            vrf_id: VRF ID to search in
            subnet_size: Subnet mask length (e.g., 24 for /24)
            tags: Tags to match parent prefixes (strict match)
            routable: Whether allocated subnet should be routable
            parent_prefix_id: Optional specific parent prefix ID
            description: Optional description for the allocated subnet
            
        Returns:
            Dict containing allocation details
            
        Raises:
            ValueError: If no suitable parent found or no available space
        """
        tags = tags or {}
        
        # Find matching parent prefixes
        parent_prefixes = self.find_matching_parent_prefixes(vrf_id, tags, parent_prefix_id)
        
        if not parent_prefixes:
            if parent_prefix_id:
                raise ValueError(f"Parent prefix {parent_prefix_id} not found or doesn't match criteria")
            else:
                raise ValueError(f"No parent prefixes found in VRF {vrf_id} matching tags: {tags}")
        
        # Try each parent prefix until we find available space
        for parent in parent_prefixes:
            try:
                # Validate routable inheritance
                if routable and not parent.routable:
                    continue  # Skip non-routable parents if we need routable subnet
                
                available_subnets = self.calculate_available_subnets(parent, subnet_size)
                
                if available_subnets:
                    # Allocate the first available subnet
                    allocated_cidr = available_subnets[0]
                    
                    # Prepare tags for the new subnet
                    subnet_tags = tags.copy()
                    if description:
                        subnet_tags['description'] = description
                    subnet_tags['allocated_from'] = parent.prefix_id
                    subnet_tags['allocation_timestamp'] = str(datetime.now())
                    
                    # Create the new prefix
                    allocated_prefix = self.create_manual_prefix(
                        vrf_id=vrf_id,
                        cidr=allocated_cidr,
                        parent_prefix_id=parent.prefix_id,
                        tags=subnet_tags,
                        routable=routable,
                        vpc_children_type_flag=False
                    )
                    
                    return {
                        'allocated_cidr': allocated_cidr,
                        'parent_prefix_id': parent.prefix_id,
                        'prefix_id': allocated_prefix.prefix_id,
                        'available_count': len(available_subnets) - 1,  # Subtract the one we just allocated
                        'parent_cidr': str(parent.cidr),
                        'tags': allocated_prefix.tags,
                        'routable': allocated_prefix.routable,
                        'created_at': allocated_prefix.created_at
                    }
                    
            except ValueError as e:
                # Log error and continue to next parent
                print(f"Error with parent {parent.prefix_id}: {e}")
                continue
        
        # No available space found in any matching parent
        parent_cidrs = [str(p.cidr) for p in parent_prefixes]
        raise ValueError(f"No available /{subnet_size} subnets found in parent prefixes: {parent_cidrs}")

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
