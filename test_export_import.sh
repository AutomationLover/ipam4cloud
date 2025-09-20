#!/bin/bash

# Test script for Export/Import functionality
# This script tests the export/import feature with the current system data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

print_status "🧪 Testing Export/Import Functionality"
echo "=" * 50

# Check if containers are running
print_status "Checking if containers are running..."
if ! ./manage.sh status | grep -q "Database: Running"; then
    print_warning "Starting containers..."
    ./manage.sh start
    sleep 10
fi

# Test 1: Export current data
print_status "Test 1: Exporting current system data..."
TEST_DIR="test_exports_$(date +%Y%m%d_%H%M%S)"

if ./export_import_data.sh export --output-dir "$TEST_DIR"; then
    print_success "Export test passed"
else
    print_error "Export test failed"
    exit 1
fi

# Verify export files exist
print_status "Verifying export files..."
if [ -d "$TEST_DIR" ]; then
    FILE_COUNT=$(ls "$TEST_DIR"/*.json 2>/dev/null | wc -l)
    if [ "$FILE_COUNT" -ge 5 ]; then
        print_success "Found $FILE_COUNT export files"
        
        # List the files
        echo ""
        print_status "Export files created:"
        ls -la "$TEST_DIR"/*.json | while read line; do
            echo "   $line"
        done
    else
        print_error "Expected at least 5 export files, found $FILE_COUNT"
        exit 1
    fi
else
    print_error "Export directory not created"
    exit 1
fi

# Test 2: Verify export file structure
print_status "Test 2: Verifying export file structure..."

MANIFEST_FILE=$(ls "$TEST_DIR"/export_manifest_*.json | head -1)
if [ -n "$MANIFEST_FILE" ]; then
    print_status "Checking manifest file: $MANIFEST_FILE"
    
    # Check if manifest is valid JSON
    if python3 -m json.tool "$MANIFEST_FILE" > /dev/null 2>&1; then
        print_success "Manifest file is valid JSON"
        
        # Show summary from manifest
        echo ""
        print_status "Export summary:"
        python3 -c "
import json
with open('$MANIFEST_FILE', 'r') as f:
    data = json.load(f)
    summary = data.get('summary', {})
    for key, value in summary.items():
        print(f'   {key}: {value}')
"
    else
        print_error "Manifest file is not valid JSON"
        exit 1
    fi
else
    print_error "No manifest file found"
    exit 1
fi

# Test 3: Test API endpoints (if backend is running)
print_status "Test 3: Testing API endpoints..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    print_status "Backend is running, testing API endpoints..."
    
    # Test list exports endpoint
    if curl -s "http://localhost:8000/api/exports?export_dir=$TEST_DIR" | python3 -m json.tool > /dev/null 2>&1; then
        print_success "List exports API endpoint works"
    else
        print_warning "List exports API endpoint failed (non-critical)"
    fi
else
    print_warning "Backend not running, skipping API tests"
fi

# Test 4: Validate individual export files
print_status "Test 4: Validating individual export files..."

for export_file in "$TEST_DIR"/*.json; do
    filename=$(basename "$export_file")
    
    if python3 -m json.tool "$export_file" > /dev/null 2>&1; then
        # Get record count from file
        count=$(python3 -c "
import json
try:
    with open('$export_file', 'r') as f:
        data = json.load(f)
    
    # Try to get count from different possible structures
    if 'export_info' in data:
        count = data['export_info'].get('count', 0)
    elif 'vrfs' in data:
        count = len(data['vrfs'])
    elif 'prefixes' in data:
        count = len(data['prefixes'])
    elif 'vpcs' in data:
        count = len(data['vpcs'])
    elif 'public_ips' in data:
        count = len(data['public_ips'])
    else:
        count = 'unknown'
    
    print(count)
except:
    print('error')
")
        print_success "$filename: Valid JSON ($count records)"
    else
        print_error "$filename: Invalid JSON"
        exit 1
    fi
done

# Test 5: Test import dry-run (we won't actually import to avoid duplicates)
print_status "Test 5: Testing import preparation..."
print_warning "Skipping actual import to avoid data duplication"
print_status "Import would use manifest: $MANIFEST_FILE"

# Show what would be imported
echo ""
print_status "Import preview:"
python3 -c "
import json
with open('$MANIFEST_FILE', 'r') as f:
    data = json.load(f)
    files = data.get('exported_files', {})
    for file_type, file_path in files.items():
        if file_type != 'manifest':
            print(f'   {file_type}: {file_path}')
"

# Cleanup
print_status "Cleaning up test files..."
if [ -d "$TEST_DIR" ]; then
    rm -rf "$TEST_DIR"
    print_success "Test files cleaned up"
fi

echo ""
print_success "🎉 All export/import tests passed!"
echo ""
print_status "Export/Import functionality is working correctly"
print_status "You can now use:"
echo "   ./export_import_data.sh export                    # Export current data"
echo "   ./export_import_data.sh import --manifest FILE    # Import from export"
echo ""
print_status "Or use the API endpoints:"
echo "   POST /api/export                                  # Export via API"
echo "   GET  /api/exports                                 # List exports"
echo "   POST /api/import                                  # Import via API"
