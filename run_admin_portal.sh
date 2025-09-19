#!/bin/bash

# IPAM4Cloud Admin Portal Runner
# Runs the admin interface on port 8080

echo "🚀 Starting IPAM4Cloud Admin Portal..."
echo "📍 Admin Portal will be available at: http://localhost:8080"
echo "🔗 Read-Only Portal available at: http://localhost:8081"
echo ""

cd frontend

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

echo "🏃‍♂️ Starting Admin Portal development server..."
npm run serve
