"""
API endpoints for system monitoring and status.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db, models
from app.scheduler.daily_scheduler import get_scheduler_status
from app.ragflow.client import list_knowledge_bases

router = APIRouter()

def get_queue_status():
    """Get queue status locally to avoid circular import."""
    try:
        from app.queue.tasks import get_queue_status as _get_queue_status
        return _get_queue_status()
    except ImportError:
        return {
            'email_queue': {'pending': 0, 'failed': 0, 'started': 0},
            'document_queue': {'pending': 0, 'failed': 0, 'started': 0},
            'digest_queue': {'pending': 0, 'failed': 0, 'started': 0}
        }

@router.get("/status")
async def system_status(db: Session = Depends(get_db)):
    """Get overall system status including queue and scheduler status."""
    
    # Get database counts
    total_emails = db.query(models.Email).count()
    processed_emails = db.query(models.Email).filter(models.Email.processed == True).count()
    total_documents = db.query(models.Document).count()
    processed_documents = db.query(models.Document).filter(models.Document.processed == True).count()
    
    # Get queue status
    queue_status = get_queue_status()
    
    # Get scheduler status
    scheduler_status = get_scheduler_status()
    
    # Get knowledge bases
    kb_list = list_knowledge_bases()
    
    return {
        "database": {
            "total_emails": total_emails,
            "processed_emails": processed_emails,
            "total_documents": total_documents,
            "processed_documents": processed_documents
        },
        "queues": queue_status,
        "scheduler": scheduler_status,
        "knowledge_bases": len(kb_list) if isinstance(kb_list, list) else 0,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/emails/recent")
async def recent_emails(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent emails for monitoring."""
    emails = db.query(models.Email).order_by(models.Email.date.desc()).limit(limit).all()
    return [
        {
            "email_id": email.email_id,
            "subject": email.subject,
            "sender": email.sender,
            "date": email.date.isoformat() if email.date else None,
            "processed": email.processed,
            "category": email.category,
            "priority": email.priority
        }
        for email in emails
    ]

@router.get("/documents/recent")
async def recent_documents(limit: int = 50, db: Session = Depends(get_db)):
    """Get recent documents for monitoring."""
    documents = db.query(models.Document).order_by(models.Document.id.desc()).limit(limit).all()
    return [
        {
            "document_id": doc.id,
            "filename": doc.metadata.get('filename', 'Unknown') if doc.metadata else 'Unknown',
            "folder": doc.metadata.get('folder', 'Unknown') if doc.metadata else 'Unknown',
            "processed": doc.processed,
            "category": doc.category,
            "priority": doc.priority
        }
        for doc in documents
    ]
