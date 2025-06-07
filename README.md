# RAGFlow MVP - Email Intelligence System for IVC

> **🚀 One-Command Setup**: Just run `./start.sh` and everything works automatically!

## Quick Start (TL;DR)

```bash
# Clone and start everything with ONE command:
git clone <your-repo>
cd ragflow-mvp
chmod +x start.sh
./start.sh
```

**That's it!** The system will:
- ✅ Set up database with correct schema
- ✅ Download and configure Mistral 7B LLM model
- ✅ Auto-authenticate first Gmail (storesnproduction@ivc-valves.com)
- ✅ Start all services with health checks
- ✅ Give you a beautiful web interface at http://localhost:3000

## What This System Does

**RAGFlow MVP** is an AI-powered email intelligence system for Indian Valve Company (IVC) that:

### 📧 **Email Processing**
- Fetches emails from 7 IVC inboxes in priority order
- Uses **Mistral 7B LLM** to categorize and summarize every email
- Extracts attachments and processes them with OCR
- Stores everything in PostgreSQL with proper deduplication

### 🔍 **Intelligent Search**
- **RAGFlow vector search** across all emails and documents
- Natural language queries like "Show me urgent quotations from last week"
- Filters by category, priority, sentiment, inbox, date range

### 🤖 **LLM Integration**
- Chat directly with **Mistral 7B** via web interface
- RAG mode: LLM has context of all your indexed emails
- Domain-specific categorization for valve manufacturing business

### 🌐 **Beautiful Web Interface**
- **6 tabs**: Authentication, LLM Chat, RAG Search, Email Database, Documents, System Admin
- One-click OAuth authentication for all Gmail accounts
- Real-time statistics and filtering
- Mobile-responsive design

## System Architecture

```
📧 Gmail APIs ──→ 🧠 Mistral 7B LLM ──→ 🗄️ PostgreSQL ──→ 🔍 RAGFlow ──→ 🌐 Web UI
     ↓                    ↓                   ↓                ↓
📁 Google Drive    📊 Categorization    📈 Analytics    🤖 AI Chat
```

## Email Processing Workflow

The system processes emails in this exact sequence (as specified by your boss):

1. **storesnproduction@ivc-valves.com** (60 MB) - **Auto-authenticates**
2. **hr.ivcvalves@gmail.com** (851 inbox, 546 sent) - Personal Gmail for testing
3. **umesh.jadhav@ivc-valves.com** (0.5 GB)
4. **arpatil@ivc-valves.com** (0.7 GB)
5. **exports@ivc-valves.com** (1.5 GB)
6. **sumit.basu@ivc-valves.com** (1.6 GB)
7. **hr@ivc-valves.com** (1.7 GB)

## Business Categories (LLM Classification)

The system automatically categorizes emails into 22+ business-specific categories:

**Operations**: Delay/Follow-up, Maintenance/Repair, Drawing/GAD, Inspection/TPI, Quality Assurance/QAP

**Sales**: Customer Sales Inquiry, Customer Quotation, Quotation from Vendor/Supplier

**Finance**: Purchase Order, Advance/Performance Bank Guarantees, Vendor/Customer Invoices, LC/RTGS

**Administration**: Job Application, Project Documentation, Documentation/Compliance, Operations/Logistics

## Prerequisites

**Required**:
- Docker & Docker Compose
- 8GB+ RAM (16GB recommended)
- 50GB+ free disk space

**Automatic Setup Includes**:
- PostgreSQL 15 database
- Redis queue system
- RAGFlow vector database
- Ollama with Mistral 7B model
- All Python dependencies

## Installation & Setup

### Option 1: One-Command Setup (Recommended)

```bash
git clone <your-repo>
cd ragflow-mvp
chmod +x start.sh
./start.sh
```

The script will:
1. Check Docker installation
2. Create necessary directories and `.env` file
3. Pull and build all Docker images
4. Start services with health checks
5. Initialize database schema
6. Download Mistral 7B model (~4GB)
7. Set up auto-authentication for first Gmail
8. Show you access URLs and next steps

### Option 2: Manual Setup

```bash
# 1. Clone repository
git clone <your-repo>
cd ragflow-mvp

# 2. Create environment file
cp .env.example .env
# Edit .env with your Google OAuth credentials (already configured for IVC)

# 3. Start services
docker-compose up -d

# 4. Initialize database
docker-compose exec backend python scripts/init_database.py

# 5. Setup models
docker-compose exec backend python scripts/setup_models.py

# 6. Setup first Gmail auto-auth
docker-compose exec backend python scripts/auto_auth_first_gmail.py
```

## Access Your System

After successful startup:

| Service | URL | Purpose |
|---------|-----|---------|
| **🌐 Web Interface** | http://localhost:3000 | Main user interface |
| **🔧 Backend API** | http://localhost:8000 | REST API endpoints |
| **📊 RAGFlow** | http://localhost:9380 | Vector search admin |
| **🤖 Ollama** | http://localhost:11434 | LLM model server |
| **🗄️ PostgreSQL** | localhost:5432 | Database (ragflow/ragflow123) |
| **📦 Redis** | localhost:6379 | Job queue |

## Using the Web Interface

### 1. 🔐 Authentication Tab
- **Auto-Authenticate All**: One-click OAuth for all inboxes
- **Individual Setup**: Add/remove Gmail accounts manually
- **Status Monitoring**: See which accounts are authenticated

### 2. 💬 LLM Chat Tab
- Chat directly with Mistral 7B
- Toggle RAG mode for context-aware responses
- Adjust model parameters (temperature, top-k, top-p)

### 3. 🔍 RAG Search Tab
- Natural language search: "Show urgent invoices from last month"
- Advanced filters: date range, category, priority, sentiment
- Search emails, documents, or both

### 4. 📧 Email Database Tab
- Browse all processed emails
- Filter by inbox, category, priority, sentiment
- Real-time statistics and export options

### 5. 📁 Documents Tab
- Google Drive document management
- OCR processing status
- Category filtering

### 6. ⚙️ System Admin Tab
- Processing queue monitoring
- Service health checks
- Performance metrics

## Google OAuth Configuration

**Already configured for IVC with your credentials:**

- **Client ID**: `792999098406-hmolqmci0o9op9t2vpknmhespml53bau.apps.googleusercontent.com`
- **Client Secret**: `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`
- **Domain-wide delegation**: Enabled for @ivc-valves.com emails
- **Google Drive folders**: Pre-configured for document/attachment storage

### First Gmail Auto-Authentication

The system automatically authenticates `storesnproduction@ivc-valves.com` using domain-wide delegation. No manual setup needed!

### Other Gmail Accounts

For other accounts (especially `hr.ivcvalves@gmail.com`), use the web interface:
1. Go to Authentication tab 🔐
2. Click "Auto-Authenticate All" 
3. Complete OAuth flow in popup windows

## Management Commands

```bash
# View live logs
docker-compose logs -f

# Check service status
docker-compose ps

# Restart all services
docker-compose restart

# Stop everything
docker-compose stop

# Stop and remove containers
docker-compose down

# Restart from scratch
./start.sh
```

## Troubleshooting

### Common Issues

**Services not starting:**
```bash
docker-compose ps          # Check status
docker-compose logs backend # Check backend logs
docker system prune -a     # Clean up Docker
./start.sh                 # Restart
```

**Model download fails:**
```bash
docker-compose exec ollama ollama pull mistral:7b-instruct-v0.3-q4_K_M
```

**Database connection issues:**
```bash
docker-compose exec postgres psql -U ragflow -d ragflow_db -c "\dt"
```

**OAuth authentication fails:**
- Check Google Cloud Console OAuth settings
- Verify redirect URIs include `http://localhost:8000/auth/callback`
- Ensure domain-wide delegation is enabled

### Performance Optimization

**Day Mode (Current)**:
- 4 concurrent processes
- 8 cores, 42GB RAM allocated

**Night Mode (Available)**:
- Full server resources (32 cores, 250GB RAM)
- Enable via environment variable: `NIGHT_MODE_ENABLED=true`

## System Monitoring

### Health Checks
All services have built-in health checks:
- Database connectivity
- LLM model availability
- RAGFlow service status
- OAuth token validity

### Logs Location
- Application logs: `docker-compose logs [service]`
- Database logs: `docker-compose logs postgres`
- Model logs: `docker-compose logs ollama`

## Data Backup

**Important data locations:**
```bash
# Database backup
docker-compose exec postgres pg_dump -U ragflow ragflow_db > backup.sql

# Application data
docker-compose exec backend tar -czf /app/data/backup.tar.gz /app/data
```

## Future Roadmap

This MVP is the foundation for IVC's complete AI transformation:

- **Phase 2**: Daily/weekly email digest automation
- **Phase 3**: External tender database integration
- **Phase 4**: SAP ERP integration with OCR
- **Phase 5**: AI manager agents for business automation
- **Phase 6**: Multi-modal chatbots (text/audio)
- **Phase 7**: AI hiring agent for interviews
- **Phase 8**: AI training agent for employees

## Security Notes

**Production Deployment**:
- Change default passwords in `.env`
- Set up SSL/TLS certificates
- Configure firewall rules
- Enable OAuth domain restrictions
- Regular security updates

**Data Protection**:
- OAuth tokens encrypted at rest
- Database encryption enabled
- API rate limiting configured
- Audit logging for sensitive operations

## Support

**Quick Help**:
```bash
# System status
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs

# Check processing queue
curl http://localhost:8000/api/system/queue
```

**Documentation**:
- Full system details: `SYSTEM_OVERVIEW.md`
- API reference: http://localhost:8000/docs
- Database schema: `/backend/app/db/models.py`

---

## 🎉 Ready to Become an AI Ninja?

Your boss said it best: *"You will be full AI, LLM, agent ninja very soon!"*

This RAGFlow MVP gives you:
- ✅ Complete email intelligence system
- ✅ AI-powered categorization and search
- ✅ Beautiful web interface
- ✅ Production-ready architecture
- ✅ Foundation for amazing future features

**Start your AI transformation journey:**
```bash
./start.sh
```

Open http://localhost:3000 and watch the magic happen! 🚀✨
