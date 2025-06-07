# RAGFlow MVP - Complete System Overview

## Project Vision & Future Roadmap

This RAGFlow MVP is the foundation for Indian Valve Company's (IVC) complete AI transformation. After this phase, the roadmap includes:

- **Phase 2**: Agents for automated daily/weekly reports via email/WhatsApp
- **Phase 3**: External data integration (tender databases, web scraping)
- **Phase 4**: SAP ERP integration with OCR for vendor bills, orders, challans
- **Phase 5**: AI manager suite monitoring all data and taking business actions
- **Phase 6**: Multi-modal chatbots (text/audio) for internal and external communication
- **Phase 7**: AI hiring agent for resume screening and interviews
- **Phase 8**: AI training agent for internal employee development

## Current Phase Goals

### Primary Objectives
1. **Daily Email Digest**: Automated summary of previous 24 hours across all inboxes → `tony@ivc-valves.com`
2. **Weekly Sales Digest**: Summary of quotations sent and sales inquiries received
3. **Complete Email Intelligence**: Process, categorize, and make searchable all company emails
4. **Document Processing**: OCR and categorization of Google Drive documents
5. **RAG-Powered Search**: Semantic search across all indexed content

## System Architecture

### Core Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Gmail API     │    │  Google Drive   │    │   Frontend      │
│   OAuth 2.0     │    │   Documents     │    │   Web UI        │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend API Server                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Gmail     │  │   Drive     │  │    LLM      │            │
│  │  Fetcher    │  │  Processor  │  │ Summarizer  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────┬───────────────────┬───────────────────┬─────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │    RAGFlow      │  │     Ollama      │
│   Database      │  │ Vector Search   │  │ Mistral 7B LLM  │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with proper relationships and deduplication
- **Vector Search**: RAGFlow for semantic search and knowledge bases
- **LLM**: Ollama with Mistral-7B-Instruct-v0.3 (local deployment)
- **Queue**: Redis for job processing
- **OCR**: Tesseract + PyPDF2 for document text extraction
- **Authentication**: Google OAuth 2.0 with domain-wide delegation
- **Frontend**: Modern HTML5/CSS3/JavaScript with responsive design

## Database Schema

### Core Tables

#### 1. Emails Table
```sql
CREATE TABLE emails (
    email_id UUID PRIMARY KEY,
    message_id VARCHAR(255),       -- Gmail message ID
    thread_id VARCHAR(16),         -- Gmail thread ID
    subject TEXT,
    body TEXT,
    sender VARCHAR(255),           -- From email and name
    to TEXT[],                     -- Array of To recipients
    cc TEXT[],                     -- Array of CC recipients
    date TIMESTAMPTZ,
    labels VARCHAR(50)[],          -- Gmail labels (inbox/sent/draft)
    attachments JSONB,             -- Attachment metadata
    summary TEXT,                  -- LLM-generated summary
    category VARCHAR(50),          -- Business category
    priority VARCHAR(15),          -- Urgent/Normal/Low Priority
    sentiment VARCHAR(10),         -- Positive/Neutral/Negative
    importance VARCHAR(15),        -- Very Important/Normal/Low Importance
    keywords TEXT[],               -- 3-5 key phrases
    processed BOOLEAN DEFAULT FALSE,
    rfc822_hash VARCHAR(64)        -- SHA-256 for deduplication
);
```

#### 2. Email Attachments Table
```sql
CREATE TABLE email_attachments (
    attachment_id INT PRIMARY KEY AUTO_INCREMENT,
    email_id UUID REFERENCES emails(email_id),
    file_name VARCHAR(255),
    mime_type VARCHAR(100),
    gdrive_id VARCHAR(44),         -- Google Drive file ID
    size INTEGER,
    content TEXT,                  -- Extracted text content
    summary TEXT,                  -- LLM-generated summary
    category VARCHAR(50),          -- Document category
    priority VARCHAR(15),          -- Urgent/Normal/Low Priority
    sentiment VARCHAR(10),         -- Positive/Neutral/Negative
    importance VARCHAR(15),        -- Very Important/Normal/Low Importance
    keywords TEXT[],               -- Key phrases
    processed BOOLEAN DEFAULT FALSE
);
```

#### 3. Documents Table (Google Drive)
```sql
CREATE TABLE documents (
    doc_id UUID PRIMARY KEY,
    gdrive_id VARCHAR(44),         -- Google Drive file ID
    source_type VARCHAR(50),       -- pdf/doc/image/etc
    content TEXT,                  -- Extracted text
    summary TEXT,                  -- LLM-generated summary
    doc_metadata JSONB,            -- File metadata
    category VARCHAR(50),          -- Document category
    priority VARCHAR(15),          -- Urgent/Normal/Low Priority
    sentiment VARCHAR(10),         -- Positive/Neutral/Negative
    importance VARCHAR(15),        -- Very Important/Normal/Low Importance
    keywords TEXT[],               -- Key phrases
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 4. Inboxes Table
```sql
CREATE TABLE inboxes (
    inbox_id INT PRIMARY KEY AUTO_INCREMENT,
    email_address VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    oauth_token TEXT,              -- Encrypted OAuth refresh token
    token_expires_at TIMESTAMPTZ,  -- Token expiration
    last_history_id VARCHAR(50),   -- Gmail history ID for incremental sync
    last_sync_time TIMESTAMPTZ,    -- Last successful sync
    is_active BOOLEAN DEFAULT TRUE
);
```

## Email Processing Workflow

### 1. Authentication & Authorization

**Domain-Wide Delegation** (for @ivc-valves.com emails):
- Client ID: `792999098406-hmolqmci0o9op9t2vpknmhespml53bau.apps.googleusercontent.com`
- Client Secret: `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`
- Scope: `https://www.googleapis.com/auth/gmail.readonly`

**Individual OAuth** (for @gmail.com accounts):
- Each inbox requires separate OAuth authorization
- Popup-based authentication in web UI
- Automatic token refresh handling

### 2. Email Fetching Sequence

Emails are processed in this exact order (as specified):
1. `storesnproduction@ivc-valves.com` (60 MB)
2. `hr.ivcvalves@gmail.com` (851 inbox, 546 sent - personal Gmail for testing)
3. `umesh.jadhav@ivc-valves.com` (0.5 GB)
4. `arpatil@ivc-valves.com` (0.7 GB)
5. `exports@ivc-valves.com` (1.5 GB)
6. `sumit.basu@ivc-valves.com` (1.6 GB)
7. `hr@ivc-valves.com` (1.7 GB)

### 3. Email Processing Pipeline

```
Gmail API → Email Extraction → Content Cleaning → LLM Analysis → Database Storage → RAGFlow Indexing
```

#### Step 1: Email Extraction
- Fetch emails via Gmail API
- Extract headers (From, To, CC, Date, Subject)
- Extract plain text body (no HTML)
- Remove disclaimers and virus warnings
- Process attachments

#### Step 2: Content Cleaning
- Strip HTML tags and formatting
- Remove email disclaimers (patterns: "Disclaimer:", "WARNING:")
- Preserve email signatures
- Clean OCR text from attachments using domain-specific LLM correction

#### Step 3: LLM Analysis
Uses **Mistral-7B-Instruct-v0.3** with specialized prompts:

**Email Analysis Prompt**:
```
You are an intelligent email assistant for Indian Valve (IVC), a valve manufacturing company...

Given the email below (including subject, email header and body), perform the following tasks:
- Summary (3–5 sentences)
- Urgency: Urgent / Normal / Low Priority  
- Sentiment: Positive / Neutral / Negative
- Importance: Very Important / Normal / Low Importance
- Keywords: 3–5 important keywords
- Category: [22+ business-specific categories]
```

**Categories for Emails**:
- Delay/Follow-up/Reminder/Pending/Shortage
- Maintenance/Repair/Problem/Defect/Issue/Support Request
- Drawing/GAD
- Inspection/TPI
- Quality Assurance/QAP
- Customer Sales Inquiry/Request for Quotation
- Customer Quotation
- Quotation from Vendor/Supplier
- Project Documentation/Approval Process
- Job Application
- Purchase Order
- Advance Bank Guarantee/ABG
- Performance Bank Guarantee/PBG
- Financial Compliance/Document Submission
- Documentation/Compliance
- Vendor Invoice/Bill/Outgoing Payment/Due
- Customer Invoice/Incoming Payment/LC/Letter of Credit/RTGS
- Unsolicited marketing/Newsletter/Promotion
- Operations/Logistics

#### Step 4: Database Storage
- Store email with RFC-822 hash for deduplication
- Link to multiple inboxes via `email_recipients` table
- Store all LLM analysis results
- Track processing status

#### Step 5: RAGFlow Indexing
- Create separate knowledge base per inbox
- Push email content + summary + metadata
- Enable semantic search across all content
- Maintain document relationships

## Attachment Processing

### 1. Supported File Types
- **Text files**: Direct text extraction
- **PDF files**: PyPDF2 + OCR fallback
- **Images**: Tesseract OCR
- **Word documents**: python-docx (planned)
- **Excel files**: pandas (planned)

### 2. OCR Error Correction
Advanced LLM-based OCR correction using domain-specific context:

```
You are an advanced text correction model specializing in fixing OCR errors...
The document belongs to Indian Valve Company (IVC), a valve manufacturing firm...
Apply domain context to resolve ambiguities and maintain proper formatting.
```

### 3. Google Drive Integration
- Upload all attachments to "RAG-Email Attachments" folder
- Store Google Drive file IDs for reference
- Maintain original filenames and metadata

## Google Drive Document Processing

### 1. Source Folders
- **RAG-IVC Documents**: `1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn`
- **RAG-Email Attachments**: `1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV`

### 2. Processing Pipeline
```
Google Drive API → File Download → OCR/Text Extraction → LLM Analysis → Database Storage → RAGFlow Indexing
```

### 3. Knowledge Base Mapping
- Each 1st level folder → Separate RAGFlow knowledge base
- Each inbox → Separate RAGFlow knowledge base
- Enables future access control by department/inbox
- Global search across all knowledge bases

## Web Interface Features

### 1. Authentication Tab 🔐
- **Auto-Authenticate All**: One-click OAuth for all inboxes
- **Individual Inbox Management**: Add/remove inboxes dynamically
- **Real-time Status**: Visual indicators for authentication status
- **Token Management**: Automatic refresh and encrypted storage

### 2. LLM Chat Tab 💬
- **Direct Chat**: Communicate with Mistral 7B LLM
- **RAG Mode Toggle**: Enable context-aware responses using indexed content
- **Conversation History**: Maintain chat sessions
- **Model Settings**: Adjust temperature, top-k, top-p parameters

### 3. RAG Search Tab 🔍
- **Semantic Search**: Natural language queries across all content
- **Advanced Filters**: Date range, priority, category, inbox selection
- **Scope Selection**: Search emails, documents, or both
- **Real-time Results**: Instant search with relevance scoring

### 4. Email Database Tab 📧
- **Comprehensive Filtering**: Category, inbox, priority, sentiment, importance
- **Date Range Selection**: Custom date filtering
- **Pagination**: Handle large datasets efficiently
- **Quick Actions**: View details, mark as processed, export
- **Real-time Statistics**: Email counts by category and status

### 5. Documents Tab 📁
- **Google Drive Integration**: Browse and search documents
- **Category Filtering**: Filter by document type and category
- **Processing Status**: Track OCR and analysis progress
- **Metadata Display**: File size, type, processing date

### 6. System Admin Tab ⚙️
- **Queue Monitoring**: View processing queue status
- **Scheduler Status**: Monitor background jobs
- **System Health**: Check service connectivity
- **Performance Metrics**: Processing speeds and success rates

## API Endpoints

### Authentication
- `POST /auth/start/{inbox}` - Start OAuth flow for inbox
- `GET /auth/callback` - Handle OAuth callback
- `GET /auth/status` - Check authentication status
- `POST /auth/refresh/{inbox}` - Refresh OAuth token

### Email Management
- `GET /api/emails` - List emails with filtering
- `GET /api/emails/{email_id}` - Get email details
- `POST /api/emails/search` - Search emails
- `GET /api/emails/stats` - Get email statistics

### Document Management
- `GET /api/documents` - List documents with filtering
- `GET /api/documents/{doc_id}` - Get document details
- `POST /api/documents/search` - Search documents

### LLM Integration
- `POST /api/llm/chat` - Chat with LLM
- `POST /api/llm/rag-search` - RAG-powered search
- `GET /api/llm/models` - List available models

### System Administration
- `GET /api/system/status` - System health check
- `GET /api/system/queue` - Processing queue status
- `POST /api/system/process` - Trigger processing
- `GET /api/system/stats` - System statistics

## Deployment & Configuration

### 1. Docker Compose Setup
```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ragflow_db
      POSTGRES_USER: ragflow
      POSTGRES_PASSWORD: ragflow123
    
  redis:
    image: redis:7-alpine
    
  ragflow:
    image: infiniflow/ragflow:latest
    ports:
      - "9380:9380"
    
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - ragflow
      - ollama
```

### 2. Environment Configuration
```bash
# Google OAuth
GOOGLE_CLIENT_ID=792999098406-hmolqmci0o9op9t2vpknmhespml53bau.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=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

# Google Drive Folders
GDRIVE_DOCUMENTS_FOLDER_ID=1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn
GDRIVE_ATTACHMENTS_FOLDER_ID=1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV

# Database
DATABASE_URL=postgresql://ragflow:ragflow123@postgres:5432/ragflow_db

# RAGFlow
RAGFLOW_HOST=http://ragflow:9380
RAGFLOW_API_KEY=ragflow-YWRtaW46cmFnZmxvdzEyMw

# Ollama
OLLAMA_HOST=http://ollama:11434
LLM_MODEL=mistral:7b-instruct-v0.3-q4_K_M
```

### 3. Model Setup
```bash
# Pull Mistral model
docker exec -it ollama ollama pull mistral:7b-instruct-v0.3-q4_K_M

# Verify model
docker exec -it ollama ollama list
```

## Performance Optimizations

### 1. Database Optimizations
- Indexes on frequently queried fields (date, category, sender)
- Partitioning for large email tables
- Connection pooling for concurrent access

### 2. LLM Optimizations
- Prompt caching for repeated patterns
- Batch processing for multiple emails
- Temperature optimization for different tasks

### 3. RAGFlow Optimizations
- Separate knowledge bases for better performance
- Metadata enrichment for faster filtering
- Chunking strategy for large documents

### 4. System Resource Management
- **Day Mode**: 4 concurrent processes, 8 cores, 42GB RAM
- **Night Mode**: Full server resources (32 cores, 250GB RAM)
- **Auto-scaling**: Adjust based on queue size

## Monitoring & Logging

### 1. Application Logs
- Structured logging with timestamps
- Error tracking and alerting
- Performance metrics collection

### 2. System Monitoring
- Database connection health
- RAGFlow service status
- Ollama model availability
- OAuth token validity

### 3. Business Metrics
- Emails processed per hour
- Categorization accuracy
- Search query performance
- User engagement statistics

## Security Considerations

### 1. OAuth Security
- Encrypted token storage
- Automatic token refresh
- Scope limitation (read-only access)

### 2. Data Protection
- Database encryption at rest
- Secure API endpoints
- Input validation and sanitization

### 3. Access Control
- Role-based access (planned for future phases)
- Audit logging for sensitive operations
- Rate limiting on API endpoints

## Future Enhancements (Next Phases)

### 1. Automated Reporting
- Daily digest emails to `tony@ivc-valves.com`
- Weekly sales quotation summaries
- Custom report generation

### 2. Advanced AI Features
- Sentiment analysis trends
- Automated follow-up suggestions
- Priority-based email routing

### 3. Integration Capabilities
- SAP ERP integration
- External tender database scraping
- WhatsApp Business API integration

### 4. Advanced Analytics
- Email pattern analysis
- Business intelligence dashboards
- Predictive analytics for sales

## Troubleshooting Guide

### Common Issues

1. **OAuth Authentication Failures**
   - Check client ID/secret configuration
   - Verify redirect URI matches
   - Ensure proper scopes are requested

2. **LLM Processing Errors**
   - Verify Ollama service is running
   - Check model availability
   - Monitor memory usage

3. **RAGFlow Connection Issues**
   - Verify RAGFlow service status
   - Check API key configuration
   - Test knowledge base creation

4. **Database Connection Problems**
   - Check PostgreSQL service status
   - Verify connection string
   - Monitor connection pool usage

### Performance Issues

1. **Slow Email Processing**
   - Check Gmail API rate limits
   - Monitor database query performance
   - Optimize LLM batch processing

2. **Search Performance**
   - Verify RAGFlow indexing status
   - Check knowledge base size
   - Monitor vector search performance

## Support & Maintenance

### Regular Maintenance Tasks
- Database backup and cleanup
- Log rotation and archival
- OAuth token renewal monitoring
- Model performance evaluation

### Monitoring Checklist
- [ ] All services running
- [ ] OAuth tokens valid
- [ ] Processing queue healthy
- [ ] Database performance optimal
- [ ] Search functionality working
- [ ] Web interface responsive

This comprehensive system provides the foundation for IVC's complete AI transformation, with robust email intelligence, document processing, and semantic search capabilities. The architecture is designed to scale for the ambitious roadmap ahead! 🚀 