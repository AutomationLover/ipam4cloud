#!/bin/bash

# AWS CLI Commands for ipam4cloud VPC Management
# Template version - replace ${VARIABLES} with actual values
# Account: ${AWS_ACCOUNT_ID}
# Region: ${AWS_DEFAULT_REGION}

echo "=== AWS VPC Management Commands for ipam4cloud ==="
echo "Account: ${AWS_ACCOUNT_ID}"
echo "Region: ${AWS_DEFAULT_REGION}"
echo ""

# Check current AWS identity
echo "1. Verify AWS Identity:"
echo "aws sts get-caller-identity"
echo ""

# Create VPCs
echo "2. Create Test VPCs:"
echo "aws ec2 create-vpc --cidr-block ${TEST_VPC_1_CIDR} --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=${TEST_VPC_1_NAME}}]'"
echo "aws ec2 create-vpc --cidr-block ${TEST_VPC_2_CIDR} --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=${TEST_VPC_2_NAME}}]'"
echo ""

# Describe VPCs
echo "3. Describe VPCs:"
aws ec2 describe-vpcs --vpc-ids ${TEST_VPC_1_ID} ${TEST_VPC_2_ID} \
  --query 'Vpcs[*].{VpcId:VpcId,CidrBlock:CidrBlock,State:State,Tags:Tags}' \
  --output table
echo ""

# List subnets in VPCs
echo "4. List Subnets (run these commands):"
echo "aws ec2 describe-subnets --filters \"Name=vpc-id,Values=${TEST_VPC_1_ID}\""
echo "aws ec2 describe-subnets --filters \"Name=vpc-id,Values=${TEST_VPC_2_ID}\""
echo ""

# Create example subnets
echo "5. Create Example Subnets:"
echo "aws ec2 create-subnet --vpc-id ${TEST_VPC_1_ID} --cidr-block 10.101.100.0/24 --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ipam4cloud-test-subnet-100}]'"
echo "aws ec2 create-subnet --vpc-id ${TEST_VPC_2_ID} --cidr-block 10.102.200.0/24 --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ipam4cloud-test-subnet-200}]'"
echo ""

# Cleanup commands (commented out for safety)
echo "6. Cleanup Commands (uncomment to use):"
echo "# aws ec2 delete-vpc --vpc-id ${TEST_VPC_1_ID}"
echo "# aws ec2 delete-vpc --vpc-id ${TEST_VPC_2_ID}"
