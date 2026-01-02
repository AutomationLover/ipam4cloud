#!/bin/bash

# Prefix Management System Management Script
# Usage: ./manage.sh [command] [options]

set -e  # Exit on any error

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

# Check if .env file exists, create from env.example if not
if [ ! -f .env ]; then
    if [ -f env.example ]; then
        print_warning ".env file not found. Creating from env.example..."
        cp env.example .env
        print_success ".env file created"
    else
        print_error ".env file not found and env.example does not exist!"
        exit 1
    fi
fi

# Check for --install-compose flag early (before Docker Compose detection)
INSTALL_COMPOSE=false
for arg in "$@"; do
    if [ "$arg" = "--install-compose" ]; then
        INSTALL_COMPOSE=true
        break
    fi
done

# Docker Compose command with env file
# Try docker compose (V2) first, fallback to docker-compose (V1)
DOCKER_COMPOSE=""

# Check if docker is installed
if ! command -v docker >/dev/null 2>&1; then
    print_error "Docker is not installed or not in PATH!"
    print_error "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Try Docker Compose V2 (docker compose as plugin) - try multiple ways
if docker compose version >/dev/null 2>&1; then
    # Docker Compose V2 (newer syntax) - version check passed
    DOCKER_COMPOSE="docker compose --file containers/docker-compose.yml"
    if [ -f .env ]; then
        DOCKER_COMPOSE="$DOCKER_COMPOSE --env-file .env"
    fi
elif docker compose ps >/dev/null 2>&1; then
    # Docker Compose V2 - try ps command instead of version
    DOCKER_COMPOSE="docker compose --file containers/docker-compose.yml"
    if [ -f .env ]; then
        DOCKER_COMPOSE="$DOCKER_COMPOSE --env-file .env"
    fi
elif docker compose >/dev/null 2>&1 2>&1; then
    # Docker Compose V2 - basic check (might show help)
    DOCKER_COMPOSE="docker compose --file containers/docker-compose.yml"
    if [ -f .env ]; then
        DOCKER_COMPOSE="$DOCKER_COMPOSE --env-file .env"
    fi
# Try Docker Compose V1 (standalone docker-compose)
elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    # Docker Compose V1 (older syntax)
    DOCKER_COMPOSE="docker-compose --file containers/docker-compose.yml"
    # For V1, we need to source .env file manually
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
    fi
else
    print_error "Docker Compose is not installed or not available!"
    print_error ""
    print_error "Docker version detected:"
    docker --version 2>&1 || echo "  Docker not found"
    print_error ""
    
    if [ "$INSTALL_COMPOSE" = true ]; then
        print_status "Installing docker-compose-plugin (--install-compose flag detected)..."
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update
            sudo apt-get install -y docker-compose-plugin
            print_success "Docker Compose plugin installed!"
            print_status "Verifying installation..."
            if docker compose version >/dev/null 2>&1; then
                DOCKER_COMPOSE="docker compose --file containers/docker-compose.yml"
                if [ -f .env ]; then
                    DOCKER_COMPOSE="$DOCKER_COMPOSE --env-file .env"
                fi
                print_success "Docker Compose is now available!"
            else
                print_error "Installation completed but docker compose still not working."
                print_error "Please try: docker compose version"
                exit 1
            fi
        else
            print_error "apt-get not found. Please install Docker Compose manually:"
            echo "  sudo apt-get update"
            echo "  sudo apt-get install docker-compose-plugin"
            exit 1
        fi
    else
        print_warning "Would you like to install Docker Compose plugin automatically? (y/n)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            print_status "Installing docker-compose-plugin..."
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update
                sudo apt-get install -y docker-compose-plugin
                print_success "Docker Compose plugin installed!"
                print_status "Verifying installation..."
                if docker compose version >/dev/null 2>&1; then
                    DOCKER_COMPOSE="docker compose --file containers/docker-compose.yml"
                    if [ -f .env ]; then
                        DOCKER_COMPOSE="$DOCKER_COMPOSE --env-file .env"
                    fi
                    print_success "Docker Compose is now available!"
                else
                    print_error "Installation completed but docker compose still not working."
                    print_error "Please try: docker compose version"
                    exit 1
                fi
            else
                print_error "apt-get not found. Please install Docker Compose manually:"
                echo "  sudo apt-get update"
                echo "  sudo apt-get install docker-compose-plugin"
                exit 1
            fi
        else
            print_error "Installation cancelled."
            print_error ""
            print_error "To install Docker Compose plugin manually (recommended for Docker 20.10+):"
            echo "  sudo apt-get update"
            echo "  sudo apt-get install docker-compose-plugin"
            echo ""
            print_error "Or use the --install-compose flag to install automatically:"
            echo "  ./manage.sh start --install-compose"
            echo ""
            print_error "Or install standalone docker-compose (V1):"
            echo "  sudo apt-get install docker-compose"
            echo ""
            print_error "After installation, verify with:"
            echo "  docker compose version"
            echo "  # or"
            echo "  docker-compose version"
            exit 1
        fi
    fi
fi

# Function to show help
show_help() {
    echo "IPAM4Cloud Management Script - Dual Portal Setup"
    echo ""
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  start [--clean]     Start the system (optionally with clean database)"
    echo "  stop                Stop all containers"
    echo "  restart [--clean]   Restart the system (optionally with clean database)"
    echo "  clean               Clean database only (remove volumes)"
    echo "  logs [service]      Show logs (optionally for specific service)"
    echo "  status              Show container status"
    echo "  reset               Complete reset (stop, clean, start)"
    echo ""
    echo "Dual Portal Services:"
    echo "  🔧 Admin Portal:    http://localhost:8080 (Full CRUD operations)"
    echo "  👀 Read-Only Portal: http://localhost:8081 (Query-only access)"
    echo "  🔧 Backend API:     http://localhost:8000"
    echo "  🗄️  Database:       localhost:5432"
    echo ""
    echo "Options:"
    echo "  --clean             Remove all database volumes (fresh start)"
    echo "  --install-compose   Automatically install docker-compose-plugin if missing"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start            # Start with existing data"
    echo "  $0 start --clean    # Start with fresh database"
    echo "  $0 restart --clean  # Restart with fresh database"
    echo "  $0 logs admin-frontend     # Show admin portal logs"
    echo "  $0 logs readonly-frontend  # Show readonly portal logs"
    echo "  $0 reset            # Complete fresh start"
}

# Function to start containers
start_containers() {
    local clean_db=$1
    
    print_status "Starting Prefix Management System..."
    
    if [ "$clean_db" = true ]; then
        print_warning "Cleaning database (removing all volumes and data)..."
        $DOCKER_COMPOSE down -v --remove-orphans 2>/dev/null || true
        print_success "Database cleaned"
    fi
    
    # Remove any existing containers with conflicting names
    print_status "Removing any existing containers..."
    existing_containers=$(docker ps -a --filter "name=prefix_" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$existing_containers" ]; then
        echo "$existing_containers" | xargs docker rm -f 2>/dev/null || true
    fi
    
    print_status "Starting containers..."
    $DOCKER_COMPOSE up -d
    
    print_success "Containers started!"
    print_status "Services available at:"
    echo "  🔧 Admin Portal: http://localhost:8080"
    echo "  👀 Read-Only Portal: http://localhost:8081"
    echo "  🔧 Backend API: http://localhost:8000"
    echo "  🗄️  Database: localhost:5432"
}

# Function to stop containers
stop_containers() {
    print_status "Stopping containers..."
    $DOCKER_COMPOSE down --remove-orphans
    print_success "Containers stopped"
}

# Function to show logs
show_logs() {
    local service=$1
    if [ -n "$service" ]; then
        print_status "Showing logs for $service..."
        $DOCKER_COMPOSE logs -f "$service"
    else
        print_status "Showing logs for all services..."
        $DOCKER_COMPOSE logs -f
    fi
}

# Function to show status
show_status() {
    print_status "Container status:"
    $DOCKER_COMPOSE ps
    echo ""
    print_status "Service health:"
    
    # Check if containers are running
    if $DOCKER_COMPOSE ps --services --filter "status=running" | grep -q "postgres"; then
        echo "  🗄️  Database: Running"
    else
        echo "  🗄️  Database: Stopped"
    fi
    
    if $DOCKER_COMPOSE ps --services --filter "status=running" | grep -q "backend"; then
        echo "  🔧 Backend: Running"
    else
        echo "  🔧 Backend: Stopped"
    fi
    
    if $DOCKER_COMPOSE ps --services --filter "status=running" | grep -q "admin-frontend"; then
        echo "  🔧 Admin Portal: Running (http://localhost:8080)"
    else
        echo "  🔧 Admin Portal: Stopped"
    fi
    
    if $DOCKER_COMPOSE ps --services --filter "status=running" | grep -q "readonly-frontend"; then
        echo "  👀 Read-Only Portal: Running (http://localhost:8081)"
    else
        echo "  👀 Read-Only Portal: Stopped"
    fi
    
    if $DOCKER_COMPOSE ps --services --filter "status=running" | grep -q "app"; then
        echo "  📊 Demo App: Running"
    else
        echo "  📊 Demo App: Stopped"
    fi
}

# Function to clean database
clean_database() {
    print_warning "Cleaning database (removing volumes)..."
    $DOCKER_COMPOSE down -v --remove-orphans
    # Also remove any orphaned containers
    existing_containers=$(docker ps -a --filter "name=prefix_" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$existing_containers" ]; then
        echo "$existing_containers" | xargs docker rm -f 2>/dev/null || true
    fi
    print_success "Database cleaned"
}

# Function to reset everything
reset_system() {
    print_warning "Performing complete system reset..."
    $DOCKER_COMPOSE down -v --remove-orphans
    # Remove any orphaned containers
    existing_containers=$(docker ps -a --filter "name=prefix_" --format "{{.Names}}" 2>/dev/null || true)
    if [ -n "$existing_containers" ]; then
        echo "$existing_containers" | xargs docker rm -f 2>/dev/null || true
    fi
    print_status "Starting fresh system..."
    $DOCKER_COMPOSE up -d
    print_success "System reset complete!"
}

# Parse command line arguments
COMMAND=""
CLEAN_DB=false

while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|clean|logs|status|reset)
            COMMAND=$1
            shift
            ;;
        --clean)
            CLEAN_DB=true
            shift
            ;;
        --install-compose)
            # Already handled at the top, just skip
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            if [ "$COMMAND" = "logs" ] && [ -z "$2" ]; then
                # This is a service name for logs
                SERVICE_NAME=$1
                shift
            else
                print_error "Unknown option: $1"
                echo "Use -h or --help for usage information"
                exit 1
            fi
            ;;
    esac
done

# Default command if none provided
if [ -z "$COMMAND" ]; then
    COMMAND="start"
fi

# Execute command
case $COMMAND in
    start)
        start_containers $CLEAN_DB
        ;;
    stop)
        stop_containers
        ;;
    restart)
        stop_containers
        start_containers $CLEAN_DB
        ;;
    clean)
        clean_database
        ;;
    logs)
        show_logs "$SERVICE_NAME"
        ;;
    status)
        show_status
        ;;
    reset)
        reset_system
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac

