#!/bin/bash
set -e

# Advanced Configuration Generator
# Generates JSON configuration files from templates using environment variables
# Supports default values using ${VAR:-default} syntax

echo "🔧 Advanced Configuration Generator"
echo "=================================="

# Load .env file if it exists
if [ -f ".env" ]; then
    echo "📁 Loading environment variables from .env file..."
    # Export all variables from .env file
    set -a
    source .env
    set +a
    echo "✅ Environment variables loaded"
else
    echo "⚠️  No .env file found, using system environment variables only"
fi

# Function to substitute environment variables with default value support
substitute_env_vars() {
    local template_file="$1"
    local output_file="$2"
    
    echo "🔄 Processing: $template_file -> $output_file"
    
    # Create temporary file for processing
    local temp_file=$(mktemp)
    
    # Set default values for demo variables if not set
    export DEMO_AWS_ACCOUNT_ID="${DEMO_AWS_ACCOUNT_ID:-123456789012}"
    export DEMO_AWS_REGION="${DEMO_AWS_REGION:-us-east-1}"
    
    # Use envsubst to substitute all environment variables
    envsubst < "$template_file" > "$temp_file"
    
    # Validate JSON only for .json files
    if [[ "$output_file" == *.json ]]; then
        if python3 -m json.tool "$temp_file" > /dev/null 2>&1; then
            mv "$temp_file" "$output_file"
            echo "✅ Generated: $output_file"
            return 0
        else
            echo "❌ Invalid JSON generated for $output_file"
            cat "$temp_file"
            rm -f "$temp_file"
            return 1
        fi
    else
        # For non-JSON files, just move the file
        mv "$temp_file" "$output_file"
        echo "✅ Generated: $output_file"
        return 0
    fi
}

# Function to show environment variable status
show_env_status() {
    echo ""
    echo "📊 Environment Variable Status:"
    echo "=============================="
    
    # Required variables
    echo "Required Variables:"
    for var in AWS_ACCOUNT_ID AWS_DEFAULT_REGION TEST_VPC_1_ID TEST_VPC_2_ID; do
        if [ -n "${!var}" ]; then
            echo "  ✅ $var = ${!var}"
        else
            echo "  ❌ $var = (not set)"
        fi
    done
    
    # Optional variables with defaults
    echo ""
    echo "Optional Variables (with defaults):"
    for var in DEMO_AWS_ACCOUNT_ID DEMO_AWS_REGION DEFAULT_VRF_ID; do
        if [ -n "${!var}" ]; then
            echo "  ✅ $var = ${!var}"
        else
            echo "  ⚠️  $var = (using default)"
        fi
    done
    echo ""
}

# Show current environment status
show_env_status

# Define template mappings (generate files with .gen.json extension to indicate they're generated)
templates=(
    "containers/app/data/vpc_data.template.json:containers/app/data/vpc_data.gen.json"
    "containers/app/data/manual_prefixes.template.json:containers/app/data/manual_prefixes.gen.json"
)

# Process each template
success_count=0
total_count=${#templates[@]}

for template_mapping in "${templates[@]}"; do
    template_file="${template_mapping%:*}"
    output_file="${template_mapping#*:}"
    
    if [ ! -f "$template_file" ]; then
        echo "⚠️  Template not found: $template_file"
        continue
    fi
    
    if substitute_env_vars "$template_file" "$output_file"; then
        ((success_count++))
    fi
done

# Create public_ips.gen.json from vpc_data.gen.json if it doesn't exist as a template
if [ -f "containers/app/data/vpc_data.gen.json" ]; then
    echo "🔄 Extracting public IPs to separate file..."
    python3 -c "
import json
with open('containers/app/data/vpc_data.gen.json', 'r') as f:
    data = json.load(f)
public_ips = {'public_ips': data.get('public_ips', [])}
with open('containers/app/data/public_ips.gen.json', 'w') as f:
    json.dump(public_ips, f, indent=2)
print('✅ Generated: containers/app/data/public_ips.gen.json')
"
    ((success_count++))
    ((total_count++))
fi

# Summary
echo ""
echo "📊 Generation Summary:"
echo "===================="
echo "Generated: $success_count/$total_count files"

if [ $success_count -eq $total_count ]; then
    echo "🎉 All configuration files generated successfully!"
    echo ""
    echo "📁 Generated files (git-ignored):"
    for template_mapping in "${templates[@]}"; do
        output_file="${template_mapping#*:}"
        if [ -f "$output_file" ]; then
            echo "  - $output_file"
        fi
    done
    if [ -f "containers/app/data/public_ips.gen.json" ]; then
        echo "  - containers/app/data/public_ips.gen.json"
    fi
    if [ -f ".aws-local/vpc_details.json" ]; then
        echo "  - .aws-local/vpc_details.json"
    fi
    if [ -f ".aws-local/commands.sh" ]; then
        echo "  - .aws-local/commands.sh"
    fi
    echo ""
    echo "🚀 Ready to start the application!"
    exit 0
else
    echo "❌ Some configuration files failed to generate"
    echo ""
    echo "💡 Tips:"
    echo "  - Check that all required environment variables are set"
    echo "  - Run: cp env.example .env && nano .env"
    echo "  - Or run: ./setup_env.sh"
    exit 1
fi
