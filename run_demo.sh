#!/bin/bash

echo "🚀 Starting Prefix Management System Demo"
echo "=========================================="

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "✓ Docker and docker-compose are available"

# Clean up any existing containers
echo "🧹 Cleaning up existing containers..."
docker-compose down -v 2>/dev/null

# Build and start the containers
echo "🏗️  Building and starting containers..."
docker-compose up --build --abort-on-container-exit

# Show final status
echo ""
echo "📊 Final container status:"
docker-compose ps

echo ""
echo "🎉 Demo completed! To run again:"
echo "   cd containers/"
echo "   ./run_demo.sh"
echo ""
echo "To explore the database manually:"
echo "   docker-compose up -d postgres"
echo "   docker-compose exec postgres psql -U prefix_user -d prefix_management"

