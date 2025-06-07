from sqlalchemy.orm import Session
from app.db import models
from typing import List, Dict, Any, Optional

# Email operations
def get_email_by_msgid(db: Session, msg_id: str):
    return db.query(models.Email).filter(models.Email.message_id == msg_id).first()

def get_email_by_rfc822_hash(db: Session, rfc822_hash: str):
    return db.query(models.Email).filter(models.Email.rfc822_hash == rfc822_hash).first()

def create_email(db: Session, email_obj: dict):
    db_email = models.Email(**email_obj)
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email

def update_email(db: Session, email_id: str, update_data: dict):
    db_email = db.query(models.Email).filter(models.Email.email_id == email_id).first()
    if db_email:
        for key, value in update_data.items():
            setattr(db_email, key, value)
        db.commit()
        db.refresh(db_email)
    return db_email

def get_emails_by_inbox(db: Session, inbox_address: str, limit: int = 100, offset: int = 0):
    return db.query(models.Email).join(models.EmailRecipient).join(models.Inbox)\
        .filter(models.Inbox.email_address == inbox_address)\
        .offset(offset).limit(limit).all()

def get_emails_by_category(db: Session, category: str, limit: int = 100, offset: int = 0):
    return db.query(models.Email).filter(models.Email.category == category)\
        .offset(offset).limit(limit).all()

# Inbox operations
def get_or_create_inbox(db: Session, email_address: str, description: str = ""):
    inbox = db.query(models.Inbox).filter(models.Inbox.email_address == email_address).first()
    if not inbox:
        inbox = models.Inbox(email_address=email_address, description=description)
        db.add(inbox)
        db.commit()
        db.refresh(inbox)
    return inbox

def get_all_inboxes(db: Session):
    return db.query(models.Inbox).all()

# Email recipient operations
def create_email_recipient(db: Session, email_id: str, inbox_id: int):
    recipient = models.EmailRecipient(email_id=email_id, inbox_id=inbox_id)
    db.add(recipient)
    db.commit()
    return recipient

# Attachment operations
def create_email_attachment(db: Session, attachment_data: dict):
    attachment = models.EmailAttachment(**attachment_data)
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment

def get_attachments_by_email(db: Session, email_id: str):
    return db.query(models.EmailAttachment).filter(models.EmailAttachment.email_id == email_id).all()

# Document operations
def create_document(db: Session, document_obj: dict):
    db_document = models.Document(**document_obj)
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    return db_document

def get_document_by_gdrive_id(db: Session, gdrive_id: str):
    return db.query(models.Document).filter(models.Document.gdrive_id == gdrive_id).first()

def get_documents_by_category(db: Session, category: str, limit: int = 100, offset: int = 0):
    return db.query(models.Document).filter(models.Document.category == category)\
        .offset(offset).limit(limit).all()

def update_document(db: Session, document_id: str, update_data: dict):
    db_document = db.query(models.Document).filter(models.Document.doc_id == document_id).first()
    if db_document:
        for key, value in update_data.items():
            setattr(db_document, key, value)
        db.commit()
        db.refresh(db_document)
    return db_document

# Processing queue operations
def add_to_processing_queue(db: Session, item_id: str, item_type: str):
    queue_item = models.ProcessingQueue(
        item_id=item_id,
        item_type=item_type,
        status='pending'
    )
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)
    return queue_item

def get_processing_queue_count(db: Session, status: str = 'pending'):
    return db.query(models.ProcessingQueue).filter(models.ProcessingQueue.status == status).count()

def get_processing_queue_items(db: Session, limit: int = 100, offset: int = 0):
    return db.query(models.ProcessingQueue)\
        .order_by(models.ProcessingQueue.created_at.desc())\
        .offset(offset).limit(limit).all()

def update_processing_queue_status(db: Session, queue_id: str, status: str):
    queue_item = db.query(models.ProcessingQueue).filter(models.ProcessingQueue.id == queue_id).first()
    if queue_item:
        queue_item.status = status
        db.commit()
        db.refresh(queue_item)
    return queue_item

def get_next_pending_item(db: Session, item_type: Optional[str] = None):
    query = db.query(models.ProcessingQueue).filter(models.ProcessingQueue.status == 'pending')
    if item_type:
        query = query.filter(models.ProcessingQueue.item_type == item_type)
    return query.order_by(models.ProcessingQueue.created_at.asc()).first()
