#!/bin/bash

# Test AWS VPC Subnet Synchronization
# This script tests the AWS sync functionality

echo "🧪 Testing AWS VPC Subnet Synchronization"
echo "=============================================="

# Set working directory
cd "$(dirname "$0")"

echo "📋 Current working directory: $(pwd)"
echo "📋 AWS Region: ${AWS_DEFAULT_REGION:-us-east-2}"
echo "📋 Database URL: ${DATABASE_URL:-postgresql://prefix_user:prefix_pass@localhost:5432/prefix_management}"

echo ""
echo "1️⃣ Testing AWS CLI access..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    echo "✅ AWS CLI access confirmed"
    aws sts get-caller-identity | grep Account
else
    echo "❌ AWS CLI access failed. Please configure AWS credentials."
    exit 1
fi

echo ""
echo "2️⃣ Checking VPC access..."
aws ec2 describe-vpcs --vpc-ids vpc-0123456789abcdef0 vpc-0123456789abcdef1 --query 'Vpcs[*].[VpcId,CidrBlock,Tags[?Key==`Name`].Value|[0]]' --output table

echo ""
echo "3️⃣ Testing database connection..."
if command -v docker &> /dev/null && docker compose -f containers/docker-compose.yml ps postgres | grep -q "Up"; then
    echo "✅ Database is running via Docker"
else
    echo "⚠️  Database status unknown - ensure PostgreSQL is accessible"
fi

echo ""
echo "4️⃣ Running AWS sync test..."
export SYNC_MODE=once
./run_aws_sync.sh

echo ""
echo "5️⃣ Checking sync results..."
echo "Check the web interface at:"
echo "   📱 VPCs: http://localhost:8080/vpcs"
echo "   📱 Prefixes: http://localhost:8080/prefixes"

echo ""
echo "6️⃣ Checking logs..."
if [ -f "app/logs/aws_sync.log" ]; then
    echo "📋 Recent sync log entries:"
    tail -10 app/logs/aws_sync.log
else
    echo "⚠️  No sync log file found yet"
fi

echo ""
echo "=============================================="
echo "🎉 AWS sync test completed!"
echo "Review the output above and check the web interface to verify results."
