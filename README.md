# RAGFlow MVP - Indian Valve Company Internal RAG System

End‑to‑end internal Retrieval‑Augmented‑Generation system for IVC email processing, document indexing, and daily digest generation.

## Features

- **Gmail Integration**: Process emails from 7 specific inboxes in sequence
- **Google Drive Integration**: Index documents with OCR processing
- **Daily Digest**: Automated email summaries sent to tony@ivc-valves.com
- **LLM Processing**: Mistral-7B-Instruct-v0.3 (configurable via `.env`) with conservative sampling to reduce hallucinations
- **Background Queue**: Redis-based task processing
- **RAGFlow Integration**: Vector database with search capabilities

## Quick Start

```bash
# Setup environment and pull required models
bash setup.sh

# Start all services using the provided compose file
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

1. Edit the provided `.env` file if you need to change defaults:
   - Google OAuth credentials (already set from requirements)
   - Gmail inbox sequence (already configured)
   - Google Drive folder IDs (already set)
   - LLM settings (model and sampling parameters) using `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_TOP_K`, and `LLM_TOP_P`

### Authentication

1. Open `/auth/login` in your browser.
2. Click each inbox to authorize access via Google's consent screen.
3. After Google redirects back, tokens are stored automatically.
4. Check authentication status with `GET /auth/status`.

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

## Project Vision & Goals (Current Phase)
The current sprint focuses on generating a **daily email digest** (previous 24 h) automatically sent to **tony@ivc-valves.com** and building an internal Retrieval-Augmented-Generation (RAG) system that answers questions from all indexed emails and documents.  
*A weekly sales digest will follow as a separate milestone after this 7-day sprint.*

## Email Indexing Sequence (Round 1)
1. storesnproduction@ivc-valves.com  
2. hr.ivcvalves@gmail.com  
3. umesh.jadhav@ivc-valves.com  
4. arpatil@ivc-valves.com  
5. exports@ivc-valves.com  
6. sumit.basu@ivc-valves.com  
7. hr@ivc-valves.com  

Emails are deduplicated with an RFC-822 SHA-256 hash so a single copy is stored even if CC’ed to multiple internal recipients.

## Knowledge-Base Mapping
• One RAGFlow knowledge base per inbox listed above.  
• One knowledge base per first-level folder under the Google Drive folder “RAG-IVC Documents”.  
Search queries are executed across **all** knowledge bases.

## Future Milestones
• Weekly sales quotation / inquiry digest.  
• Extended agents (reporting, SAP integration, chatbots, etc.) – outside current sprint scope.

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
