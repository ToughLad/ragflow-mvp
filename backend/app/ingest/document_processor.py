"""
Document processing module for Google Drive integration.
Processes documents from the "RAG-IVC Documents" folder according to requirements.
"""
import logging
import os
from typing import List, Dict, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.config import get_settings
from app.auth.oauth import get_authenticated_service
from app.db import SessionLocal, models, crud
from app.llm.summarizer import summarize_document, clean_ocr_text
from app.ragflow.client import push_text, create_knowledge_base
from app.ingest.drive_uploader import download_file_content

log = logging.getLogger(__name__)

def get_department_from_path(folder_path: str) -> str:
    """Extract department name from folder path for proper categorization."""
    # Each 1st level folder under 'IVC Documents for RAG' maps to department
    parts = folder_path.split('/')
    if len(parts) >= 2:
        return parts[1]  # First level folder name
    return "GENERAL"

def extract_text_from_file(file_data: bytes, filename: str, mime_type: str) -> str:
    """Extract text from various file types using OCR when needed."""
    content = ""
    mime_type = mime_type.lower()
    
    try:
        if mime_type.startswith('text/'):
            # Plain text files
            content = file_data.decode('utf-8', errors='ignore')
            
        elif mime_type == 'application/pdf':
            # PDF files - use OCR with Tesseract as specified
            from app.ocr.ocr_cleaner import extract_text_from_pdf_bytes
            raw_text = extract_text_from_pdf_bytes(file_data)
            content = clean_ocr_text(raw_text)  # LLM cleanup as per requirements
            
        elif mime_type in [
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ]:
            # Word documents
            try:
                import docx
                from io import BytesIO
                doc = docx.Document(BytesIO(file_data))
                content = '\n'.join([paragraph.text for paragraph in doc.paragraphs])
            except Exception as e:
                log.warning(f"Failed to extract text from Word document {filename}: {e}")
                
        elif mime_type in [
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]:
            # Excel files - basic text extraction
            try:
                import pandas as pd
                from io import BytesIO
                df = pd.read_excel(BytesIO(file_data))
                content = df.to_string()
            except Exception as e:
                log.warning(f"Failed to extract text from Excel file {filename}: {e}")
                
        elif mime_type.startswith('image/'):
            # Image files - use OCR with Tesseract as specified
            try:
                import pytesseract
                from PIL import Image
                from io import BytesIO
                
                image = Image.open(BytesIO(file_data))
                raw_text = pytesseract.image_to_string(image)
                content = clean_ocr_text(raw_text)  # LLM cleanup as per requirements
            except Exception as e:
                log.warning(f"Failed to extract text from image {filename}: {e}")
                
        else:
            log.info(f"Unsupported file type for text extraction: {mime_type} ({filename})")
            
    except Exception as e:
        log.error(f"Error extracting text from {filename}: {e}")
        
    return content

def process_drive_folder(folder_id: str, folder_name: str = "", token_path: str = "token.json"):
    """Process documents from a Google Drive folder."""
    try:
        service = get_authenticated_service('drive', 'v3', token_path)
        db = SessionLocal()
        
        # Create knowledge base for this folder/department
        kb_name = f"docs_{folder_name.replace(' ', '_').replace('-', '_').lower()}"
        create_knowledge_base(
            name=kb_name,
            description=f"Knowledge base for documents from {folder_name} department"
        )
        
        # List files in the folder
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, modifiedTime, size, parents)"
        ).execute()
        
        files = results.get('files', [])
        log.info(f"Found {len(files)} files in folder {folder_name}")
        
        for file_info in files:
            file_id = file_info['id']
            filename = file_info['name']
            mime_type = file_info['mimeType']
            
            # Skip if already processed
            if crud.get_document_by_gdrive_id(db, file_id):
                continue
                
            # Skip Google-specific file types that can't be downloaded directly
            if mime_type.startswith('application/vnd.google-apps.'):
                log.info(f"Skipping Google-specific file: {filename}")
                continue
                
            try:
                # Download file content
                file_content = download_file_content(file_id, token_path)
                
                # Extract text content
                extracted_text = extract_text_from_file(file_content, filename, mime_type)
                
                if extracted_text.strip():
                    # Determine department from folder structure
                    department = get_department_from_path(folder_name)
                    
                    # Summarize document using LLM with exact prompt from requirements
                    summary_data = summarize_document(extracted_text, department)
                    
                    # Create document record
                    document_data = {
                        'gdrive_id': file_id,
                        'source_type': mime_type,
                        'extracted_text': extracted_text,
                        'summary': summary_data.get('summary', ''),
                        'metadata': {
                            'filename': filename,
                            'size': file_info.get('size', 0),
                            'department': department,
                            'folder_name': folder_name
                        },
                        'category': summary_data.get('category', ''),
                        'priority': summary_data.get('urgency', 'Normal'),  # Map urgency to priority
                        'sentiment': summary_data.get('sentiment', 'Neutral'),
                        'importance': summary_data.get('importance', 'Normal'),
                        'keywords': summary_data.get('keywords', []),
                        'processed': True
                    }
                    
                    # Save to database
                    db_document = crud.create_document(db, document_data)
                    
                    # Push to RAGFlow
                    push_text(
                        kb_name=kb_name,
                        text=f"Document: {filename}\n\n{extracted_text}\n\nSummary: {summary_data.get('summary', '')}",
                        metadata={
                            'document_id': db_document.id,
                            'gdrive_id': file_id,
                            'filename': filename,
                            'department': department,
                            'category': summary_data.get('category', ''),
                            'priority': summary_data.get('urgency', 'Normal'),
                            'type': 'document'
                        }
                    )
                    
                    log.info(f"Processed document: {filename} from {folder_name}")
                    
                else:
                    log.warning(f"No text extracted from {filename}")
                    
            except Exception as e:
                log.error(f"Failed to process file {filename}: {e}")
                continue
                
        db.close()
        
    except Exception as e:
        log.error(f"Failed to process folder {folder_name}: {e}")

def process_all_documents(token_path: str = "token.json"):
    """Process all documents from the RAG-IVC Documents folder and subfolders."""
    settings = get_settings()
    documents_folder_id = settings.documents_folder_id  # 1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn
    
    try:
        service = get_authenticated_service('drive', 'v3', token_path)
        
        # Get first level subfolders (departments)
        results = service.files().list(
            q=f"'{documents_folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        folders = results.get('files', [])
        log.info(f"Found {len(folders)} department folders to process")
        
        # Process each department folder
        for folder in folders:
            folder_id = folder['id']
            folder_name = folder['name']
            log.info(f"Processing department folder: {folder_name}")
            process_drive_folder(folder_id, folder_name, token_path)
            
        # Also process files directly in the root documents folder
        process_drive_folder(documents_folder_id, "ROOT", token_path)
        
    except Exception as e:
        log.error(f"Failed to process documents: {e}")

def monitor_drive_changes(token_path: str = "token.json"):
    """Monitor Google Drive for new files and folders (for future implementation)."""
    # This would implement the requirement: "As new files or folders are added to Google Drive, 
    # they should be added to the indexing pipeline"
    # Could use Google Drive API's changes.watch() for real-time monitoring
    pass

def monitor_new_documents(token_path: str = "token.json"):
    """Monitor Google Drive for new documents and queue them for processing."""
    settings = get_settings()
    db = SessionLocal()
    try:
        # Authenticate Drive service
        service = get_authenticated_service('drive', 'v3', token_path)
        folder_id = settings.documents_folder_id
        
        # Find files modified in the last hour
        from datetime import datetime, timedelta
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        modified_time = one_hour_ago.isoformat() + 'Z'
        query = f"'{folder_id}' in parents and trashed=false and modifiedTime > '{modified_time}'"
        
        results = service.files().list(
            q=query,
            fields="files(id,name,mimeType,modifiedTime,size)",
            pageSize=100
        ).execute()
        new_files = results.get('files', [])
        
        if not new_files:
            log.info("No new documents found in the last hour")
            return
        
        # Queue each unprocessed file
        for file_info in new_files:
            file_id = file_info['id']
            file_name = file_info.get('name')
            if crud.get_document_by_gdrive_id(db, file_id):
                continue
            crud.add_to_processing_queue(db, file_id, 'document')
            log.info(f"Queued new document for processing: {file_name}")
    except Exception as e:
        log.error(f"Error monitoring new documents: {e}")
    finally:
        db.close()
