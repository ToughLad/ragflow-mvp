# RAGFlow MVP - Indian Valve Company Internal RAG System

End‑to‑end internal Retrieval‑Augmented‑Generation system for IVC email processing, document indexing, and daily digest generation.

## Features

- **Gmail Integration**: Process emails from 7 specific inboxes in sequence
- **Google Drive Integration**: Index documents with OCR processing
- **Daily Digest**: Automated email summaries sent to tony@ivc-valves.com
- **LLM Processing**: Mistral-7B-Instruct-v0.3 for summarization and categorization
- **Background Queue**: Redis-based task processing
- **RAGFlow Integration**: Vector database with search capabilities

## Quick Start

```bash
# Setup environment and pull required models
bash setup.sh

# Start all services
docker compose up -d --build
```

### Services

| Service   | Port | Purpose                       |
|-----------|------|-------------------------------|
| backend   | 8000 | FastAPI + API endpoints       |
| worker    | -    | Background task processing    |
| RAGFlow   | 3000 | Vector DB & search UI         |
| Ollama    | 11434| Local Mistral 7B LLM          |
| PostgreSQL| 5432 | Structured data storage       |
| Redis     | 6379 | Background job queue          |

### Configuration

1. Copy `.env.example` to `.env` and configure:
   - Google OAuth credentials (already set from requirements)
   - Gmail inbox sequence (already configured)
   - Google Drive folder IDs (already set)

### Authentication

1. Start Google OAuth flow: `GET /auth/google`
2. Complete authorization and get callback token
3. Check authentication status: `GET /auth/status`

### Usage

```bash
# Process emails from all configured inboxes
POST /ingest/emails

# Process documents from Google Drive
POST /api/documents/upload

# Generate daily digest
POST /api/digest/daily

# Search across all indexed content
POST /api/search?q=your-query

# Monitor processing queue
GET /api/queue/status
```

### API Endpoints

All endpoints exactly match Phase 1c specification:

- **Email Management**: `/api/emails/*`, `/api/inbox/*`
- **Document Management**: `/api/documents/*`
- **Processing Queue**: `/api/processing_queue/*`
- **Search**: `/api/search`
- **Authentication**: `/auth/*`
- **Daily Digest**: `/api/digest/daily`

### Architecture

- **PostgreSQL**: Emails, documents, attachments, processing queue
- **RAGFlow**: Vector database with separate knowledge bases per inbox/department
- **Redis + RQ**: Background task processing
- **Ollama**: Local LLM serving (Mistral-7B-Instruct-v0.3)
- **Google APIs**: Gmail and Drive integration with OAuth2

### Background Processing

- Email processing: Fetches, extracts, summarizes, indexes
- Document processing: OCR, text extraction, categorization
- Daily digest: HTML email generation and sending
- Attachment processing: Upload to Drive, OCR, content extraction

### Access URLs

- API Documentation: http://localhost:8000/docs
- RAGFlow UI: http://localhost:3000
- Health Check: http://localhost:8000/health

For technical details, see the implementation files in `/backend/app/`.
