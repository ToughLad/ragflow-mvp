import logging
import os
import base64
import json
import hashlib
import email
import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from email.utils import parsedate_to_datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from app.config import get_settings
from app.auth.oauth import get_service_for_email, refresh_token_if_needed
from app.db import SessionLocal, models, crud
from app.llm.summarizer import summarize_email, summarize_attachment, clean_ocr_text
from app.ragflow.client import push_text, get_or_create_kb
from app.ingest.drive_uploader import upload_attachment_to_drive

log = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def generate_rfc822_hash(headers: Dict[str, str], body: str) -> str:
    """Generate SHA-256 hash of RFC-822 headers for email deduplication."""
    # Create canonical representation of email headers
    canonical_headers = []
    
    # Use key headers for deduplication - Message-ID is the most reliable
    key_headers = ['Message-ID', 'Date', 'From', 'To', 'Subject']
    
    for header in key_headers:
        if header in headers:
            canonical_headers.append(f"{header}: {headers[header]}")
    
    # Add first 500 chars of body to handle forwarded emails
    canonical_content = "\n".join(canonical_headers) + "\n" + body[:500]
    
    return hashlib.sha256(canonical_content.encode('utf-8')).hexdigest()

def _get_service(token_path="token.json"):
    settings = get_settings()
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            # Save the refreshed token
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            raise RuntimeError("Provide a valid Gmail OAuth token.json file.")
    service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
    return service

def extract_email_body(payload: Dict[str, Any]) -> str:
    """Extract email body from Gmail API payload, handling both plain text and HTML."""
    def extract_body_recursive(parts):
        text_body = ''
        html_body = ''
        for p in parts:
            if p.get('parts'):
                t, h = extract_body_recursive(p['parts'])
                text_body += t
                html_body += h
            elif p['mimeType'] == 'text/plain' and p['body'].get('data'):
                body_bytes = base64.urlsafe_b64decode(p['body']['data'])
                text_body += body_bytes.decode('utf-8', errors='ignore')
            elif p['mimeType'] == 'text/html' and p['body'].get('data'):
                body_bytes = base64.urlsafe_b64decode(p['body']['data'])
                html_body += body_bytes.decode('utf-8', errors='ignore')
        return text_body, html_body
    
    # Handle simple body
    if payload.get('body', {}).get('data'):
        body_bytes = base64.urlsafe_b64decode(payload['body']['data'])
        return body_bytes.decode('utf-8', errors='ignore')
    
    # Handle multipart
    parts = payload.get('parts', [])
    if parts:
        text_body, html_body = extract_body_recursive(parts)
        return text_body if text_body else html_body
    
    return ''

def strip_disclaimer(text: str) -> str:
    """Remove disclaimer or virus warning sections from email body."""
    lowered = text.lower()
    patterns = ["disclaimer:", "warning:"]
    for p in patterns:
        idx = lowered.find(p)
        if idx != -1:
            return text[:idx].strip()
    return text.strip()

def process_attachments(service, user_id: str, message_id: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Process email attachments, upload to Google Drive and extract text content."""
    attachments = []
    
    def find_attachments_recursive(parts):
        for part in parts:
            if part.get('parts'):
                find_attachments_recursive(part['parts'])
            elif part.get('body', {}).get('attachmentId'):
                attachments.append({
                    'filename': part.get('filename', 'unknown'),
                    'mimeType': part.get('mimeType', 'application/octet-stream'),
                    'attachmentId': part['body']['attachmentId'],
                    'size': part['body'].get('size', 0)
                })
    
    find_attachments_recursive(payload.get('parts', []))
    
    processed_attachments = []
    for att in attachments:
        try:
            # Download attachment from Gmail
            attachment = service.users().messages().attachments().get(
                userId=user_id, messageId=message_id, id=att['attachmentId']
            ).execute()
            
            # Decode attachment data
            file_data = base64.urlsafe_b64decode(attachment['data'])
            
            # Upload to Google Drive folder "RAG-Email Attachments"
            gdrive_id = upload_attachment_to_drive(
                file_data, 
                att['filename'], 
                att['mimeType']
            )
            
            # Extract text content based on file type
            content = ""
            mime_type = att['mimeType'].lower()
            
            if mime_type.startswith('text/'):
                # Text files
                content = file_data.decode('utf-8', errors='ignore')
            elif mime_type == 'application/pdf':
                # PDF files - use OCR
                try:
                    from app.ocr.ocr_cleaner import extract_text_from_pdf_bytes
                    from app.llm.summarizer import clean_ocr_text
                    raw_text = extract_text_from_pdf_bytes(file_data)
                    # Clean up OCR output for better summaries
                    content = clean_ocr_text(raw_text)
                except Exception as e:
                    log.warning(f"Failed to extract text from PDF {att['filename']}: {e}")
                    content = ""
            elif mime_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # Word documents - would need python-docx
                log.info(f"Word document processing not implemented for {att['filename']}")
                content = ""
            elif mime_type.startswith('image/'):
                # Image files - use OCR
                try:
                    import pytesseract
                    from PIL import Image
                    from io import BytesIO
                    from app.llm.summarizer import clean_ocr_text
                    
                    image = Image.open(BytesIO(file_data))
                    raw_text = pytesseract.image_to_string(image)
                    # Clean up OCR output for better summaries
                    content = clean_ocr_text(raw_text)
                except Exception as e:
                    log.warning(f"Failed to extract text from image {att['filename']}: {e}")
                    content = ""
            
            processed_attachments.append({
                'filename': att['filename'],
                'mime_type': att['mimeType'],
                'size': att['size'],
                'gdrive_id': gdrive_id,
                'content': content  # Extracted text for RAGFlow indexing
            })
            
        except Exception as e:
            log.error(f"Failed to process attachment {att['filename']}: {e}")
            processed_attachments.append({
                'filename': att['filename'],
                'mime_type': att['mimeType'],
                'size': att['size'],
                'gdrive_id': None,
                'content': "",
                'error': str(e)
            })
    
    return processed_attachments

def fetch_and_process():
    """Fetch emails from all configured inboxes and process them."""
    settings = get_settings()
    
    # Inbox sequence is processed in this order
    inbox_sequence = [
        "storesnproduction@ivc-valves.com",  # 60 MB
        "hr.ivcvalves@gmail.com",           # inbox 851, sent 546 - personal Gmail ID for testing
        "umesh.jadhav@ivc-valves.com",      # 0.5 GB
        "arpatil@ivc-valves.com",           # 0.7 GB
        "exports@ivc-valves.com",           # 1.5 GB
        "sumit.basu@ivc-valves.com",        # 1.6 GB
        "hr@ivc-valves.com"                 # 1.7 GB
    ]
    
    db = SessionLocal()
    
    try:
        for inbox in inbox_sequence:
            log.info(f"Processing inbox: {inbox}")
            
            try:
                # Get Gmail service for this specific email (handles domain-wide vs OAuth)
                service = get_service_for_email(inbox)
                
                # Create or get inbox record
                db_inbox = crud.get_or_create_inbox(db, inbox, f"Inbox for {inbox}")
                
                # Create knowledge base for this inbox in RAGFlow
                kb_name = f"inbox_{inbox.replace('@', '_at_').replace('.', '_')}"
                kb_id = get_or_create_kb(
                    kb_name=kb_name,
                    description=f"Knowledge base for emails from {inbox}"
                )
                
                # Fetch recent messages (last 24 hours for incremental processing)
                # For initial load, we might want to fetch more historical data
                query = f"newer_than:1d"
                res = service.users().messages().list(
                    userId=inbox if inbox.endswith('@ivc-valves.com') else 'me',
                    q=query,
                    maxResults=100  # Increased for better coverage
                ).execute()
                
                messages = res.get('messages', [])
                log.info(f"Found {len(messages)} messages in {inbox}")
                
                for msg_meta in messages:
                    msg_id = msg_meta['id']
                    
                    # Check for duplication - avoid storing same email multiple times
                    # if CC'ed to multiple internal recipients
                    if crud.get_email_by_msgid(db, msg_id):
                        continue
                    
                    try:
                        # Fetch full message
                        msg = service.users().messages().get(
                            userId=inbox if inbox.endswith('@ivc-valves.com') else 'me',
                            id=msg_id,
                            format='full'
                        ).execute()
                        
                        # Extract headers
                        headers = {h['name']: h['value'] for h in msg['payload']['headers']}
                        
                        # Parse date with better error handling
                        date_str = headers.get('Date')
                        date = None
                        if date_str:
                            try:
                                date = parsedate_to_datetime(date_str)
                            except Exception as e:
                                log.warning(f"Failed to parse date: {date_str}, error: {e}")
                                try:
                                    # Fallback parsing
                                    date = datetime.datetime.strptime(date_str[:25], '%a, %d %b %Y %H:%M:%S')
                                except:
                                    date = None
                        
                        # Extract body with improved handling and strip disclaimers
                        body = extract_email_body(msg['payload'])
                        body = strip_disclaimer(body)
                        
                        # Extract recipients
                        to_list = []
                        cc_list = []
                        recipients = []
                        if headers.get('To'):
                            to_list = [r.strip() for r in headers['To'].split(',')]
                            recipients.extend(to_list)
                        if headers.get('Cc'):
                            cc_list = [r.strip() for r in headers['Cc'].split(',')]
                            recipients.extend(cc_list)
                        if headers.get('Bcc'):
                            recipients.extend([r.strip() for r in headers['Bcc'].split(',')])
                        
                        # Process attachments first
                        attachments_data = []
                        if msg['payload'].get('parts'):
                            attachments_data = process_attachments(
                                service, 
                                inbox if inbox.endswith('@ivc-valves.com') else 'me',
                                msg_id, 
                                msg['payload']
                            )
                        
                        # Generate RFC-822 hash for deduplication
                        rfc822_hash = generate_rfc822_hash(headers, body)
                        
                        # Check for duplication using RFC-822 hash instead of just message_id
                        if crud.get_email_by_rfc822_hash(db, rfc822_hash):
                            log.info(f"Skipping duplicate email: {msg_id}")
                            continue
                        
                        # Create email object
                        email_data = {
                            'message_id': msg_id,
                            'thread_id': msg['threadId'],
                            'subject': headers.get('Subject', ''),
                            'body': body,
                            'sender': headers.get('From', ''),
                            'to': to_list,
                            'cc': cc_list,
                            'date': date,
                            'labels': msg.get('labelIds', []),
                            'attachments': attachments_data,
                            'rfc822_hash': rfc822_hash,  # Add hash for deduplication
                            'processed': False
                        }
                        
                        # Save email to database
                        db_email = crud.create_email(db, email_data)
                        
                        # Create email recipient record for avoiding duplication
                        crud.create_email_recipient(db, db_email.email_id, db_inbox.inbox_id)
                        
                        # Summarize the email using the configured prompt
                        if body.strip():
                            summary_data = summarize_email(
                                from_email=email_data['sender'],
                                to_list=to_list,
                                cc_list=cc_list,
                                subject=email_data['subject'],
                                date_str=date.isoformat() if date else '',
                                body=body,
                                email_id=inbox,
                            )
                            
                            # Update email with summary data using priority instead of urgency
                            db_email.summary = summary_data.get('summary', '')
                            db_email.category = summary_data.get('category', '')
                            db_email.priority = summary_data.get('urgency', 'Normal')  # Map urgency to priority
                            db_email.sentiment = summary_data.get('sentiment', 'Neutral')
                            db_email.importance = summary_data.get('importance', 'Normal')
                            db_email.keywords = summary_data.get('keywords', [])
                            
                            # Push to RAGFlow with proper metadata
                            push_text(
                                kb_name=kb_name,
                                text=f"{email_data['subject']}\n\n{body}\n\nSummary: {db_email.summary}",
                                metadata={
                                    'email_id': db_email.email_id,
                                    'message_id': msg_id,
                                    'sender': email_data['sender'],
                                    'date': date.isoformat() if date else None,
                                    'category': db_email.category,
                                    'priority': db_email.priority,
                                    'inbox': inbox,
                                    'type': 'email'
                                }
                            )
                        
                        # Process attachment summaries
                        for attachment in attachments_data:
                            if attachment.get('gdrive_id') and attachment.get('content'):
                                att_summary = summarize_attachment(attachment['content'], inbox)
                                # Store attachment data in database with summary fields
                                crud.create_email_attachment(db, {
                                    'email_id': db_email.email_id,
                                    'file_name': attachment['filename'],
                                    'mime_type': attachment['mime_type'],
                                    'gdrive_id': attachment['gdrive_id'],
                                    'size': attachment.get('size', 0),
                                    'content': attachment['content'],
                                    'summary': att_summary.get('summary', ''),
                                    'category': att_summary.get('category', ''),
                                    'priority': att_summary.get('urgency', 'Normal'),
                                    'sentiment': att_summary.get('sentiment', 'Neutral'),
                                    'importance': att_summary.get('importance', 'Normal'),
                                    'keywords': att_summary.get('keywords', []),
                                    'processed': True
                                })
                                
                                # Push attachment to RAGFlow
                                push_text(
                                    kb_name=kb_name,
                                    text=f"Attachment: {attachment['filename']}\n\n{attachment['content']}\n\nSummary: {att_summary.get('summary', '')}",
                                    metadata={
                                        'email_id': db_email.email_id,
                                        'attachment_filename': attachment['filename'],
                                        'gdrive_id': attachment['gdrive_id'],
                                        'category': att_summary.get('category', ''),
                                        'priority': att_summary.get('urgency', 'Normal'),
                                        'inbox': inbox,
                                        'type': 'email_attachment'
                                    }
                                )
                        
                        db_email.processed = True
                        db.commit()
                        
                        log.info(f"Processed email {msg_id} from {inbox}")
                        
                    except Exception as e:
                        log.error(f"Failed to process message {msg_id} from {inbox}: {e}")
                        db.rollback()
                        continue
                        
            except HttpError as e:
                log.error(f"Gmail API error for inbox {inbox}: {e}")
                continue
            except Exception as e:
                log.error(f"General error processing inbox {inbox}: {e}")
                continue
                
    except Exception as e:
        log.error(f"Fatal error in fetch_and_process: {e}")
    finally:
        db.close()

def get_last_history_id(db: Session, inbox: str) -> str:
    """Get the last stored history ID for an inbox to enable incremental fetching."""
    # Check if we have a metadata table or use a simple approach with inbox table
    inbox_record = crud.get_or_create_inbox(db, inbox)
    # For now, return None to fetch all recent emails
    # In production, we would store historyId in inbox metadata
    return None

def store_history_id(db: Session, inbox: str, history_id: str):
    """Store the latest history ID for an inbox."""
    # In production implementation, we would store this in inbox metadata
    # For now, we'll log it for future implementation
    log.info(f"Would store history ID {history_id} for inbox {inbox}")

def fetch_incremental_emails(service, inbox: str, history_id: str = None) -> List[Dict]:
    """Fetch emails using Gmail history API for incremental updates."""
    try:
        if history_id:
            # Use history API for incremental fetch
            history_response = service.users().history().list(
                userId=inbox if inbox.endswith('@ivc-valves.com') else 'me',
                startHistoryId=history_id
            ).execute()
            
            changes = history_response.get('history', [])
            message_ids = set()
            
            for change in changes:
                # Extract message IDs from history changes
                if 'messagesAdded' in change:
                    for msg_added in change['messagesAdded']:
                        message_ids.add(msg_added['message']['id'])
            
            return list(message_ids)
        else:
            # Fallback to regular search for recent messages
            results = service.users().messages().list(
                userId=inbox if inbox.endswith('@ivc-valves.com') else 'me',
                q="newer_than:1d",
                maxResults=100
            ).execute()
            
            messages = results.get('messages', [])
            return [msg['id'] for msg in messages]
            
    except Exception as e:
        log.error(f"Error in incremental email fetch for {inbox}: {e}")
        return []
