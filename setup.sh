#!/usr/bin/env bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Setting up RAGFlow MVP...${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command_exists docker; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker Compose is not available${NC}"
    exit 1
fi

for cmd in jq curl nc; do
    if ! command_exists "$cmd"; then
        echo -e "${RED}Error: $cmd is required but not installed${NC}"
        exit 1
    fi
done

# Check if Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Error: Docker daemon is not running${NC}"
    exit 1
fi

echo -e "${GREEN}Docker prerequisites OK${NC}"

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p backend/data backend/logs backend/config

# Copy .env from example if it doesn't exist
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${GREEN}Created .env file from template${NC}"
        echo -e "${YELLOW}Please edit .env file with your configuration before continuing${NC}"
        echo -e "${YELLOW}Press Enter when ready to continue...${NC}"
        read
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# Stop any existing containers
echo -e "${BLUE}Stopping existing containers...${NC}"
docker compose down --remove-orphans 2>/dev/null || true

# Remove old images (optional)
echo -e "${BLUE}Cleaning up old images...${NC}"
docker compose down --rmi local 2>/dev/null || true

# Build and start services
echo -e "${BLUE}Building and starting services...${NC}"
docker compose up --build -d

# Wait for services to be healthy
echo -e "${BLUE}Waiting for services to be ready...${NC}"

# Function to wait for service health
wait_for_service() {
    local service=$1
    local max_attempts=30
    local attempt=1
    
    echo -e "${YELLOW}Waiting for $service to be healthy...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose ps --services --filter "status=running" | grep -q "^$service$"; then
            if [ "$(docker compose ps --format json | jq -r --arg service "$service" '.[] | select(.Service == $service) | .Health')" = "healthy" ]; then
                echo -e "${GREEN}$service is healthy${NC}"
                return 0
            fi
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}$service failed to become healthy${NC}"
    return 1
}

# Wait for core services
wait_for_service "postgres"
wait_for_service "redis"
wait_for_service "ragflow"
wait_for_service "ollama"
wait_for_service "backend"

echo -e "${GREEN}All services are running!${NC}"

# Initialize database
echo -e "${BLUE}Initializing database...${NC}"
docker compose exec backend python init_db.py

# Pull Ollama model if needed
echo -e "${BLUE}Ensuring Ollama model is available...${NC}"
docker compose exec ollama ollama pull mistral:7b-instruct-v0.3 || echo -e "${YELLOW}Model pull failed, continuing...${NC}"

# Show service status
echo -e "\n${GREEN}Setup completed successfully!${NC}"
echo -e "\n${BLUE}Service Status:${NC}"
docker compose ps

echo -e "\n${BLUE}Available Services:${NC}"
echo -e "- ${GREEN}API Server:${NC} http://localhost:8000"
echo -e "- ${GREEN}API Documentation:${NC} http://localhost:8000/docs"
echo -e "- ${GREEN}Frontend:${NC} http://localhost:8080"
echo -e "- ${GREEN}RAGFlow:${NC} http://localhost:3000"
echo -e "- ${GREEN}Ollama:${NC} http://localhost:11434"

echo -e "\n${BLUE}Useful Commands:${NC}"
echo -e "- View logs: ${YELLOW}docker compose logs -f${NC}"
echo -e "- Stop services: ${YELLOW}docker compose down${NC}"
echo -e "- Restart services: ${YELLOW}docker compose restart${NC}"
echo -e "- Check status: ${YELLOW}docker compose ps${NC}"

echo -e "\n${BLUE}Next Steps:${NC}"
echo -e "1. Configure Google OAuth credentials in .env"
echo -e "2. Set up authentication: http://localhost:8000/auth/login"
echo -e "3. Start email ingestion: POST http://localhost:8000/ingest/emails"
echo -e "4. Upload documents: POST http://localhost:8000/api/documents/upload"

echo -e "\n${GREEN}RAGFlow MVP is ready!${NC}"
