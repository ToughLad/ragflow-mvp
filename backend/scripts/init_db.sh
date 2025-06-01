#!/usr/bin/env bash
set -e

echo "Initializing database..."

# Create tables using SQLAlchemy
python - <<'PY'
from app.db import models, engine
models.Base.metadata.create_all(bind=engine)
print("Database tables created successfully")
PY

# Insert initial inbox data
python - <<'PY'
from app.db import SessionLocal, crud

db = SessionLocal()
try:
    # Create initial inboxes as per requirements
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
PY

echo "Database initialization completed!"
