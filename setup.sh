#!/usr/bin/env bash
set -e

# RAGFlow MVP Setup Script (Local Python Setup)
echo "Setting up RAGFlow MVP for Indian Valve Company (Local Python)..."

# Create .env from example if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << 'EOF'
# ---------------- Google OAuth ----------------
GOOGLE_CLIENT_ID=792999098406-hmolqmci0o9op9t2vpknmhespml53bau.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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
GOOGLE_PROJECT_ID=ragflow-demo

# Gmail inboxes to process in sequence
GMAIL_INBOXES=storesnproduction@ivc-valves.com,hr.ivcvalves@gmail.com,umesh.jadhav@ivc-valves.com,arpatil@ivc-valves.com,exports@ivc-valves.com,sumit.basu@ivc-valves.com,hr@ivc-valves.com

# Google Drive folder IDs
ATTACHMENT_FOLDER_ID=1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV
DOCUMENTS_FOLDER_ID=1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn

# LLM Model specification
LLM_MODEL=mistral-7b-instruct-v0.3

# Daily digest settings
DIGEST_RECIPIENT=tony@ivc-valves.com
DIGEST_TIME=08:00

# SMTP settings for email sending
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=rag-system@ivc-valves.com

# ---------------- Database --------------------
POSTGRES_USER=raguser
POSTGRES_PASSWORD=ragpass
POSTGRES_DB=ragdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# ---------------- RAGFlow ---------------------
RAGFLOW_HOST=http://localhost:3000
RAGFLOW_API_KEY=

# ---------------- Redis -----------------------
REDIS_HOST=localhost
REDIS_PORT=6379

# ---------------- Ollama ----------------------
OLLAMA_HOST=http://localhost:11434

# ---------------- Other -----------------------
OPENAI_API_KEY=
EOF
    echo "Created .env file - please edit it with your specific configuration values"
fi

# Create logs directory
mkdir -p logs

# Set up Python environment
echo "Setting up Python virtual environment..."
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "Setup complete! Next steps:"
echo ""
echo "1. Install prerequisites on your system:"
echo "   - PostgreSQL: Create database 'ragdb' with user 'raguser'"
echo "   - Redis server"
echo "   - Ollama (optional): Pull model 'mistral:7b-instruct-v0.3'"
echo ""
echo "2. Initialize database:"
echo "   cd backend && source .venv/bin/activate"
echo "   bash scripts/init_db.sh"
echo ""
echo "3. Start the services:"
echo "   bash scripts/run_server.sh    # API server"
echo "   bash scripts/run_worker.sh    # Background worker (in another terminal)"
echo ""
echo "Services will be available at:"
echo "- API: http://localhost:8000"
echo "- API Documentation: http://localhost:8000/docs"
