#!/usr/bin/env bash
set -e

echo "Starting RQ worker for email, document, and digest processing..."

# Run the worker
python -m app.queue.tasks
