from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
import os
import io
from app.config import get_settings

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Google Drive folder IDs used by the application
ATTACHMENT_FOLDER_ID = "1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV"  # RAG-Email Attachments
DOCUMENTS_FOLDER_ID = "1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn"   # RAG-IVC Documents

def _get_drive_service(token_path='token.json'):
    """Get authenticated Google Drive service."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            creds.refresh(Request())
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            raise RuntimeError("Provide a valid Google Drive OAuth token.json file.")
    
    return build('drive', 'v3', credentials=creds, cache_discovery=False)

def upload_attachment_to_drive(file_data: bytes, filename: str, mime_type: str, token_path='token.json') -> str:
    """Upload email attachment to the designated Google Drive folder."""
    service = _get_drive_service(token_path)
    
    file_metadata = {
        "name": filename,
        "parents": [ATTACHMENT_FOLDER_ID]
    }
    
    # Create media upload from bytes
    media = MediaIoBaseUpload(
        io.BytesIO(file_data),
        mimetype=mime_type,
        resumable=True
    )
    
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id'
    ).execute()
    
    if not file or 'id' not in file:
        raise RuntimeError(f"Failed to upload {filename} to Google Drive")
    
    return file.get('id')

def upload_file(local_path: str, drive_folder_id: str = None, token_path='token.json') -> str:
    """Upload local file to Google Drive folder."""
    if drive_folder_id is None:
        drive_folder_id = DOCUMENTS_FOLDER_ID
        
    service = _get_drive_service(token_path)
    
    file_metadata = {
        "name": os.path.basename(local_path), 
        "parents": [drive_folder_id]
    }
    
    media = MediaFileUpload(local_path, resumable=True)
    
    file = service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id'
    ).execute()
    
    if not file or 'id' not in file:
        raise RuntimeError(f"Failed to upload {local_path} to Google Drive")
    
    return file.get('id')

def list_drive_folder_contents(folder_id: str, token_path='token.json') -> list:
    """List contents of a Google Drive folder."""
    service = _get_drive_service(token_path)
    
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, modifiedTime, size)"
    ).execute()
    
    return results.get('files', [])

def download_file_content(file_id: str, token_path='token.json') -> bytes:
    """Download file content from Google Drive."""
    service = _get_drive_service(token_path)
    
    file_content = service.files().get_media(fileId=file_id).execute()
    return file_content
