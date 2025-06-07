#!/usr/bin/env bash
set -e

echo "🚀 Starting RAGFlow MVP..."

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env file from template"
        echo "⚠️  Please edit .env file with your Google OAuth credentials!"
        echo "Press Enter to continue or Ctrl+C to exit..."
        read
    else
        echo "❌ .env.example not found. Please create .env file manually."
        exit 1
    fi
fi

# Create required directories
mkdir -p backend/{data,logs,config} init-scripts

# Create database initialization script
cat > init-scripts/init.sql << 'EOF'
-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF

echo "📦 Building and starting all services..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose up --build -d

echo "⏳ Waiting for services to start..."
sleep 30

# Initialize database
echo "🗄️ Initializing database..."
docker compose exec -T backend python init_db.py || echo "Database init failed, continuing..."

# Check service status
echo "📊 Service Status:"
docker compose ps

echo ""
echo "✅ RAGFlow MVP is starting up!"
echo ""
echo "🌐 Services:"
echo "   - API: http://localhost:8000"
echo "   - Frontend: http://localhost:8080" 
echo "   - API Docs: http://localhost:8000/docs"
echo "   - RAGFlow: http://localhost:3000"
echo ""
echo "🔧 Setup OAuth: http://localhost:8000/auth/login"
echo "📊 Monitor: http://localhost:8000/api/monitoring/status"
echo ""
echo "📋 Commands:"
echo "   - Check logs: docker compose logs -f"
echo "   - Stop all: docker compose down"
echo "   - Restart: docker compose restart" 