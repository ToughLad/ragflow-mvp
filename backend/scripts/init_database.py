#!/usr/bin/env python3
"""
Database initialization script for RAGFlow MVP.
Creates all tables and sets up initial data.
"""

import logging
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.db.database import engine, SessionLocal
from app.db.models import Base
from app.db import crud
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_schema():
    """Create all database tables."""
    logger.info("Creating database schema...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database schema created successfully!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create database schema: {e}")
        return False

def setup_initial_inboxes():
    """Set up the initial inbox sequence."""
    logger.info("Setting up initial inboxes...")
    
    settings = get_settings()
    db = SessionLocal()
    
    try:
        # Create inboxes in the specified sequence
        for email_address in settings.inbox_sequence:
            description = f"IVC Inbox for {email_address}"
            inbox = crud.get_or_create_inbox(db, email_address, description)
            logger.info(f"✅ Created/verified inbox: {email_address}")
        
        logger.info("✅ All inboxes set up successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to set up inboxes: {e}")
        return False
    finally:
        db.close()

def verify_database_connection():
    """Verify database connection and tables."""
    logger.info("Verifying database connection...")
    
    try:
        db = SessionLocal()
        
        # Test basic queries
        inboxes = crud.get_all_inboxes(db)
        logger.info(f"✅ Database connection verified. Found {len(inboxes)} inboxes.")
        
        db.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False

def main():
    """Main initialization function."""
    logger.info("🚀 Starting RAGFlow MVP database initialization...")
    
    # Step 1: Create schema
    if not create_database_schema():
        sys.exit(1)
    
    # Step 2: Set up initial data
    if not setup_initial_inboxes():
        sys.exit(1)
    
    # Step 3: Verify everything works
    if not verify_database_connection():
        sys.exit(1)
    
    logger.info("🎉 Database initialization completed successfully!")
    logger.info("Your RAGFlow MVP database is ready to go!")

if __name__ == "__main__":
    main() 