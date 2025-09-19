#!/bin/bash

# IPAM4Cloud Dual Portal Runner
# Runs both admin and read-only interfaces simultaneously

echo "🚀 Starting IPAM4Cloud Dual Portal Setup..."
echo ""
echo "📍 Admin Portal: http://localhost:8080"
echo "📍 Read-Only Portal: http://localhost:8081"
echo ""
echo "Press Ctrl+C to stop both portals"
echo ""

# Function to handle cleanup
cleanup() {
    echo ""
    echo "🛑 Stopping both portals..."
    kill $ADMIN_PID $READONLY_PID 2>/dev/null
    exit 0
}

# Set trap to handle Ctrl+C
trap cleanup SIGINT

# Start admin portal in background
echo "🏃‍♂️ Starting Admin Portal..."
cd frontend
if [ ! -d "node_modules" ]; then
    echo "📦 Installing admin portal dependencies..."
    npm install
fi
npm run serve > ../admin-portal.log 2>&1 &
ADMIN_PID=$!

# Start readonly portal in background
echo "🔍 Starting Read-Only Portal..."
cd ../frontend-readonly
if [ ! -d "node_modules" ]; then
    echo "📦 Installing readonly portal dependencies..."
    npm install
fi
npm run serve > ../readonly-portal.log 2>&1 &
READONLY_PID=$!

cd ..

echo ""
echo "✅ Both portals are starting up..."
echo "📝 Admin Portal logs: admin-portal.log"
echo "📝 Read-Only Portal logs: readonly-portal.log"
echo ""
echo "Wait a few seconds for both servers to start, then visit:"
echo "  🔧 Admin Portal: http://localhost:8080"
echo "  👀 Read-Only Portal: http://localhost:8081"
echo ""

# Wait for both processes
wait $ADMIN_PID $READONLY_PID
