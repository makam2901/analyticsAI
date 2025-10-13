#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting Analytics AI Platform with Docker..."
echo "=============================================="

# Change to project directory
cd "$PROJECT_DIR"

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
cd docker && docker-compose down 2>/dev/null || true
cd ..

# Build and start services
echo "🔨 Building and starting services..."
cd docker && docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
cd docker
if docker-compose ps | grep -q "Up"; then
    echo ""
    echo "✅ Analytics AI Platform is now running!"
    echo "=============================================="
    echo "🌐 Frontend: http://localhost:3000"
    echo "🔗 Backend API: http://localhost:8000"
    echo "📖 API Documentation: http://localhost:8000/api/docs"
    echo ""
    echo "📊 Container Status:"
    docker-compose ps
    echo ""
    echo "🛑 To stop: ./scripts/stop.sh"
    echo "📋 To view logs: ./scripts/logs.sh"
    echo "=============================================="
else
    echo "❌ Failed to start services. Check logs with: ./scripts/logs.sh"
    exit 1
fi