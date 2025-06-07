#!/usr/bin/env python3
"""
Auto-authentication script for the first Gmail account.
Uses domain-wide delegation for storesnproduction@ivc-valves.com
"""

import logging
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.config import get_settings
from app.db.database import SessionLocal
from app.db import crud
from app.auth.oauth import setup_domain_wide_auth

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_first_gmail_auto_auth():
    """Set up automatic authentication for the first Gmail account."""
    settings = get_settings()
    first_inbox = settings.inbox_sequence[0]  # storesnproduction@ivc-valves.com
    
    logger.info(f"Setting up auto-authentication for: {first_inbox}")
    
    if not first_inbox.endswith("@ivc-valves.com"):
        logger.error(f"❌ First inbox {first_inbox} is not an @ivc-valves.com domain")
        return False
    
    try:
        # Set up domain-wide delegation auth
        success = setup_domain_wide_auth(first_inbox)
        
        if success:
            logger.info(f"✅ Auto-authentication set up for {first_inbox}")
            
            # Update database to mark as authenticated
            db = SessionLocal()
            try:
                inbox = crud.get_or_create_inbox(db, first_inbox, f"Auto-auth inbox for {first_inbox}")
                # Mark as having valid auth (we'll store the domain-wide credentials separately)
                inbox.is_active = True
                db.commit()
                logger.info("✅ Database updated with auth status")
            finally:
                db.close()
            
            return True
        else:
            logger.error(f"❌ Failed to set up auto-authentication for {first_inbox}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error setting up auto-authentication: {e}")
        return False

def verify_first_gmail_access():
    """Verify we can access the first Gmail account."""
    settings = get_settings()
    first_inbox = settings.inbox_sequence[0]
    
    logger.info(f"Verifying access to: {first_inbox}")
    
    try:
        from app.auth.oauth import get_service_for_email
        service = get_service_for_email(first_inbox)
        
        # Test basic access
        profile = service.users().getProfile(userId=first_inbox).execute()
        email_address = profile.get('emailAddress')
        
        if email_address == first_inbox:
            logger.info(f"✅ Successfully verified access to {first_inbox}")
            return True
        else:
            logger.error(f"❌ Email mismatch: expected {first_inbox}, got {email_address}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to verify access to {first_inbox}: {e}")
        return False

def main():
    """Main auto-authentication function."""
    logger.info("🚀 Starting auto-authentication for first Gmail account...")
    
    # Step 1: Set up auto-authentication
    if not setup_first_gmail_auto_auth():
        logger.error("❌ Auto-authentication setup failed")
        sys.exit(1)
    
    # Step 2: Verify access works
    if not verify_first_gmail_access():
        logger.error("❌ Access verification failed")
        sys.exit(1)
    
    logger.info("🎉 Auto-authentication completed successfully!")
    logger.info("The first Gmail account is ready for automatic processing!")

if __name__ == "__main__":
    main() 