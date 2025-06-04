#!/usr/bin/env bash
set -e

echo "🚀 RAGFlow MVP Quick Start"

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file"
fi

# Create required directories
mkdir -p backend/{data,logs,config}
echo "✅ Created directories"

# Stop existing containers
docker compose down --remove-orphans 2>/dev/null || true

# Start with minimal services first
echo "🔄 Starting core services..."
docker compose up -d postgres redis

# Wait for core services
echo "⏳ Waiting for database..."
sleep 10

# Start remaining services
echo "🔄 Starting application services..."
docker compose up -d --build

echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if services are running
if docker compose ps | grep -q "Up"; then
    echo "✅ Services are running!"
    echo ""
    echo "🌐 Available at:"
    echo "   - API: http://localhost:8000"
    echo "   - Frontend: http://localhost:8080"
    echo "   - Docs: http://localhost:8000/docs"
    echo ""
    echo "📋 To check status: docker compose ps"
    echo "📋 To view logs: docker compose logs -f"
    echo "📋 To stop: docker compose down"
else
    echo "❌ Some services failed to start"
    echo "Run: ./troubleshoot.sh for diagnostics"
    docker compose ps
fi
