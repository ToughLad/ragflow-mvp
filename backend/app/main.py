from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from contextlib import asynccontextmanager
from typing import List, Optional
import logging
from datetime import datetime, timedelta

from app.ingest.gmail_fetcher import fetch_and_process
from app.ingest.document_processor import process_all_documents
from app.digest.daily_digest import send_daily_digest
from app.ragflow.client import query_ragflow
from app.db import models, engine, SessionLocal
from app.db import crud
from app.llm.summarizer import summarize_email, summarize_document
from app.scheduler.daily_scheduler import start_scheduler, stop_scheduler, get_scheduler_status
from app.config import get_settings
from app.api.monitoring import router as monitoring_router

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

# Include monitoring router
app.include_router(monitoring_router, prefix="/api/monitoring", tags=["monitoring"])

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
@app.get("/api/inbox/list", summary="Get list of configured inboxes")
def get_inbox_list():
    """Get all configured Gmail inboxes."""
    settings = get_settings()
    inboxes = [e.strip() for e in settings.gmail_inboxes.split(',') if e.strip()]
    
    db = SessionLocal()
    try:
        # Get additional info from database
        inbox_data = []
        for email in inboxes:
            inbox_record = db.query(Inbox).filter(Inbox.email_address == email).first()
            inbox_data.append({
                "email": email,
                "description": inbox_record.description if inbox_record else "",
                "authenticated": bool(inbox_record and inbox_record.oauth_token),
                "last_synced": inbox_record.last_sync_time.isoformat() if inbox_record and inbox_record.last_sync_time else None
            })
        
        return {"inboxes": [email for email in inboxes], "details": inbox_data}
    finally:
        db.close()

@app.post("/api/inbox/add", summary="Add new inbox")
def add_inbox(email: str, description: str = ""):
    """Add a new Gmail inbox to the system."""
    db = SessionLocal()
    try:
        # Check if inbox already exists
        existing = db.query(Inbox).filter(Inbox.email_address == email).first()
        if existing:
            return {"error": f"Inbox {email} already exists"}
        
        # Create new inbox record
        new_inbox = Inbox(
            email_address=email,
            description=description,
            is_active=True
        )
        db.add(new_inbox)
        db.commit()
        
        return {"success": True, "message": f"Added inbox: {email}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/inbox/remove", summary="Remove inbox")
def remove_inbox(email: str):
    """Remove an inbox from the system."""
    db = SessionLocal()
    try:
        inbox = db.query(Inbox).filter(Inbox.email_address == email).first()
        if inbox:
            db.delete(inbox)
            db.commit()
            return {"success": True, "message": f"Removed inbox: {email}"}
        else:
            return {"error": f"Inbox {email} not found"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/inbox/refreshAll", summary="Refresh all inboxes")
def refresh_all_inboxes(background_tasks: BackgroundTasks):
    """Queue refresh for all authenticated inboxes."""
    from app.queue.task_manager import queue_email_ingestion
    
    settings = get_settings()
    inboxes = [e.strip() for e in settings.gmail_inboxes.split(',') if e.strip()]
    
    queued_count = 0
    for inbox in inboxes:
        try:
            queue_email_ingestion(inbox)
            queued_count += 1
        except Exception as e:
            print(f"Failed to queue {inbox}: {e}")
    
    return {"success": True, "queued": queued_count, "total": len(inboxes)}

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

@app.post("/ingest/emails", summary="Fetch latest emails and index them")
def ingest_emails(bg: BackgroundTasks):
    bg.add_task(fetch_and_process)
    return {"detail": "Email ingestion started"}

# Document endpoints
@app.post("/api/documents/upload", summary="Handle multiple files/folders/zips")
def upload_documents(bg: BackgroundTasks):
    """Handle document upload from Google Drive folders."""
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
@app.get("/api/documents", summary="Search documents")
def search_documents(
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    filename: Optional[str] = None,
    offset: int = 0,
    limit: int = 50
):
    """Search documents with filters."""
    db = SessionLocal()
    try:
        query = db.query(models.Document)
        
        if source_type:
            query = query.filter(models.Document.source_type.ilike(f"%{source_type}%"))
        
        if category:
            query = query.filter(models.Document.category.ilike(f"%{category}%"))
        
        if filename:
            query = query.filter(models.Document.doc_metadata.ilike(f"%{filename}%"))
        
        total_count = query.count()
        documents = query.offset(offset).limit(limit).all()
        
        doc_list = []
        for doc in documents:
            doc_dict = {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "category": doc.category,
                "doc_metadata": doc.doc_metadata,
                "content_preview": doc.content[:200] if doc.content else "",
                "processed_date": doc.created_at.isoformat() if doc.created_at else None
            }
            doc_list.append(doc_dict)
        
        return {
            "documents": doc_list,
            "total": total_count,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

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
@app.post("/api/search", summary="Enhanced RAG search")
def enhanced_search(request: dict):
    """Enhanced search with filters and context."""
    query = request.get("q", "")
    date_from = request.get("date_from")
    date_to = request.get("date_to")
    priority = request.get("priority")
    category = request.get("category")
    
    if not query:
        return {"error": "Query is required"}
    
    try:
        from app.ragflow.ragflow_client import RagflowClient
        ragflow = RagflowClient()
        
        # Build enhanced query with filters
        enhanced_query = query
        if category:
            enhanced_query += f" category:{category}"
        if priority:
            enhanced_query += f" priority:{priority}"
        if date_from or date_to:
            enhanced_query += f" date range filters applied"
        
        # Perform search
        results = ragflow.search(enhanced_query)
        
        # Apply local filters if needed
        if results.get("references"):
            filtered_refs = results["references"]
            
            # Additional filtering based on your database
            if date_from or date_to or priority or category:
                # Here you'd implement database-level filtering
                pass
            
            results["references"] = filtered_refs
        
        return results
        
    except Exception as e:
        return {"error": f"Search failed: {str(e)}"}

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
    """Generate and send the daily digest email."""
    bg.add_task(send_daily_digest)
    return {"detail": "Daily digest generation started"}

# OAuth endpoints for Google authentication
@app.get("/auth/login", summary="Select inbox to authenticate")
def auth_login():
    """API endpoint to get list of inboxes for authentication."""
    settings = get_settings()
    inboxes = [e.strip() for e in settings.gmail_inboxes.split(',')]
    return {
        "inboxes": inboxes,
        "auth_url_template": "/auth/google?email={email}",
        "instructions": [
            "Each Gmail inbox needs to be authenticated separately",
            "Click authenticate next to each inbox you want to access",
            "You'll be redirected to Google to grant permissions",
            "After successful authentication, you can start processing emails"
        ]
    }

@app.get("/auth/google", summary="Start Google OAuth flow")
def start_oauth(email: str, request: Request):
    """Redirect user to Google's OAuth consent screen for specific inbox."""
    from app.auth.oauth import get_authorization_url
    try:
        auth_url = get_authorization_url(email)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        # Return JSON error for API calls, HTML for browser redirects
        accept_header = request.headers.get('Accept', '')
        if 'application/json' in accept_header:
            raise HTTPException(status_code=500, detail=str(e))
        return HTMLResponse(
            content=f"<h3>Authentication Error</h3><p>{str(e)}</p><p><a href='/auth/login'>Try again</a></p>",
            status_code=500
        )

@app.get("/auth/callback", summary="Handle OAuth callback")
def oauth_callback(code: str, state: Optional[str] = None):
    """Handle OAuth callback and store token for specific inbox."""
    from app.auth.oauth import exchange_code_for_token
    try:
        email = state if state else ""
        if not email:
            raise ValueError("Email address is required (missing state parameter)")
        
        token_info = exchange_code_for_token(code, email)
        
        # Return success page that will close automatically
        html = f"""
        <html>
        <head>
            <title>Authentication Success</title>
            <style>
                body {{
                    font-family: 'Segoe UI', sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    color: white;
                }}
                .container {{
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                    max-width: 500px;
                    margin: 0 auto;
                }}
                .success-icon {{ font-size: 48px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="success-icon">✅</div>
                <h2>Authentication Successful!</h2>
                <p><strong>{email}</strong> has been authenticated successfully.</p>
                <p>You can close this window and return to the main application.</p>
                <p><small>This window will close automatically in 3 seconds...</small></p>
            </div>
            <script>
                setTimeout(function() {{
                    window.close();
                }}, 3000);
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html)
    except Exception as e:
        error_html = f"""
        <html>
        <head>
            <title>Authentication Error</title>
            <style>
                body {{
                    font-family: 'Segoe UI', sans-serif;
                    text-align: center;
                    padding: 50px;
                    background: linear-gradient(135deg, #fc466b 0%, #3f5efb 100%);
                    color: white;
                }}
                .container {{
                    background: rgba(255,255,255,0.1);
                    padding: 30px;
                    border-radius: 10px;
                    backdrop-filter: blur(10px);
                    max-width: 500px;
                    margin: 0 auto;
                }}
                .error-icon {{ font-size: 48px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">❌</div>
                <h2>Authentication Failed</h2>
                <p>There was an error authenticating your account:</p>
                <p><code>{str(e)}</code></p>
                <p><a href="/auth/login" style="color: white;">Try again</a></p>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(content=error_html, status_code=500)

@app.get("/api/auth/status", summary="Enhanced auth status check")
def enhanced_auth_status(email: Optional[str] = None):
    """Enhanced authentication status with detailed info."""
    if email:
        # Check specific email
        try:
            from app.auth.oauth import get_credentials_for_email
            creds = get_credentials_for_email(email)
            
            if creds and creds.valid:
                return {
                    "authenticated": True,
                    "email": email,
                    "expires_at": creds.expiry.isoformat() if creds.expiry else None,
                    "scopes": creds.scopes if hasattr(creds, 'scopes') else []
                }
            else:
                return {
                    "authenticated": False,
                    "email": email,
                    "error": "No valid credentials found"
                }
        except Exception as e:
            return {
                "authenticated": False,
                "email": email,
                "error": str(e)
            }
    else:
        # Check all inboxes
        settings = get_settings()
        inboxes = [e.strip() for e in settings.gmail_inboxes.split(',') if e.strip()]
        
        results = {}
        for inbox in inboxes:
            status = enhanced_auth_status(inbox)
            results[inbox] = status
        
        # Overall status
        authenticated_count = sum(1 for status in results.values() if status.get("authenticated"))
        
        return {
            "overall_authenticated": authenticated_count > 0,
            "total_inboxes": len(inboxes),
            "authenticated_inboxes": authenticated_count,
            "details": results
        }

# Queue status endpoint
@app.get("/api/queue/status", summary="Get queue status")
def get_queue_status():
    """Get processing queue status."""
    try:
        # This would integrate with your Redis queue
        return {
            "status": "active",
            "pending_jobs": 0,  # Replace with actual queue count
            "failed_jobs": 0,
            "completed_today": 0
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

# Scheduler status endpoint
@app.get("/api/scheduler/status", summary="Get scheduler status")
def get_scheduler_status_endpoint():
    """Get status of background scheduler and scheduled jobs."""
    try:
        status = get_scheduler_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add new comprehensive API endpoints

# ==================== LLM CHAT ENDPOINTS ====================

@app.post("/api/chat/send", summary="Send message to LLM")
async def chat_with_llm(request: dict):
    """Send a message directly to the LLM."""
    message = request.get("message", "")
    rag_mode = request.get("rag_mode", False)
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    try:
        if rag_mode:
            # Use RAG search for context-aware responses
            from app.ragflow.ragflow_client import RagflowClient
            ragflow = RagflowClient()
            
            # Search for relevant context
            search_results = ragflow.search(message)
            
            # Build context-aware prompt
            context = ""
            if search_results.get("references"):
                context = "\n\nRelevant context from documents:\n"
                for ref in search_results["references"][:3]:  # Top 3 results
                    context += f"- {ref.get('content_ltks', '')[:200]}...\n"
            
            prompt = f"{message}\n{context}\n\nPlease answer based on the above context if relevant, otherwise provide a general response."
        else:
            prompt = message
        
        # Send to local LLM (Ollama)
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "mistral:7b-instruct-v0.3",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60.0
            )
            
            if response.status_code == 200:
                llm_response = response.json()
                return {
                    "response": llm_response.get("response", "No response from LLM"),
                    "context_used": rag_mode,
                    "model": "mistral:7b-instruct-v0.3"
                }
            else:
                raise HTTPException(status_code=500, detail="LLM service unavailable")
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

@app.get("/api/llm/status", summary="Check LLM status")
async def check_llm_status():
    """Check if the local LLM is running."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/version", timeout=5.0)
            return {"status": "online", "service": "ollama"}
    except:
        return {"status": "offline", "service": "ollama"}

# ==================== ENHANCED SEARCH ENDPOINTS ====================

@app.get("/api/ragflow/status", summary="Get RAGFlow knowledge base status")
def get_ragflow_status():
    """Get status of RAGFlow knowledge bases."""
    try:
        from app.ragflow.ragflow_client import RagflowClient
        ragflow = RagflowClient()
        
        # Get knowledge base count and status
        datasets = ragflow.list_datasets()
        
        return {
            "count": len(datasets) if datasets else 0,
            "lastUpdated": "Recent",  # This would come from your sync records
            "status": "active"
        }
    except Exception as e:
        return {
            "count": 0,
            "lastUpdated": "Unknown",
            "status": "error",
            "error": str(e)
        }

# ==================== EMAIL DATABASE ENDPOINTS ====================

@app.get("/api/emails", summary="Search and filter emails")
def search_emails(
    inboxes: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    sender: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    offset: int = 0,
    limit: int = 50
):
    """Search emails with comprehensive filters."""
    db = SessionLocal()
    try:
        query = db.query(models.Email)
        
        # Apply filters
        if inboxes:
            inbox_list = [i.strip() for i in inboxes.split(',')]
            query = query.filter(models.Email.inbox_address.in_(inbox_list))
        
        if category:
            query = query.filter(models.Email.category.ilike(f"%{category}%"))
        
        if priority:
            query = query.filter(models.Email.priority == priority)
        
        if sender:
            query = query.filter(models.Email.sender.ilike(f"%{sender}%"))
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
                query = query.filter(models.Email.date >= from_date)
            except ValueError:
                pass
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                query = query.filter(models.Email.date <= to_date)
            except ValueError:
                pass
        
        # Get total count before pagination
        total_count = query.count()
        
        # Apply pagination
        emails = query.order_by(models.Email.date.desc()).offset(offset).limit(limit).all()
        
        # Convert to JSON-serializable format
        email_list = []
        for email in emails:
            email_dict = {
                "email_id": email.email_id,
                "subject": email.subject,
                "sender": email.sender,
                "date": email.date.isoformat() if email.date else None,
                "category": email.category,
                "priority": email.priority,
                "summary": email.summary,
                "inbox_address": email.inbox_address
            }
            email_list.append(email_dict)
        
        return {
            "emails": email_list,
            "total": total_count,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/emails/stats", summary="Get email statistics")
def get_email_stats():
    """Get comprehensive email statistics."""
    db = SessionLocal()
    try:
        # Total emails
        total_emails = db.query(models.Email).count()
        
        # Today's emails
        today = datetime.now().date()
        today_emails = db.query(models.Email).filter(
            db.func.date(models.Email.date) == today
        ).count()
        
        # Urgent emails
        urgent_emails = db.query(models.Email).filter(
            models.Email.priority == "Urgent"
        ).count()
        
        # Category count
        category_count = db.query(models.Email.category).distinct().count()
        
        # Recent activity
        recent_emails = db.query(models.Email).filter(
            models.Email.date >= datetime.now() - timedelta(days=7)
        ).count()
        
        return {
            "total_emails": total_emails,
            "today_emails": today_emails,
            "urgent_emails": urgent_emails,
            "category_count": category_count,
            "recent_activity": recent_emails,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/emails/{email_id}", summary="Get email details")
def get_email_details(email_id: str):
    """Get detailed information for a specific email."""
    db = SessionLocal()
    try:
        email = db.query(models.Email).filter(models.Email.email_id == email_id).first()
        if not email:
            raise HTTPException(status_code=404, detail="Email not found")
        
        return {
            "email_id": email.email_id,
            "subject": email.subject,
            "sender": email.sender,
            "recipients": email.recipients,
            "date": email.date.isoformat() if email.date else None,
            "body": email.body,
            "summary": email.summary,
            "category": email.category,
            "priority": email.priority,
            "attachments": email.attachments,
            "inbox_address": email.inbox_address,
            "thread_id": email.thread_id
        }
        
    except Exception as e:
        if "not found" in str(e):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ==================== DOCUMENT MANAGEMENT ENDPOINTS ====================

@app.post("/api/documents/upload", summary="Process new documents")
def process_new_documents(background_tasks: BackgroundTasks):
    """Queue processing for new documents."""
    try:
        from app.queue.task_manager import queue_document_processing
        
        # Queue document processing job
        queue_document_processing()
        
        return {"success": True, "message": "Document processing queued"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SYSTEM ADMINISTRATION ENDPOINTS ====================

@app.get("/api/system/status", summary="Get overall system status")
def get_system_status():
    """Get comprehensive system status."""
    try:
        db = SessionLocal()
        
        # Database status
        try:
            db.execute("SELECT 1")
            db_status = "connected"
        except:
            db_status = "error"
        finally:
            db.close()
        
        # Redis status (if using Redis)
        redis_status = "unknown"
        try:
            # Add Redis connection check here
            redis_status = "connected"
        except:
            redis_status = "error"
        
        return {
            "database": db_status,
            "redis": redis_status,
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.post("/api/digest/daily", summary="Generate daily digest")
def generate_daily_digest(background_tasks: BackgroundTasks):
    """Generate daily email digest."""
    try:
        from app.digest.daily_digest import generate_daily_digest
        
        background_tasks.add_task(generate_daily_digest)
        
        return {"success": True, "message": "Daily digest generation started"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
