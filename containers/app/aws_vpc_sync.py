#!/usr/bin/env python3
"""
AWS VPC Subnet Synchronization Service
Fetches subnet information from AWS VPCs and updates the IPAM database.
"""

import os
import json
import time
import logging
import boto3
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from models import DatabaseManager, PrefixManager, VPC, Prefix
from json_loader import JSONDataLoader
import ipaddress

# Create logs directory if it doesn't exist
os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/aws_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SyncConfig:
    """Configuration for AWS sync operations"""
    aws_region: str
    aws_account_id: str
    vpc_configs: List[Dict[str, Any]]
    sync_interval: int = 300  # 5 minutes
    max_retries: int = 3
    batch_size: int = 10  # Batch size for processing operations
    aws_page_size: int = 50  # AWS API pagination page size
    max_subnets_per_vpc: int = 10000  # Safety limit per VPC
    db_batch_size: int = 100  # Database query batch size
    default_vrf_id: str = "prod-vrf"  # Default VRF for associations

    @classmethod
    def from_env(cls, vpc_configs: List[Dict[str, Any]]) -> 'SyncConfig':
        """Create config from environment variables"""
        return cls(
            aws_region=os.getenv('AWS_DEFAULT_REGION', 'us-east-2'),
            aws_account_id=os.getenv('AWS_ACCOUNT_ID', ''),
            vpc_configs=vpc_configs,
            sync_interval=int(os.getenv('SYNC_INTERVAL', '300')),
            max_retries=int(os.getenv('MAX_RETRIES', '3')),
            batch_size=int(os.getenv('BATCH_SIZE', '10')),
            aws_page_size=int(os.getenv('AWS_PAGE_SIZE', '50')),
            max_subnets_per_vpc=int(os.getenv('MAX_SUBNETS_PER_VPC', '10000')),
            db_batch_size=int(os.getenv('DB_BATCH_SIZE', '100')),
            default_vrf_id=os.getenv('DEFAULT_VRF_ID', 'prod-vrf')
        )

class AWSVPCSubnetSync:
    """Synchronizes AWS VPC subnet data with IPAM database"""
    
    def __init__(self, config: SyncConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.prefix_manager = PrefixManager(db_manager)
        self.ec2_client = None
        self.vpc_lookup = {}  # Cache for VPC ID mappings
        
    def initialize_aws_client(self):
        """Initialize AWS EC2 client with proper region"""
        try:
            self.ec2_client = boto3.client('ec2', region_name=self.config.aws_region)
            logger.info(f"AWS EC2 client initialized for region: {self.config.aws_region}")
        except Exception as e:
            logger.error(f"Failed to initialize AWS client: {e}")
            raise
    
    def load_vpc_registry(self) -> Dict[str, VPC]:
        """Load VPC registry from database with pagination support for large deployments"""
        session = self.db_manager.get_session()
        try:
            # Check total count first
            total_vpcs = session.query(VPC).filter(VPC.provider == 'aws').count()
            logger.info(f"Loading {total_vpcs} AWS VPCs from registry")
            
            vpc_registry = {}
            
            # For large deployments, process VPCs in batches
            if total_vpcs > 100:
                logger.info(f"Large deployment detected: processing {total_vpcs} VPCs in batches")
                offset = 0
                batch_size = self.config.db_batch_size
                
                while offset < total_vpcs:
                    batch_vpcs = session.query(VPC).filter(VPC.provider == 'aws').offset(offset).limit(batch_size).all()
                    
                    for vpc in batch_vpcs:
                        key = f"{vpc.provider_account_id}:{vpc.provider_vpc_id}"
                        vpc_registry[key] = vpc
                        self.vpc_lookup[vpc.provider_vpc_id] = vpc
                    
                    offset += batch_size
                    logger.info(f"Loaded {min(offset, total_vpcs)}/{total_vpcs} VPCs")
            else:
                # Small deployment - load all at once
                vpcs = session.query(VPC).filter(VPC.provider == 'aws').all()
                for vpc in vpcs:
                    key = f"{vpc.provider_account_id}:{vpc.provider_vpc_id}"
                    vpc_registry[key] = vpc
                    self.vpc_lookup[vpc.provider_vpc_id] = vpc
            
            logger.info(f"Successfully loaded {len(vpc_registry)} AWS VPCs from registry")
            return vpc_registry
        finally:
            session.close()
    
    def fetch_vpc_subnets(self, vpc_id: str) -> tuple[List[Dict[str, Any]], bool]:
        """Fetch all subnets for a specific VPC from AWS with pagination support
        
        Returns:
            tuple: (subnets_list, is_reachable)
                - subnets_list: List of subnet dictionaries
                - is_reachable: True if VPC was accessible, False if unreachable
        """
        try:
            # First, verify the VPC exists by describing it
            try:
                self.ec2_client.describe_vpcs(VpcIds=[vpc_id])
            except Exception as vpc_error:
                # VPC doesn't exist or is not accessible
                if 'InvalidVpcID.NotFound' in str(vpc_error) or 'InvalidVpc.NotFound' in str(vpc_error):
                    logger.warning(f"VPC {vpc_id} does not exist or is not accessible: {vpc_error}")
                else:
                    logger.warning(f"VPC {vpc_id} is unreachable: {vpc_error}")
                logger.info(f"Skipping sync for unreachable VPC {vpc_id} - keeping existing subnet data unchanged")
                return [], False
            
            subnets = []
            paginator = self.ec2_client.get_paginator('describe_subnets')
            
            # Use paginator to handle large numbers of subnets
            page_iterator = paginator.paginate(
                Filters=[
                    {'Name': 'vpc-id', 'Values': [vpc_id]}
                ],
                PaginationConfig={
                    'PageSize': self.config.aws_page_size,  # AWS API page size
                    'MaxItems': self.config.max_subnets_per_vpc  # Safety limit per VPC
                }
            )
            
            total_pages = 0
            for page in page_iterator:
                total_pages += 1
                logger.debug(f"Processing page {total_pages} for VPC {vpc_id}")
                
                for subnet in page['Subnets']:
                    # Process IPv4 CIDR block
                    subnet_info = {
                        'subnet_id': subnet['SubnetId'],
                        'cidr_block': subnet['CidrBlock'],
                        'availability_zone': subnet['AvailabilityZone'],
                        'state': subnet['State'],
                        'vpc_id': subnet['VpcId'],
                        'tags': {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])},
                        'ip_version': 4
                    }
                    subnets.append(subnet_info)
                    
                    # Process IPv6 CIDR blocks if present
                    ipv6_associations = subnet.get('Ipv6CidrBlockAssociationSet', [])
                    for ipv6_assoc in ipv6_associations:
                        if ipv6_assoc.get('Ipv6CidrBlockState', {}).get('State') == 'associated':
                            ipv6_subnet_info = {
                                'subnet_id': subnet['SubnetId'],
                                'cidr_block': ipv6_assoc['Ipv6CidrBlock'],
                                'availability_zone': subnet['AvailabilityZone'],
                                'state': subnet['State'],
                                'vpc_id': subnet['VpcId'],
                                'tags': {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])},
                                'ip_version': 6,
                                'ipv6_association_id': ipv6_assoc.get('AssociationId')
                            }
                            subnets.append(ipv6_subnet_info)
                
                # Log progress for large VPCs
                if len(subnets) % 100 == 0:
                    logger.info(f"Processed {len(subnets)} subnets so far for VPC {vpc_id}")
            
            logger.info(f"Fetched {len(subnets)} subnets across {total_pages} pages for VPC {vpc_id}")
            return subnets, True  # Successfully reached VPC
            
        except Exception as e:
            logger.warning(f"VPC {vpc_id} is unreachable: {e}")
            logger.info(f"Skipping sync for unreachable VPC {vpc_id} - keeping existing subnet data unchanged")
            return [], False  # VPC unreachable
    
    def sync_vpc_subnets(self, vpc: VPC, aws_subnets: List[Dict[str, Any]]):
        """Sync AWS subnets with database for a specific VPC with batching support"""
        session = self.db_manager.get_session()
        try:
            # Get existing subnet prefixes for this VPC with pagination for large datasets
            existing_prefixes_query = session.query(Prefix).filter(
                Prefix.vpc_id == vpc.vpc_id,
                Prefix.source == 'vpc'
            )
            
            # For very large VPCs, we might need to process in batches
            total_existing = existing_prefixes_query.count()
            if total_existing > 1000:
                logger.info(f"Large VPC detected: {total_existing} existing prefixes for VPC {vpc.provider_vpc_id}")
            
            existing_prefixes = existing_prefixes_query.all()
            
            existing_cidrs = {prefix.cidr for prefix in existing_prefixes}
            aws_cidrs = {subnet['cidr_block'] for subnet in aws_subnets}
            
            # Process subnet changes in batches for large VPCs
            new_cidrs = aws_cidrs - existing_cidrs
            deleted_cidrs = existing_cidrs - aws_cidrs
            update_cidrs = aws_cidrs & existing_cidrs
            
            # Batch process new subnets
            new_subnets = [s for s in aws_subnets if s['cidr_block'] in new_cidrs]
            if new_subnets:
                logger.info(f"Creating {len(new_subnets)} new subnet prefixes")
                for i, subnet in enumerate(new_subnets):
                    self._create_subnet_prefix(vpc, subnet)
                    if (i + 1) % self.config.batch_size == 0:
                        logger.info(f"Created {i + 1}/{len(new_subnets)} new subnets")
            
            # Batch process deleted subnets
            deleted_prefixes = [p for p in existing_prefixes if p.cidr in deleted_cidrs]
            if deleted_prefixes:
                logger.info(f"Marking {len(deleted_prefixes)} subnet prefixes as deleted")
                for i, prefix in enumerate(deleted_prefixes):
                    self._delete_subnet_prefix(prefix)
                    if (i + 1) % self.config.batch_size == 0:
                        logger.info(f"Processed {i + 1}/{len(deleted_prefixes)} deletions")
            
            # Batch process subnet updates and track resurrections
            update_subnets = [s for s in aws_subnets if s['cidr_block'] in update_cidrs]
            resurrected_count = 0
            if update_subnets:
                logger.debug(f"Updating {len(update_subnets)} existing subnet prefixes")
                for i, subnet in enumerate(update_subnets):
                    was_resurrected = self._update_subnet_prefix(vpc, subnet)
                    if was_resurrected:
                        resurrected_count += 1
                    if (i + 1) % (self.config.batch_size * 5) == 0:  # Less frequent logging for updates
                        logger.info(f"Updated {i + 1}/{len(update_subnets)} subnets")
            
            # Enhanced reporting with resurrections
            if resurrected_count > 0:
                logger.info(f"VPC {vpc.provider_vpc_id}: +{len(new_cidrs)} -{len(deleted_cidrs)} ↻{resurrected_count} subnets")
            else:
                logger.info(f"VPC {vpc.provider_vpc_id}: +{len(new_cidrs)} -{len(deleted_cidrs)} subnets")
            
        except Exception as e:
            logger.error(f"Failed to sync subnets for VPC {vpc.provider_vpc_id}: {e}")
        finally:
            session.close()
    
    def _format_cidr_for_id(self, cidr: str) -> str:
        """Format CIDR for use in prefix_id, handling both IPv4 and IPv6"""
        try:
            network = ipaddress.ip_network(cidr, strict=False)
            if network.version == 4:
                # IPv4: replace dots and slashes with hyphens
                return cidr.replace('/', '-').replace('.', '-')
            else:
                # IPv6: replace colons and slashes with hyphens, handle compressed notation
                expanded = network.exploded.replace(':', '-').replace('/', '-')
                return expanded
        except (ValueError, ipaddress.AddressValueError):
            # Fallback to simple replacement if parsing fails
            return cidr.replace('/', '-').replace('.', '-').replace(':', '-')
    
    def _create_subnet_prefix(self, vpc: VPC, subnet_data: Dict[str, Any]):
        """Create a new subnet prefix in the database"""
        try:
            # Generate prefix_id for subnet
            cidr_formatted = self._format_cidr_for_id(subnet_data['cidr_block'])
            prefix_id = f"{vpc.vpc_id}-subnet-{cidr_formatted}"
            
            # Find the correct parent prefix that contains this subnet
            session = self.db_manager.get_session()
            try:
                from models import VPCPrefixAssociation
                from sqlalchemy import func
                import ipaddress
                
                # Get the VPC association to find the parent CIDR
                vpc_association = session.query(VPCPrefixAssociation).filter(
                    VPCPrefixAssociation.vpc_id == vpc.vpc_id
                ).first()
                
                parent_prefix_id = None
                vpc_cidr_prefix = None
                if vpc_association:
                    # Find the prefix that represents the VPC's CIDR (e.g., manual-prod-vrf-10-101-0-0-16)
                    # This should be the parent for subnet prefixes
                    vpc_cidr_prefix = session.query(Prefix).filter(
                        Prefix.cidr == vpc_association.vpc_prefix_cidr,
                        Prefix.vrf_id == 'prod-vrf'  # Assuming VPC prefixes are in prod-vrf
                    ).first()
                    
                    if vpc_cidr_prefix:
                        parent_prefix_id = vpc_cidr_prefix.prefix_id
                        
                        # Verify the subnet is actually within the parent CIDR
                        subnet_network = ipaddress.ip_network(subnet_data['cidr_block'])
                        parent_network = ipaddress.ip_network(vpc_association.vpc_prefix_cidr)
                        
                        if not subnet_network.subnet_of(parent_network):
                            logger.warning(f"Subnet {subnet_data['cidr_block']} is not within VPC CIDR {vpc_association.vpc_prefix_cidr}")
                            parent_prefix_id = None
                            vpc_cidr_prefix = None
                        else:
                            logger.info(f"Found parent prefix {parent_prefix_id} for subnet {subnet_data['cidr_block']}")
                    else:
                        logger.warning(f"No prefix found for VPC CIDR {vpc_association.vpc_prefix_cidr}")
                else:
                    logger.warning(f"No VPC association found for VPC {vpc.provider_vpc_id}")
                    parent_prefix_id = None
                
                # Prepare tags
                tags = subnet_data.get('tags', {})
                tags.update({
                    'aws_subnet_id': subnet_data['subnet_id'],
                    'availability_zone': subnet_data['availability_zone'],
                    'state': subnet_data['state'],
                    'sync_source': 'aws_auto_sync',
                    'last_sync': datetime.utcnow().isoformat()
                })
                
                # Determine routable status and VRF assignment
                subnet_routable = True  # Default to routable
                subnet_vrf_id = 'prod-vrf'  # Default VRF
                
                if vpc_association and vpc_cidr_prefix:
                    # Use the association's routable flag
                    subnet_routable = vpc_association.routable
                    logger.info(f"Subnet {subnet_data['cidr_block']} routable={subnet_routable} from VPC association")
                    
                    if subnet_routable:
                        # Routable subnet: use parent prefix's VRF
                        subnet_vrf_id = vpc_cidr_prefix.vrf_id
                        logger.info(f"Routable subnet using parent VRF: {subnet_vrf_id}")
                    else:
                        # Non-routable subnet: use VPC-specific VRF
                        subnet_vrf_id = self._ensure_vpc_vrf(vpc, session)
                        logger.info(f"Non-routable subnet using VPC-specific VRF: {subnet_vrf_id}")
                else:
                    logger.warning(f"No VPC association found, using default routable=True and prod-vrf")
                
                prefix = Prefix(
                    prefix_id=prefix_id,
                    vrf_id=subnet_vrf_id,
                    cidr=subnet_data['cidr_block'],
                    tags=tags,
                    parent_prefix_id=parent_prefix_id,
                    source='vpc',
                    routable=subnet_routable,
                    vpc_children_type_flag=False,
                    vpc_id=vpc.vpc_id  # Required for VPC-sourced prefixes
                )
                
                session.add(prefix)
                session.commit()
                logger.info(f"Created subnet prefix: {subnet_data['cidr_block']} ({subnet_data['subnet_id']})")
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Failed to create subnet prefix {subnet_data['cidr_block']}: {e}")
    
    def _ensure_vpc_vrf(self, vpc: VPC, session) -> str:
        """Ensure VPC-specific VRF exists for non-routable subnets, following database logic"""
        from models import VRF
        
        # Create meaningful VRF name: provider_account_providerVPCID
        vrf_name = f"{vpc.provider}_{vpc.provider_account_id or 'unknown'}_{vpc.provider_vpc_id}"
        
        # Check if VRF already exists
        existing_vrf = session.query(VRF).filter(VRF.vrf_id == vrf_name).first()
        if existing_vrf:
            logger.debug(f"VPC VRF already exists: {vrf_name}")
            return vrf_name
        
        # Create new VPC-specific VRF
        description = f"Auto VRF for {vpc.provider} VPC {vpc.provider_vpc_id}"
        if vpc.provider_account_id:
            description += f" (Account: {vpc.provider_account_id})"
        
        vpc_vrf = VRF(
            vrf_id=vrf_name,
            description=description,
            is_default=False,
            routable_flag=False  # VPC-specific VRFs are non-routable
        )
        
        session.add(vpc_vrf)
        session.commit()
        logger.info(f"Created VPC-specific VRF: {vrf_name}")
        
        return vrf_name
    
    def _update_subnet_prefix(self, vpc: VPC, subnet_data: Dict[str, Any]) -> bool:
        """Update existing subnet prefix with latest AWS data
        
        Returns:
            bool: True if this was a resurrection (previously deleted), False otherwise
        """
        session = self.db_manager.get_session()
        try:
            prefix = session.query(Prefix).filter(
                Prefix.vpc_id == vpc.vpc_id,
                Prefix.cidr == subnet_data['cidr_block'],
                Prefix.source == 'vpc'
            ).first()
            
            if prefix:
                # Check if this was a previously deleted subnet (resurrection)
                was_deleted = prefix.tags.get('deleted_from_aws') is not None
                
                # Update tags with latest AWS data
                updated_tags = prefix.tags.copy()
                updated_tags.update({
                    'aws_subnet_id': subnet_data['subnet_id'],
                    'availability_zone': subnet_data['availability_zone'],
                    'state': subnet_data['state'],
                    'last_sync': datetime.utcnow().isoformat()
                })
                
                # Remove deletion markers if this subnet was previously deleted
                if was_deleted:
                    updated_tags.pop('deleted_from_aws', None)
                    updated_tags.pop('deletion_reason', None)
                    updated_tags['resurrected_at'] = datetime.utcnow().isoformat()
                    logger.info(f"Resurrected previously deleted subnet: {subnet_data['cidr_block']} (new subnet ID: {subnet_data['subnet_id']})")
                
                prefix.tags = updated_tags
                session.commit()
                
                if was_deleted:
                    logger.info(f"Subnet resurrection completed: {subnet_data['cidr_block']}")
                else:
                    logger.debug(f"Updated subnet prefix: {subnet_data['cidr_block']}")
                
                return was_deleted
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to update subnet prefix {subnet_data['cidr_block']}: {e}")
            return False
        finally:
            session.close()
    
    def _delete_subnet_prefix(self, prefix: Prefix):
        """Mark subnet prefix as deleted (soft delete)"""
        session = self.db_manager.get_session()
        try:
            # Query the prefix again in this session to ensure it's attached
            db_prefix = session.query(Prefix).filter(Prefix.prefix_id == prefix.prefix_id).first()
            if not db_prefix:
                logger.warning(f"Prefix {prefix.cidr} not found in database for deletion marking")
                return
                
            # Add deletion marker to tags instead of hard delete
            updated_tags = db_prefix.tags.copy()
            updated_tags.update({
                'deleted_from_aws': datetime.utcnow().isoformat(),
                'deletion_reason': 'aws_subnet_not_found'
            })
            db_prefix.tags = updated_tags
            session.commit()
            logger.info(f"Marked subnet prefix as deleted: {prefix.cidr}")
            
        except Exception as e:
            logger.error(f"Failed to mark subnet prefix as deleted {prefix.cidr}: {e}")
            session.rollback()
        finally:
            session.close()
    
    def run_sync_cycle(self):
        """Run a complete synchronization cycle"""
        logger.info("Starting AWS VPC subnet synchronization cycle")
        start_time = time.time()
        
        try:
            # Initialize AWS client
            self.initialize_aws_client()
            
            # Load VPC registry
            vpc_registry = self.load_vpc_registry()
            
            if not vpc_registry:
                logger.warning("No AWS VPCs found in registry. Skipping sync.")
                return
            
            # Sync each VPC
            total_vpcs = len(vpc_registry)
            successful_syncs = 0
            
            for key, vpc in vpc_registry.items():
                try:
                    logger.info(f"Syncing VPC: {vpc.provider_vpc_id} ({vpc.description})")
                    
                    # Fetch current subnets from AWS
                    aws_subnets, is_reachable = self.fetch_vpc_subnets(vpc.provider_vpc_id)
                    
                    if not is_reachable:
                        # VPC is unreachable - skip sync to preserve existing data
                        logger.info(f"VPC {vpc.provider_vpc_id} unreachable - skipped (existing subnets preserved)")
                        continue
                    
                    # Sync with database only if VPC is reachable
                    self.sync_vpc_subnets(vpc, aws_subnets)
                    successful_syncs += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync VPC {vpc.provider_vpc_id}: {e}")
            
            # Log summary
            duration = time.time() - start_time
            logger.info(f"Sync cycle completed: {successful_syncs}/{total_vpcs} VPCs synced in {duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Sync cycle failed: {e}")

def load_sync_config() -> SyncConfig:
    """Load synchronization configuration"""
    # Load VPC configuration from JSON
    data_loader = JSONDataLoader(data_dir='data')
    vpc_data = data_loader.load_vpc_data()
    
    # Filter AWS VPCs
    aws_vpcs = [vpc for vpc in vpc_data['vpcs'] if vpc['provider'] == 'aws']
    
    # Create config from environment variables
    return SyncConfig.from_env(aws_vpcs)

def main():
    """Main synchronization function"""
    logger.info("🚀 Starting AWS VPC Subnet Synchronization Service")
    
    try:
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Load configuration
        config = load_sync_config()
        logger.info(f"Loaded config: {len(config.vpc_configs)} VPCs, region: {config.aws_region}")
        
        # Initialize database connection
        database_url = os.getenv('DATABASE_URL', 'postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management')
        db_manager = DatabaseManager(database_url)
        
        # Wait for database to be ready
        for i in range(30):
            try:
                from sqlalchemy import text
                session = db_manager.get_session()
                session.execute(text("SELECT 1"))
                session.close()
                logger.info("✓ Database connection established")
                break
            except Exception as e:
                logger.info(f"Waiting for database... ({i+1}/30)")
                time.sleep(3)
        else:
            raise Exception("Could not connect to database")
        
        # Initialize sync service
        sync_service = AWSVPCSubnetSync(config, db_manager)
        
        # Check if this is a one-time run or continuous mode
        if os.getenv('SYNC_MODE', 'once') == 'continuous':
            logger.info(f"Running in continuous mode (interval: {config.sync_interval}s)")
            while True:
                sync_service.run_sync_cycle()
                time.sleep(config.sync_interval)
        else:
            logger.info("Running in one-time mode")
            sync_service.run_sync_cycle()
        
        logger.info("✅ AWS VPC Subnet Synchronization completed successfully")
        
    except KeyboardInterrupt:
        logger.info("🛑 Synchronization stopped by user")
    except Exception as e:
        logger.error(f"❌ Synchronization failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
