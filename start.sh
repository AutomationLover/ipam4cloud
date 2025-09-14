#!/bin/bash

# Prefix Management System Startup Script
# Usage: ./start.sh [--clean]

CLEAN_DB=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --clean)
      CLEAN_DB=true
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [--clean]"
      echo ""
      echo "Options:"
      echo "  --clean    Start with a fresh database (removes all existing data)"
      echo "  -h, --help Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option $1"
      echo "Use -h or --help for usage information"
      exit 1
      ;;
  esac
done

echo "🚀 Starting Prefix Management System..."

if [ "$CLEAN_DB" = true ]; then
    echo "🧹 Cleaning database (removing all volumes and data)..."
    docker compose down -v
    echo "✓ Database cleaned"
fi

echo "🐳 Starting containers..."
docker compose up

echo "✅ Startup complete!"

