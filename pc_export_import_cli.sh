#!/bin/bash

# PC Export/Import CLI for IPAM4Cloud
# Manages data export to PC and import from PC folders

set -e

DOCKER_COMPOSE="docker compose -f containers/docker-compose.yml --env-file .env"

show_help() {
    cat << EOF
📁 IPAM PC Export/Import System

USAGE:
    $0 <command> [options]

COMMANDS:
    export <pc_folder> [export_name]    Export data to PC folder
    import <pc_folder>                  Import data from PC folder
    scan <pc_folder>                    Scan PC folder for exports
    validate <pc_folder>                Validate PC folder export

EXAMPLES:
    $0 export /Users/john/ipam-backup "my_export"
    $0 export C:\\Users\\john\\ipam-backup
    $0 import /Users/john/ipam-backup/my_export
    $0 scan /Users/john/ipam-backup
    $0 validate /Users/john/ipam-backup/my_export

NOTES:
    - PC folders must be accessible from your system
    - Use full absolute paths for best results
    - For internal Docker backups, use backup_restore_cli.sh instead
    - Windows users: Use double backslashes in paths or forward slashes

EXAMPLES BY OS:
    macOS/Linux:
        $0 export /Users/username/Documents/ipam-exports
        $0 import /Users/username/Documents/ipam-exports/export_20250920
    
    Windows:
        $0 export C:\\\\Users\\\\username\\\\Documents\\\\ipam-exports
        $0 export C:/Users/username/Documents/ipam-exports
EOF
}

pc_export() {
    local pc_folder="$1"
    local export_name="$2"
    
    if [ -z "$pc_folder" ]; then
        echo "❌ Error: PC folder path is required"
        echo "Usage: $0 export <pc_folder> [export_name]"
        exit 1
    fi
    
    echo "📤 Exporting to PC folder: $pc_folder"
    
    if [ -n "$export_name" ]; then
        $DOCKER_COMPOSE exec backend python /app/pc_export_import.py export --pc-folder "$pc_folder" --export-name "$export_name"
    else
        $DOCKER_COMPOSE exec backend python /app/pc_export_import.py export --pc-folder "$pc_folder"
    fi
}

pc_import() {
    local pc_folder="$1"
    
    if [ -z "$pc_folder" ]; then
        echo "❌ Error: PC folder path is required"
        echo "Usage: $0 import <pc_folder>"
        exit 1
    fi
    
    echo "📥 Importing from PC folder: $pc_folder"
    echo "⚠️  This will add/update data in the system!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $DOCKER_COMPOSE exec backend python /app/pc_export_import.py import --pc-folder "$pc_folder"
    else
        echo "❌ Import cancelled"
    fi
}

pc_scan() {
    local pc_folder="$1"
    
    if [ -z "$pc_folder" ]; then
        echo "❌ Error: PC folder path is required"
        echo "Usage: $0 scan <pc_folder>"
        exit 1
    fi
    
    echo "🔍 Scanning PC folder: $pc_folder"
    $DOCKER_COMPOSE exec backend python /app/pc_export_import.py scan --pc-folder "$pc_folder"
}

pc_validate() {
    local pc_folder="$1"
    
    if [ -z "$pc_folder" ]; then
        echo "❌ Error: PC folder path is required"
        echo "Usage: $0 validate <pc_folder>"
        exit 1
    fi
    
    echo "🔍 Validating PC folder: $pc_folder"
    $DOCKER_COMPOSE exec backend python /app/pc_export_import.py validate --pc-folder "$pc_folder"
}

# Check if Docker Compose is available
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    exit 1
fi

# Check if services are running
if ! $DOCKER_COMPOSE ps backend | grep -q "Up"; then
    echo "❌ Error: Backend service is not running"
    echo "Start services with: ./manage.sh start"
    exit 1
fi

# Parse command
case "${1:-}" in
    export)
        pc_export "$2" "$3"
        ;;
    import)
        pc_import "$2"
        ;;
    scan)
        pc_scan "$2"
        ;;
    validate)
        pc_validate "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    "")
        echo "❌ Error: No command specified"
        echo ""
        show_help
        exit 1
        ;;
    *)
        echo "❌ Error: Unknown command '$1'"
        echo ""
        show_help
        exit 1
        ;;
esac
