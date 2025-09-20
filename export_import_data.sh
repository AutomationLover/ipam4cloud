#!/bin/bash

# IPAM4Cloud Data Export/Import Script
# Usage: ./export_import_data.sh [export|import] [options]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Default values
ACTION=""
OUTPUT_DIR="exports"
MANIFEST_FILE=""
DATABASE_URL="${DATABASE_URL:-postgresql://prefix_user:prefix_pass@postgres:5432/prefix_management}"

# Function to show help
show_help() {
    echo "IPAM4Cloud Data Export/Import Tool"
    echo ""
    echo "Usage: $0 [export|import] [options]"
    echo ""
    echo "Commands:"
    echo "  export              Export all system data to JSON files"
    echo "  import              Import data from exported JSON files"
    echo ""
    echo "Export Options:"
    echo "  --output-dir DIR    Output directory for export files (default: exports)"
    echo ""
    echo "Import Options:"
    echo "  --manifest FILE     Manifest file from previous export (required)"
    echo ""
    echo "General Options:"
    echo "  --database-url URL  Database connection URL"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 export                                    # Export to ./exports/"
    echo "  $0 export --output-dir /backup/ipam         # Export to custom directory"
    echo "  $0 import --manifest exports/export_manifest_20241220_143022.json"
    echo ""
    echo "Data Types Exported/Imported:"
    echo "  📊 VRFs (Virtual Routing and Forwarding)"
    echo "  🌐 VPCs (Virtual Private Clouds)"
    echo "  📋 Manual Prefixes (User-defined IP ranges)"
    echo "  🔗 VPC Associations (VPC to Prefix mappings)"
    echo "  🌍 Public IP Addresses"
    echo ""
    echo "Export Files Created:"
    echo "  - vrfs_export_TIMESTAMP.json"
    echo "  - manual_prefixes_export_TIMESTAMP.json"
    echo "  - vpc_data_export_TIMESTAMP.json"
    echo "  - public_ips_export_TIMESTAMP.json"
    echo "  - export_manifest_TIMESTAMP.json (use this for import)"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        export|import)
            ACTION=$1
            shift
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --manifest)
            MANIFEST_FILE="$2"
            shift 2
            ;;
        --database-url)
            DATABASE_URL="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Validate action
if [ -z "$ACTION" ]; then
    print_error "Action required: export or import"
    show_help
    exit 1
fi

# Check if Docker containers are running
check_containers() {
    print_status "Checking if IPAM containers are running..."
    
    if ! docker compose -f containers/docker-compose.yml --env-file .env ps --services --filter "status=running" | grep -q "postgres"; then
        print_warning "Database container is not running"
        print_status "Starting containers..."
        ./manage.sh start
        sleep 5
    else
        print_success "Database container is running"
    fi
}

# Export function
do_export() {
    print_status "Starting data export..."
    print_status "Output directory: $OUTPUT_DIR"
    print_status "Database URL: ${DATABASE_URL//:*@/:***@}"  # Hide password in output
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    
    # Run export using Docker container
    print_status "Running export in container..."
    docker compose -f containers/docker-compose.yml --env-file .env exec app python data_export_import.py export \
        --output-dir "/app/$OUTPUT_DIR" \
        --database-url "$DATABASE_URL"
    
    if [ $? -eq 0 ]; then
        print_success "Export completed successfully!"
        print_status "Files exported to: $OUTPUT_DIR"
        
        # List exported files
        if [ -d "$OUTPUT_DIR" ]; then
            echo ""
            print_status "Exported files:"
            ls -la "$OUTPUT_DIR"/*.json 2>/dev/null | while read line; do
                echo "   $line"
            done
            
            # Find and highlight manifest file
            MANIFEST=$(ls "$OUTPUT_DIR"/export_manifest_*.json 2>/dev/null | head -1)
            if [ -n "$MANIFEST" ]; then
                echo ""
                print_success "Use this manifest file for import:"
                echo "   $MANIFEST"
            fi
        fi
    else
        print_error "Export failed!"
        exit 1
    fi
}

# Import function
do_import() {
    if [ -z "$MANIFEST_FILE" ]; then
        print_error "Manifest file is required for import"
        echo "Use --manifest /path/to/export_manifest_TIMESTAMP.json"
        exit 1
    fi
    
    if [ ! -f "$MANIFEST_FILE" ]; then
        print_error "Manifest file not found: $MANIFEST_FILE"
        exit 1
    fi
    
    print_status "Starting data import..."
    print_status "Manifest file: $MANIFEST_FILE"
    print_status "Database URL: ${DATABASE_URL//:*@/:***@}"
    
    print_warning "This will import data into the current database"
    print_warning "Existing data with the same IDs may be skipped or cause conflicts"
    
    # Ask for confirmation
    read -p "Continue with import? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Import cancelled"
        exit 0
    fi
    
    # Copy manifest file to container accessible location
    CONTAINER_MANIFEST="/app/$(basename "$MANIFEST_FILE")"
    docker compose -f containers/docker-compose.yml --env-file .env cp "$MANIFEST_FILE" app:"$CONTAINER_MANIFEST"
    
    # Run import using Docker container
    print_status "Running import in container..."
    docker compose -f containers/docker-compose.yml --env-file .env exec app python data_export_import.py import \
        --manifest "$CONTAINER_MANIFEST" \
        --database-url "$DATABASE_URL"
    
    if [ $? -eq 0 ]; then
        print_success "Import completed successfully!"
        print_status "You may want to restart the application to see the imported data"
        echo ""
        print_status "To restart the application:"
        echo "   ./manage.sh restart"
    else
        print_error "Import failed!"
        exit 1
    fi
}

# Main execution
print_status "IPAM4Cloud Data Export/Import Tool"
print_status "Action: $ACTION"

# Check containers
check_containers

# Execute action
case $ACTION in
    export)
        do_export
        ;;
    import)
        do_import
        ;;
    *)
        print_error "Unknown action: $ACTION"
        exit 1
        ;;
esac

print_success "Operation completed successfully! 🎉"
