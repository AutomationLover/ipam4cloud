#!/bin/bash

echo "🚀 Starting Prefix Management Web Application"
echo "=============================================="

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
echo "This will start:"
echo "  - PostgreSQL database (port 5432)"
echo "  - FastAPI backend (port 8000)"
echo "  - Vue.js frontend (port 8080)"
echo "  - Demo data loader"
echo ""

# Start services in detached mode
docker-compose up -d postgres

echo "⏳ Waiting for database to be ready..."
sleep 10

# Start backend and frontend
docker-compose up -d backend frontend

echo "⏳ Waiting for services to start..."
sleep 15

# Run the demo data loader
echo "📊 Loading demo data..."
docker-compose run --rm app python main.py

echo ""
echo "🎉 Web application is ready!"
echo ""
echo "📱 Access the application:"
echo "   Frontend: http://localhost:8080"
echo "   Backend API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "🛠️  To stop the application:"
echo "   docker-compose down"
echo ""
echo "📊 To view logs:"
echo "   docker-compose logs -f [service_name]"
echo "   Services: postgres, backend, frontend"

