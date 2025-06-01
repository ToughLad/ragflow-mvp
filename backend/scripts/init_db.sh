#!/usr/bin/env bash
set -e

echo "Initializing database..."

# Run the Python database initialization script
python ../init_db.py

echo "Database initialization completed!"
