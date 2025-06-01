#!/usr/bin/env bash
set -e

# RAGFlow MVP Setup Script
echo "Setting up RAGFlow MVP for Indian Valve Company..."

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your specific configuration values"
fi

# Create logs directory
mkdir -p logs

# Pull Ollama model
echo "Pulling Mistral model for Ollama..."
docker run --rm -v ollama_data:/root/.ollama ollama/ollama:latest pull mistral:7b-instruct-v0.3

echo "Setup complete! Now run: docker compose up -d --build"
echo ""
echo "Services will be available at:"
echo "- API: http://localhost:8000"
echo "- RAGFlow UI: http://localhost:3000"  
echo "- API Documentation: http://localhost:8000/docs"
echo ""
echo "First, authenticate with Google OAuth:"
echo "1. Visit http://localhost:8000/auth/google"
echo "2. Complete OAuth flow"
echo "3. Start processing: POST http://localhost:8000/ingest/emails"
