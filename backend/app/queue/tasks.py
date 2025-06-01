"""
Background task queue using Redis and RQ for processing emails and documents.
"""
import logging
from rq import Queue, Worker
from redis import Redis
from app.config import get_settings

log = logging.getLogger(__name__)
settings = get_settings()

# Redis connection
redis_conn = Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)

# Task queues
email_queue = Queue('emails', connection=redis_conn)
document_queue = Queue('documents', connection=redis_conn)
digest_queue = Queue('digest', connection=redis_conn)

def enqueue_email_processing():
    """Queue email processing task."""
    from app.ingest.gmail_fetcher import fetch_and_process
    job = email_queue.enqueue(fetch_and_process, job_timeout='30m')
    log.info(f"Queued email processing job: {job.id}")
    return job.id

def enqueue_document_processing():
    """Queue document processing task."""
    from app.ingest.document_processor import process_all_documents
    job = document_queue.enqueue(process_all_documents, job_timeout='60m')
    log.info(f"Queued document processing job: {job.id}")
    return job.id

def enqueue_daily_digest():
    """Queue daily digest generation."""
    from app.digest.daily_digest import send_daily_digest
    job = digest_queue.enqueue(send_daily_digest, job_timeout='10m')
    log.info(f"Queued daily digest job: {job.id}")
    return job.id

def enqueue_document_monitoring():
    """Queue document monitoring task."""
    from app.ingest.document_processor import monitor_new_documents
    job = document_queue.enqueue(monitor_new_documents, job_timeout='15m')
    log.info(f"Queued document monitoring job: {job.id}")
    return job.id

def start_worker(queue_name: str = None):
    """Start a worker for processing background tasks."""
    if queue_name:
        if queue_name == 'emails':
            worker = Worker([email_queue], connection=redis_conn)
        elif queue_name == 'documents':
            worker = Worker([document_queue], connection=redis_conn)
        elif queue_name == 'digest':
            worker = Worker([digest_queue], connection=redis_conn)
        else:
            log.error(f"Unknown queue: {queue_name}")
            return
    else:
        # Worker for all queues
        worker = Worker([email_queue, document_queue, digest_queue], connection=redis_conn)
    
    log.info(f"Starting worker for queue: {queue_name or 'all'}")
    worker.work()

def get_queue_status():
    """Get status of all queues."""
    return {
        'email_queue': {
            'pending': len(email_queue),
            'failed': len(email_queue.failed_job_registry),
            'started': len(email_queue.started_job_registry)
        },
        'document_queue': {
            'pending': len(document_queue),
            'failed': len(document_queue.failed_job_registry),
            'started': len(document_queue.started_job_registry)
        },
        'digest_queue': {
            'pending': len(digest_queue),
            'failed': len(digest_queue.failed_job_registry),
            'started': len(digest_queue.started_job_registry)
        }
    }
