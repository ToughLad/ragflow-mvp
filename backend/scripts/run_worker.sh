#!/usr/bin/env bash
set -e

# Ensure database tables exist before starting
bash $(dirname "$0")/init_db.sh

# Start RQ worker for background tasks
echo "Starting RQ worker for email, document, and digest processing..."

python -m app.queue.tasks
