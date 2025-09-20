#!/bin/bash
set -e

# Environment Setup Script for ipam4cloud
# This script helps users set up their environment configuration

echo "🚀 ipam4cloud Environment Setup"
echo "================================"

# Check if .env already exists
if [ -f ".env" ]; then
    echo "⚠️  .env file already exists. Do you want to recreate it? (y/N)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "Using existing .env file. You can edit it manually if needed."
        echo "Run: nano .env"
        exit 0
    fi
fi

# Copy example file
if [ ! -f "env.example" ]; then
    echo "❌ env.example file not found. Please run this script from the project root."
    exit 1
fi

cp env.example .env
echo "✅ Created .env file from template"

# Function to prompt for value
prompt_for_value() {
    local var_name="$1"
    local description="$2"
    local default_value="$3"
    local current_value
    
    current_value=$(grep "^${var_name}=" .env | cut -d'=' -f2)
    
    if [ -n "$default_value" ]; then
        echo -n "$description [$default_value]: "
    else
        echo -n "$description: "
    fi
    
    read -r user_input
    
    if [ -z "$user_input" ] && [ -n "$default_value" ]; then
        user_input="$default_value"
    fi
    
    if [ -n "$user_input" ]; then
        # Use sed to replace the value in .env file
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^${var_name}=.*|${var_name}=${user_input}|" .env
        else
            # Linux
            sed -i "s|^${var_name}=.*|${var_name}=${user_input}|" .env
        fi
    fi
}

echo ""
echo "📝 Please provide your AWS configuration:"
echo ""

# Get AWS Account ID
echo "🔍 Attempting to detect AWS Account ID..."
if command -v aws &> /dev/null; then
    aws_account_id=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "")
    if [ -n "$aws_account_id" ]; then
        echo "✅ Detected AWS Account ID: $aws_account_id"
        prompt_for_value "AWS_ACCOUNT_ID" "AWS Account ID" "$aws_account_id"
    else
        prompt_for_value "AWS_ACCOUNT_ID" "AWS Account ID (e.g., 012345678901)" ""
    fi
else
    prompt_for_value "AWS_ACCOUNT_ID" "AWS Account ID (e.g., 012345678901)" ""
fi

# Get AWS Region
echo ""
echo "🌍 AWS Region configuration:"
aws_region=""
if command -v aws &> /dev/null; then
    aws_region=$(aws configure get region 2>/dev/null || echo "")
    if [ -n "$aws_region" ]; then
        echo "✅ Detected AWS Region: $aws_region"
    fi
fi
prompt_for_value "AWS_DEFAULT_REGION" "AWS Region" "${aws_region:-us-east-2}"

echo ""
echo "🏗️  VPC Configuration:"
echo "If you don't have VPCs yet, you can create them after this setup."
echo ""

prompt_for_value "TEST_VPC_1_ID" "Test VPC 1 ID (e.g., vpc-0123456789abcdef0)" ""
prompt_for_value "TEST_VPC_1_CIDR" "Test VPC 1 CIDR" "10.101.0.0/16"
prompt_for_value "TEST_VPC_1_NAME" "Test VPC 1 Name" "ipam4cloud-test-vpc-1"

echo ""
prompt_for_value "TEST_VPC_2_ID" "Test VPC 2 ID (e.g., vpc-0123456789abcdef1)" ""
prompt_for_value "TEST_VPC_2_CIDR" "Test VPC 2 CIDR" "10.102.0.0/16"  
prompt_for_value "TEST_VPC_2_NAME" "Test VPC 2 Name" "ipam4cloud-test-vpc-2"

echo ""
echo "⚙️  Optional: Advanced Configuration"
echo "You can press Enter to use defaults for these settings:"
echo ""

prompt_for_value "SYNC_INTERVAL" "Sync interval in seconds" "300"
prompt_for_value "AWS_PAGE_SIZE" "AWS API page size" "100"
prompt_for_value "MAX_SUBNETS_PER_VPC" "Max subnets per VPC" "1000"

echo ""
echo "✅ Environment configuration completed!"
echo ""
echo "📄 Your configuration has been saved to .env"
echo ""

# Check if VPC IDs are set
vpc1_id=$(grep "^TEST_VPC_1_ID=" .env | cut -d'=' -f2)
vpc2_id=$(grep "^TEST_VPC_2_ID=" .env | cut -d'=' -f2)

if [ -z "$vpc1_id" ] || [ -z "$vpc2_id" ]; then
    echo "⚠️  VPC IDs are not set. You can:"
    echo "   1. Create VPCs manually using AWS Console or CLI"
    echo "   2. Use the commands in preparation/aws_commands.sh"
    echo "   3. Update the VPC IDs in .env later"
    echo ""
fi

echo "🔄 Next steps:"
echo "   1. Generate configuration files: python3 generate_config.py"
echo "   2. Start the application: docker-compose up -d"
echo "   3. Visit http://localhost:8080 to use the application"
echo ""
echo "📚 For detailed setup instructions, see: ENV_SETUP.md"
