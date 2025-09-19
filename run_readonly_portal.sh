#!/bin/bash

# IPAM4Cloud Read-Only Portal Runner
# Runs the read-only interface on port 8081

echo "🔍 Starting IPAM4Cloud Read-Only Portal..."
echo "📍 Read-Only Portal will be available at: http://localhost:8081"
echo "🔗 Admin Portal available at: http://localhost:8080"
echo ""

cd frontend-readonly

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🏃‍♂️ Starting Read-Only Portal development server..."
npm run serve
