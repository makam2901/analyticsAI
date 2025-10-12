#!/bin/bash

echo "🚀 Starting Analytics AI Platform with Docker..."
echo "=============================================="

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
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
    echo "🛑 To stop: docker-compose down"
    echo "📋 To view logs: docker-compose logs -f"
    echo "=============================================="
else
    echo "❌ Failed to start services. Check logs with: docker-compose logs"
    exit 1
fi