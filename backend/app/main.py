from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List, Optional
import logging

from app.ingest.gmail_fetcher import fetch_and_process
from app.ingest.document_processor import process_all_documents
from app.digest.daily_digest import send_daily_digest
from app.ragflow.client import query_ragflow
from app.db import models, engine, SessionLocal
from app.db import crud
from app.llm.summarizer import summarize_email, summarize_document
from app.scheduler.daily_scheduler import start_scheduler, stop_scheduler, get_scheduler_status
from app.config import get_settings

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    models.Base.metadata.create_all(bind=engine)
    start_scheduler()  # Start the background scheduler
    yield
    # Shutdown
    stop_scheduler()  # Stop the scheduler
    engine.dispose()

app = FastAPI(title="RAGFlow MVP API", lifespan=lifespan)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Email endpoints
@app.post("/api/emails/import", summary="Add new email account to fetch & index")
def add_email_inbox(email_address: str, description: str = "", db: Session = Depends(get_db)):
    try:
        inbox = crud.get_or_create_inbox(db, email_address, description)
        return {"detail": f"Email inbox {email_address} added successfully", "inbox_id": inbox.inbox_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Listing inboxes for UI
@app.get("/api/inbox/list", summary="List configured inboxes")
def list_inboxes(db: Session = Depends(get_db)):
    inboxes = crud.get_all_inboxes(db)
    return {"inboxes": [i.email_address for i in inboxes]}

@app.post("/api/emails/refresh/{email_id}", summary="Regenerate summary for 1 email")
def refresh_email(email_id: str, bg: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        email = db.query(models.Email).filter(models.Email.email_id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        # Add to background task queue for re-processing
        def reprocess_email():
            summary_data = summarize_email(
                from_email=email.sender,
                to_list=email.to or [],
                cc_list=email.cc or [],
                subject=email.subject or "",
                date_str=email.date.isoformat() if email.date else "",
                body=email.body or "",
                email_id=email.sender,
            )
            
            update_data = {
                'summary': summary_data.get('summary', ''),
                'category': summary_data.get('category', ''),
                'priority': summary_data.get('urgency', 'Normal'),  # Map urgency to priority field
                'sentiment': summary_data.get('sentiment', 'Neutral'),
                'importance': summary_data.get('importance', 'Normal'),
                'keywords': summary_data.get('keywords', [])
            }
            crud.update_email(db, email_id, update_data)
        
        bg.add_task(reprocess_email)
        return {"detail": f"Email {email_id} queued for refresh"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List emails with optional filters
@app.get("/api/emails", summary="List emails with filters")
def list_emails(
    inboxes: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    try:
        query = db.query(models.Email)
        if inboxes:
            inbox_list = [i.strip() for i in inboxes.split(',') if i.strip()]
            if inbox_list:
                query = query.join(models.EmailRecipient).join(models.Inbox).filter(models.Inbox.email_address.in_(inbox_list))
        if category:
            query = query.filter(models.Email.category == category)
        emails = query.order_by(models.Email.date.desc()).offset(offset).limit(limit).all()
        return {
            "emails": [
                {
                    "email_id": e.email_id,
                    "subject": e.subject,
                    "date": e.date.isoformat() if e.date else None,
                }
                for e in emails
            ],
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inbox/refresh/{email_addresses}", summary="Regenerate summary for email inboxes")
def refresh_inbox(email_addresses: str, bg: BackgroundTasks):
    try:
        addresses = [addr.strip() for addr in email_addresses.split(',')]
        
        def reprocess_inbox():
            # This would re-fetch and process emails from specified inboxes
            fetch_and_process()
        
        bg.add_task(reprocess_inbox)
        return {"detail": f"Inboxes {email_addresses} queued for refresh"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inbox/refreshAll", summary="Regenerate summary for all email inboxes")
def refresh_all_inboxes(bg: BackgroundTasks):
    bg.add_task(fetch_and_process)
    return {"detail": "All email inboxes queued for refresh"}

@app.post("/ingest/emails", summary="Fetch latest emails and index them")
def ingest_emails(bg: BackgroundTasks):
    bg.add_task(fetch_and_process)
    return {"detail": "Email ingestion started"}

# Document endpoints
@app.post("/api/documents/upload", summary="Handle multiple files/folders/zips")
def upload_documents(bg: BackgroundTasks):
    """Handle document upload from Google Drive folders as specified in requirements."""
    def process_documents():
        process_all_documents()
    
    bg.add_task(process_documents)
    return {"detail": "Document processing from Google Drive started"}

@app.delete("/api/documents/{document_id}", summary="Remove from index")
def delete_document(document_id: str, db: Session = Depends(get_db)):
    try:
        document = db.query(models.Document).filter(models.Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        db.delete(document)
        db.commit()
        return {"detail": f"Document {document_id} removed from index"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List documents with optional filters
@app.get("/api/documents", summary="List documents with filters")
def list_documents(
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    try:
        query = db.query(models.Document)
        if source_type:
            query = query.filter(models.Document.source_type == source_type)
        if category:
            query = query.filter(models.Document.category == category)
        docs = query.order_by(models.Document.id.desc()).offset(offset).limit(limit).all()
        return {
            "documents": [
                {
                    "id": d.id,
                    "doc_metadata": d.doc_metadata or {},
                    "category": d.category,
                }
                for d in docs
            ],
            "offset": offset,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/refresh/{document_id}", summary="Regenerate summary for 1 document")
def refresh_document(document_id: str, bg: BackgroundTasks, db: Session = Depends(get_db)):
    try:
        document = db.query(models.Document).filter(models.Document.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        def reprocess_document():
            summary_data = summarize_document(document.extracted_text, "")
            
            update_data = {
                'summary': summary_data.get('summary', ''),
                'category': summary_data.get('category', ''),
                'priority': summary_data.get('urgency', 'Normal'),  # Map urgency to priority field
                'sentiment': summary_data.get('sentiment', 'Neutral'),
                'importance': summary_data.get('importance', 'Normal'),
                'keywords': summary_data.get('keywords', [])
            }
            crud.update_document(db, document_id, update_data)
        
        bg.add_task(reprocess_document)
        return {"detail": f"Document {document_id} queued for refresh"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/refresh", summary="Regenerate summary for documents matching filters")
def refresh_documents_by_filter(
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    keywords: Optional[List[str]] = Query(None),
    bg: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    try:
        # Build query based on filters
        query = db.query(models.Document)
        if source_type:
            query = query.filter(models.Document.source_type == source_type)
        if category:
            query = query.filter(models.Document.category == category)
        if keywords:
            # Filter by keywords (this would need proper JSON query handling)
            pass
        
        documents = query.all()
        
        def reprocess_documents():
            for doc in documents:
                summary_data = summarize_document(doc.extracted_text, "")
                update_data = {
                    'summary': summary_data.get('summary', ''),
                    'category': summary_data.get('category', ''),
                    'priority': summary_data.get('urgency', 'Normal'),  # Map urgency to priority field
                    'sentiment': summary_data.get('sentiment', 'Neutral'),
                    'importance': summary_data.get('importance', 'Normal'),
                    'keywords': summary_data.get('keywords', [])
                }
                crud.update_document(db, doc.id, update_data)
        
        bg.add_task(reprocess_documents)
        return {"detail": f"Queued refresh for {len(documents)} documents"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Processing queue endpoints
@app.get("/api/processing_queue/count", summary="Count of items in processing queue")
def get_processing_queue_count(status: str = "pending", db: Session = Depends(get_db)):
    try:
        count = crud.get_processing_queue_count(db, status)
        return {"count": count, "status": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/processing_queue/list", summary="List processing queue items")
def get_processing_queue_list(
    offset: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    try:
        items = crud.get_processing_queue_items(db, limit, offset)
        return {
            "items": [
                {
                    "id": item.id,
                    "item_id": item.item_id,
                    "item_type": item.item_type,
                    "status": item.status,
                    "created_at": item.created_at.isoformat()
                }
                for item in items
            ],
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Search endpoint
@app.post("/api/search", summary="RAG query endpoint")
def search(q: str):
    try:
        res = query_ragflow(q)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search_get(q: str):
    """Legacy endpoint for compatibility"""
    return search(q)

# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "RAGFlow MVP API"}

# Daily digest endpoint
@app.post("/api/digest/daily", summary="Generate and send daily digest")
def trigger_daily_digest(bg: BackgroundTasks):
    """Generate and send daily digest to tony@ivc-valves.com as specified in requirements."""
    bg.add_task(send_daily_digest)
    return {"detail": "Daily digest generation started"}

# OAuth endpoints for Google authentication
@app.get("/auth/login", summary="Select inbox to authenticate")
def auth_login():
    """Simple HTML page to choose which inbox to authorize."""
    settings = get_settings()
    inboxes = [e.strip() for e in settings.gmail_inboxes.split(',')]
    html = "<h1>Authorize Gmail Access</h1><ul>"
    for inbox in inboxes:
        html += f'<li><a href="/auth/google?email={inbox}">{inbox}</a></li>'
    html += "</ul>"
    return HTMLResponse(content=html)

@app.get("/auth/google", summary="Start Google OAuth flow")
def start_oauth(email: str):
    """Redirect user to Google's OAuth consent screen."""
    from app.auth.oauth import get_authorization_url
    try:
        auth_url = get_authorization_url(email)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/callback", summary="Handle OAuth callback")
def oauth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth callback and store token."""
    from app.auth.oauth import exchange_code_for_token
    try:
        email = state if state else ""
        token_info = exchange_code_for_token(code, email)
        html = f"<h3>Authentication successful for {email}</h3>"
        return HTMLResponse(content=html)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/status", summary="Check authentication status")
def auth_status():
    """Check if valid authentication credentials exist."""
    from app.auth.oauth import refresh_token_if_needed
    try:
        is_valid = refresh_token_if_needed()
        return {"authenticated": is_valid}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

# Queue status endpoint
@app.get("/api/queue/status", summary="Get background queue status")
def get_queue_status():
    """Get status of background processing queues."""
    try:
        from app.queue.tasks import get_queue_status
        status = get_queue_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Scheduler status endpoint
@app.get("/api/scheduler/status", summary="Get scheduler status")
def get_scheduler_status_endpoint():
    """Get status of background scheduler and scheduled jobs."""
    try:
        status = get_scheduler_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
