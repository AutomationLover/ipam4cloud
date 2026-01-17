# General Terraform variables file
# This file is gitignored and contains your actual values
#
# IMPORTANT: Also ensure network.auto.tfvars exists with your VPC and subnet IDs


# Project Configuration
project_name = "ipam4cloud"
environment = "dev"

# Instance Configuration
instance_type = "t3.xlarge"  # Adjust based on your needs
root_volume_size = 50

# Repository
repository_url = "https://github.com/AutomationLover/ipam4cloud.git"

# Key Pair Configuration
# By default, Terraform will automatically generate a new SSH key pair.
# The keys will be saved locally as:
# - ${project_name}-${environment}-allinone-deployer-key (private key)
# - ${project_name}-${environment}-allinone-deployer-key.pub (public key)
# Example: ipam4cloud-dev-allinone-deployer-key
#
# If you want to use an existing AWS key pair instead, set:
# create_key_pair = false
# existing_key_name = "your-existing-key-pair-name"
#
# Note: create_key_pair defaults to true, so no need to set it unless you want to use an existing key
