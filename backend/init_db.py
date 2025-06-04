#!/usr/bin/env python3
"""Database initialization script for RAGFlow MVP"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.db import models, engine, SessionLocal
from app.db import crud

def init_database():
    """Initialize database tables and default data"""
    print("Initializing database...")
    
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")
    
    # Insert initial inbox data
    db = SessionLocal()
    try:
        # Create initial inboxes
        inbox_sequence = [
            'storesnproduction@ivc-valves.com',
            'hr.ivcvalves@gmail.com', 
            'umesh.jadhav@ivc-valves.com',
            'arpatil@ivc-valves.com',
            'exports@ivc-valves.com',
            'sumit.basu@ivc-valves.com',
            'hr@ivc-valves.com'
        ]
        
        for email in inbox_sequence:
            inbox = crud.get_or_create_inbox(db, email, f'Inbox for {email}')
            print(f'Created/verified inbox: {email}')
        
        print('Initial inbox data inserted successfully')
    finally:
        db.close()
    
    print("Database initialization completed!")

if __name__ == "__main__":
    init_database()
