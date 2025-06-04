#!/usr/bin/env bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}RAGFlow MVP Troubleshooting${NC}"
echo "================================="

# Check required commands
echo -e "\n${BLUE}1. Command availability${NC}"
for cmd in docker "docker compose" jq curl nc; do
    if ! command -v ${cmd%% *} >/dev/null 2>&1; then
        echo -e "${RED}✗ Required command '$cmd' is missing${NC}"
        exit 1
    fi
done

# Docker status
echo -e "\n${BLUE}2. Docker Status${NC}"
if docker info >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker daemon is running${NC}"
    docker --version
else
    echo -e "${RED}✗ Docker daemon is not running${NC}"
    exit 1
fi

# Check Docker Compose
echo -e "\n${BLUE}3. Docker Compose${NC}"
if docker compose version >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker Compose is available${NC}"
    docker compose version
else
    echo -e "${RED}✗ Docker Compose is not available${NC}"
    exit 1
fi

# Check .env file
echo -e "\n${BLUE}4. Configuration${NC}"
if [ -f .env ]; then
    echo -e "${GREEN}✓ .env file exists${NC}"
    
    # Check critical variables
    if grep -q "GOOGLE_CLIENT_ID=" .env && grep -q "GOOGLE_CLIENT_SECRET=" .env; then
        echo -e "${GREEN}✓ Google OAuth credentials configured${NC}"
    else
        echo -e "${YELLOW}⚠ Google OAuth credentials may be missing${NC}"
    fi
else
    echo -e "${RED}✗ .env file is missing${NC}"
    echo "Run: cp .env.example .env"
fi

# Check containers
echo -e "\n${BLUE}5. Container Status${NC}"
if docker compose ps >/dev/null 2>&1; then
    echo "Current container status:"
    docker compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Health}}"
    
    # Check individual services
    services=("postgres" "redis" "ragflow" "ollama" "backend" "frontend" "worker")
    
    for service in "${services[@]}"; do
        status=$(docker compose ps --format json | jq -r --arg service "$service" '.[] | select(.Service == $service) | .Status')
        if [ "$status" != "null" ] && [ -n "$status" ]; then
            if [[ "$status" == *"Up"* ]]; then
                echo -e "${GREEN}✓ $service is running${NC}"
            else
                echo -e "${RED}✗ $service is not running: $status${NC}"
            fi
        else
            echo -e "${RED}✗ $service is not found${NC}"
        fi
    done
else
    echo -e "${YELLOW}⚠ No containers are running${NC}"
fi

# Check ports
echo -e "\n${BLUE}6. Port Availability${NC}"
ports=(5432 6379 3000 8000 8080 11434)
port_names=("PostgreSQL" "Redis" "RAGFlow" "Backend API" "Frontend" "Ollama")

for i in "${!ports[@]}"; do
    port=${ports[$i]}
    name=${port_names[$i]}
    
    if nc -z localhost $port 2>/dev/null; then
        echo -e "${GREEN}✓ Port $port ($name) is accessible${NC}"
    else
        echo -e "${RED}✗ Port $port ($name) is not accessible${NC}"
    fi
done

# Check service health
echo -e "\n${BLUE}7. Service Health${NC}"

# Backend API
if curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend API is healthy${NC}"
else
    echo -e "${RED}✗ Backend API is not responding${NC}"
fi

# Ollama
if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is accessible${NC}"
    # Check for models
    models=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null)
    if echo "$models" | grep -q "mistral"; then
        echo -e "${GREEN}✓ Mistral model is available${NC}"
    else
        echo -e "${YELLOW}⚠ Mistral model not found${NC}"
        echo "Run: docker compose exec ollama ollama pull mistral:7b-instruct-v0.3"
    fi
else
    echo -e "${RED}✗ Ollama is not responding${NC}"
fi

# Check logs for errors
echo -e "\n${BLUE}8. Recent Errors${NC}"
echo "Checking recent container logs for errors..."

services=("backend" "worker" "ragflow" "ollama")
for service in "${services[@]}"; do
    echo -e "\n${YELLOW}$service errors:${NC}"
    docker compose logs --tail=5 $service 2>/dev/null | grep -i "error\|exception\|failed" || echo "No recent errors"
done

# Check disk space
echo -e "\n${BLUE}9. System Resources${NC}"
df_output=$(df -h /)
available_space=$(echo "$df_output" | awk 'NR==2 {print $4}')
echo "Available disk space: $available_space"

# Check memory
if command -v free >/dev/null 2>&1; then
    free -h
elif command -v vm_stat >/dev/null 2>&1; then
    # macOS
    vm_stat
fi

echo -e "\n${BLUE}Common Solutions:${NC}"
echo "- If containers won't start: docker compose down && docker compose up --build -d"
echo "- If database issues: docker compose down -v && docker compose up -d"
echo "- If port conflicts: Check if other services are using the same ports"
echo "- If Ollama model missing: docker compose exec ollama ollama pull mistral:7b-instruct-v0.3"
echo "- If permission issues: Check .env file permissions and Docker daemon access"

echo -e "\n${BLUE}For detailed logs, run:${NC}"
echo "docker compose logs -f [service_name]"

