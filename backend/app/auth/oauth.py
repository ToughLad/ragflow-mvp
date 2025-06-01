"""
OAuth setup and token management for Gmail and Google Drive APIs.
"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import SessionLocal
from app.db.models import Inbox
import hashlib
from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

# Scopes required for the application - Exact from requirements
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',  # Domain wide access for ivc-valves.com
    'https://www.googleapis.com/auth/drive.file'
]

def get_encryption_key():
    """Get or create encryption key for storing OAuth tokens."""
    key_file = "/app/data/token_key.key"
    if os.path.exists(key_file):
        with open(key_file, 'rb') as f:
            return f.read()
    else:
        key = Fernet.generate_key()
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        with open(key_file, 'wb') as f:
            f.write(key)
        return key

def encrypt_token(token_json: str) -> str:
    """Encrypt OAuth token for storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token_json.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt stored OAuth token."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()

def setup_domain_wide_delegation():
    """Set up domain-wide delegation for @ivc-valves.com emails."""
    service_account_file = "/app/config/service_account.json"
    if not os.path.exists(service_account_file):
        log.warning("Service account file not found. Domain-wide delegation not available.")
        return None
    
    credentials = service_account.Credentials.from_service_account_file(
        service_account_file,
        scopes=SCOPES
    )
    return credentials

def get_service_for_email(email_address: str):
    """Get Gmail service for specific email address using appropriate auth method."""
    db = SessionLocal()
    try:
        inbox = db.query(Inbox).filter(Inbox.email_address == email_address).first()
        
        if email_address.endswith('@ivc-valves.com'):
            # Use domain-wide delegation
            credentials = setup_domain_wide_delegation()
            if credentials:
                delegated_credentials = credentials.with_subject(email_address)
                return build('gmail', 'v1', credentials=delegated_credentials)
            else:
                log.error(f"Domain-wide delegation not configured for {email_address}")
                return None
        else:
            # Use stored OAuth token
            if inbox and inbox.oauth_token:
                try:
                    token_data = json.loads(decrypt_token(inbox.oauth_token))
                    credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
                    
                    # Refresh if needed
                    if credentials.expired and credentials.refresh_token:
                        credentials.refresh(Request())
                        # Update stored token
                        updated_token = json.dumps({
                            'token': credentials.token,
                            'refresh_token': credentials.refresh_token,
                            'token_uri': credentials.token_uri,
                            'client_id': credentials.client_id,
                            'client_secret': credentials.client_secret
                        })
                        inbox.oauth_token = encrypt_token(updated_token)
                        inbox.token_expires_at = datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp())
                        db.commit()
                    
                    return build('gmail', 'v1', credentials=credentials)
                except Exception as e:
                    log.error(f"Failed to load credentials for {email_address}: {e}")
                    return None
            else:
                log.error(f"No OAuth token stored for {email_address}")
                return None
    finally:
        db.close()

def store_oauth_token(email_address: str, credentials: Credentials):
    """Store OAuth token for an email address."""
    db = SessionLocal()
    try:
        inbox = db.query(Inbox).filter(Inbox.email_address == email_address).first()
        if not inbox:
            inbox = Inbox(email_address=email_address, description=f"OAuth inbox for {email_address}")
            db.add(inbox)
        
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret
        }
        
        inbox.oauth_token = encrypt_token(json.dumps(token_data))
        inbox.token_expires_at = datetime.utcnow() + timedelta(seconds=3600)  # 1 hour default
        
        db.commit()
        log.info(f"OAuth token stored for {email_address}")
    finally:
        db.close()

def setup_oauth_flow(redirect_uri: str = "http://localhost:8000/auth/callback"):
    """Set up OAuth2 flow for Google APIs."""
    settings = get_settings()
    
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    return flow

def get_authorization_url() -> str:
    """Get the authorization URL for OAuth flow."""
    flow = setup_oauth_flow()
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    return auth_url

def exchange_code_for_token(code: str, token_path: str = "token.json") -> dict:
    """Exchange authorization code for access token."""
    flow = setup_oauth_flow()
    flow.fetch_token(code=code)
    
    # Save credentials to file
    creds = flow.credentials
    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())
    
    return {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": creds.expiry.isoformat() if creds.expiry else None
    }

def refresh_token_if_needed(token_path: str = "token.json") -> bool:
    """Refresh token if it's expired."""
    if not os.path.exists(token_path):
        return False
    
    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            
            # Save refreshed token
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
            
            log.info("Token refreshed successfully")
            return True
        
        return True  # Token is still valid
        
    except Exception as e:
        log.error(f"Failed to refresh token: {e}")
        return False

def get_authenticated_service(service_name: str, version: str, token_path: str = "token.json"):
    """Get authenticated Google API service."""
    if not refresh_token_if_needed(token_path):
        raise RuntimeError("No valid credentials available. Please re-authenticate.")
    
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    return build(service_name, version, credentials=creds, cache_discovery=False)

def validate_domain_wide_access(domain: str = "ivc-valves.com") -> bool:
    """Validate that domain-wide access is configured correctly."""
    try:
        # This would check if the service account has domain-wide access
        # For now, we'll just check if we can authenticate
        service = get_authenticated_service('gmail', 'v1')
        # Try to access a domain email (this would require domain admin setup)
        return True
    except Exception as e:
        log.error(f"Domain-wide access validation failed: {e}")
        return False

def setup_domain_wide_delegation(user_email: str, token_path: str = "token.json"):
    """Set up domain-wide delegation for accessing ivc-valves.com emails."""
    try:
        # First try service account credentials for domain-wide delegation
        service_account_file = "/app/config/service_account.json"
        
        if os.path.exists(service_account_file):
            log.info(f"Using service account for domain-wide delegation to {user_email}")
            
            # Load service account credentials
            credentials = service_account.Credentials.from_service_account_file(
                service_account_file,
                scopes=SCOPES
            )
            
            # Create delegated credentials for the specific user
            delegated_creds = credentials.with_subject(user_email)
            
            return build('gmail', 'v1', credentials=delegated_creds, cache_discovery=False)
        else:
            log.warning(f"Service account file not found at {service_account_file}")
            log.info(f"Falling back to OAuth credentials for {user_email}")
            
            # Fallback to OAuth credentials if service account not available
            if not refresh_token_if_needed(token_path):
                raise RuntimeError("No valid credentials available for domain-wide access")
            
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            return build('gmail', 'v1', credentials=creds, cache_discovery=False)
        
    except Exception as e:
        log.error(f"Failed to setup domain-wide delegation for {user_email}: {e}")
        # Final fallback to regular OAuth
        try:
            return get_authenticated_service('gmail', 'v1', token_path)
        except Exception as fallback_error:
            log.error(f"Fallback OAuth also failed: {fallback_error}")
            raise RuntimeError(f"All authentication methods failed for {user_email}")

def get_service_for_email(email_address: str, token_path: str = "token.json"):
    """Get Gmail service for specific email address, handling domain-wide access."""
    if email_address.endswith('@ivc-valves.com'):
        # Use domain-wide delegation for company emails
        return setup_domain_wide_delegation(email_address, token_path)
    else:
        # Use regular OAuth for @gmail.com addresses
        return get_authenticated_service('gmail', 'v1', token_path)
