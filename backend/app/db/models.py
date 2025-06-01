from sqlalchemy import Column, String, Text, Boolean, DateTime, Integer, JSON, ForeignKey, ARRAY, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import TIMESTAMP
import uuid, datetime

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class Email(Base):
    __tablename__ = "emails"
    
    email_id = Column(String, primary_key=True, default=gen_uuid)  # UUID PRIMARY KEY
    message_id = Column(String(255), nullable=False)  # Gmail message ID
    thread_id = Column(String(16), nullable=False)  # Gmail thread ID
    subject = Column(Text)
    body = Column(Text)
    sender = Column(String(255))  # email id and/or name
    recipients = Column(ARRAY(String))  # email id and/or name as TEXT[]
    date = Column(TIMESTAMP(timezone=True))  # TIMESTAMP WITH TIME ZONE
    labels = Column(ARRAY(String(50)))  # inbox/sent/draft etc. as VARCHAR(50)[]
    attachments = Column(JSON)  # e.g., { attachment_id:123, filename: "file.pdf", gdrive_id: "xyz", size:1540}
    summary = Column(Text)
    category = Column(String(50))
    priority = Column(String(50))  # Urgent / Normal / Low Priority (using 'priority' as per updated requirements)
    sentiment = Column(String(50))  # Positive / Neutral / Negative  
    importance = Column(String(50))  # Very Important / Normal / Low Importance
    keywords = Column(ARRAY(String))  # Array of keywords as TEXT[]
    processed = Column(Boolean, default=False)
    rfc822_hash = Column(String(64))  # SHA-256 hash of full RFC-822 headers for deduplication
    
    # Relationship to recipients
    email_recipients = relationship("EmailRecipient", back_populates="email")
    
    # Prevent duplicate emails - one copy even if CC'ed to multiple internal recipients
    __table_args__ = (UniqueConstraint('rfc822_hash', name='unique_email_content'),)

class EmailAttachment(Base):
    __tablename__ = "email_attachments"
    
    attachment_id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, ForeignKey('emails.email_id', ondelete='CASCADE'), nullable=False)
    file_name = Column(String(255))
    mime_type = Column(String(100))
    gdrive_id = Column(String(44))  # Google Drive file ID
    size = Column(Integer)
    content = Column(Text)  # Extracted text content for RAGFlow indexing
    processed = Column(Boolean, default=False)  # Set to TRUE once OCR done or if no OCR needed

class Inbox(Base):
    __tablename__ = "inboxes"
    
    inbox_id = Column(Integer, primary_key=True, autoincrement=True)
    email_address = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    oauth_token = Column(Text)  # Encrypted OAuth refresh token
    token_expires_at = Column(TIMESTAMP(timezone=True))  # Token expiration
    last_history_id = Column(String(50))  # Gmail history ID for incremental sync
    
    # Relationship to recipients
    email_recipients = relationship("EmailRecipient", back_populates="inbox")

class EmailRecipient(Base):
    __tablename__ = "email_recipients"
    
    email_id = Column(String, ForeignKey('emails.email_id', ondelete='CASCADE'), primary_key=True)
    inbox_id = Column(Integer, ForeignKey('inboxes.inbox_id', ondelete='CASCADE'), primary_key=True)
    
    # Relationships
    email = relationship("Email", back_populates="email_recipients")
    inbox = relationship("Inbox", back_populates="email_recipients")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=gen_uuid)  # UUID PRIMARY KEY
    gdrive_id = Column(String(44))  # Google Drive file ID
    source_type = Column(String(50))  # pdf/doc/ocr_pdf/xls/jpg etc.
    extracted_text = Column(Text)
    summary = Column(Text)
    doc_metadata = Column(JSON)  # filename, author, pages, keywords, size
    category = Column(String(50))
    priority = Column(String(50))  # Urgent / Normal / Low Priority (using 'priority' as per updated requirements)
    sentiment = Column(String(50))  # Positive / Neutral / Negative
    importance = Column(String(50))  # Very Important / Normal / Low Importance
    keywords = Column(ARRAY(String))  # Array of keywords as TEXT[]
    processed = Column(Boolean, default=False)

class ProcessingQueue(Base):
    __tablename__ = "processing_queue"
    
    id = Column(String, primary_key=True, default=gen_uuid)
    item_id = Column(String)  # email/doc ID
    item_type = Column(String(10))  # 'email' or 'doc'
    status = Column(String(15))  # pending/processing/completed
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.datetime.utcnow)
