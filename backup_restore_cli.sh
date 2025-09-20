#!/bin/bash

# Backup/Restore CLI for IPAM4Cloud
# Manages internal Docker backups with timeline functionality

set -e

DOCKER_COMPOSE="docker compose -f containers/docker-compose.yml --env-file .env"

show_help() {
    cat << EOF
🔄 IPAM Backup/Restore System

USAGE:
    $0 <command> [options]

COMMANDS:
    backup [description]     Create a new backup
    list                     List all backups
    restore <backup_id>      Restore from backup
    delete <backup_id>       Delete a backup
    details <backup_id>      Show backup details
    cleanup [keep_count]     Clean up old backups (default: keep 10)

EXAMPLES:
    $0 backup "Before major update"
    $0 list
    $0 restore 20250920_143022
    $0 delete 20250920_143022
    $0 details 20250920_143022
    $0 cleanup 5

NOTES:
    - Backups are stored inside Docker containers
    - Use for quick system snapshots and timeline restore
    - For PC exports, use pc_export_import_cli.sh instead
EOF
}

backup_create() {
    local description="$1"
    echo "🔄 Creating backup..."
    
    if [ -n "$description" ]; then
        $DOCKER_COMPOSE exec backend python /app/backup_restore.py backup --description "$description"
    else
        $DOCKER_COMPOSE exec backend python /app/backup_restore.py backup
    fi
}

backup_list() {
    echo "📋 Listing backups..."
    $DOCKER_COMPOSE exec backend python /app/backup_restore.py list
}

backup_restore() {
    local backup_id="$1"
    if [ -z "$backup_id" ]; then
        echo "❌ Error: Backup ID is required"
        echo "Usage: $0 restore <backup_id>"
        exit 1
    fi
    
    echo "🔄 Restoring from backup: $backup_id"
    echo "⚠️  This will replace all current data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $DOCKER_COMPOSE exec backend python /app/backup_restore.py restore --backup-id "$backup_id"
    else
        echo "❌ Restore cancelled"
    fi
}

backup_delete() {
    local backup_id="$1"
    if [ -z "$backup_id" ]; then
        echo "❌ Error: Backup ID is required"
        echo "Usage: $0 delete <backup_id>"
        exit 1
    fi
    
    echo "🗑️  Deleting backup: $backup_id"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        $DOCKER_COMPOSE exec backend python /app/backup_restore.py delete --backup-id "$backup_id"
    else
        echo "❌ Delete cancelled"
    fi
}

backup_details() {
    local backup_id="$1"
    if [ -z "$backup_id" ]; then
        echo "❌ Error: Backup ID is required"
        echo "Usage: $0 details <backup_id>"
        exit 1
    fi
    
    echo "📋 Backup details for: $backup_id"
    $DOCKER_COMPOSE exec backend python /app/backup_restore.py details --backup-id "$backup_id"
}

backup_cleanup() {
    local keep_count="${1:-10}"
    echo "🧹 Cleaning up old backups (keeping $keep_count recent)..."
    $DOCKER_COMPOSE exec backend python /app/backup_restore.py cleanup --keep "$keep_count"
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
    backup)
        backup_create "$2"
        ;;
    list)
        backup_list
        ;;
    restore)
        backup_restore "$2"
        ;;
    delete)
        backup_delete "$2"
        ;;
    details)
        backup_details "$2"
        ;;
    cleanup)
        backup_cleanup "$2"
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
