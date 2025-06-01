"""
Daily digest scheduler using APScheduler.
Automatically triggers daily digest generation at configured time.
"""
import logging
import asyncio
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import get_settings
from app.queue.tasks import enqueue_daily_digest, enqueue_email_processing, enqueue_document_processing, enqueue_document_monitoring

log = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    """Start the scheduler for background tasks."""
    settings = get_settings()
    
    try:
        # Parse digest time (format: HH:MM)
        digest_hour, digest_minute = map(int, settings.digest_time.split(':'))
        
        # Schedule daily digest
        scheduler.add_job(
            func=trigger_daily_digest,
            trigger=CronTrigger(hour=digest_hour, minute=digest_minute),
            id='daily_digest',
            name='Daily Email Digest',
            replace_existing=True
        )
        
        # Schedule email processing every 30 minutes
        scheduler.add_job(
            func=trigger_email_processing,
            trigger=CronTrigger(minute='*/30'),
            id='email_processing',
            name='Email Processing',
            replace_existing=True
        )
        
        # Schedule document monitoring every hour
        scheduler.add_job(
            func=trigger_document_monitoring,
            trigger=CronTrigger(minute=0),
            id='document_monitoring',
            name='Document Monitoring',
            replace_existing=True
        )
        
        # Schedule document processing every 2 hours
        scheduler.add_job(
            func=trigger_document_processing,
            trigger=CronTrigger(minute=0, hour='*/2'),
            id='document_processing',
            name='Document Processing',
            replace_existing=True
        )
        
        scheduler.start()
        log.info(f"Scheduler started successfully. Daily digest scheduled at {settings.digest_time}")
        
    except Exception as e:
        log.error(f"Failed to start scheduler: {e}")

def stop_scheduler():
    """Stop the scheduler."""
    try:
        if scheduler.running:
            scheduler.shutdown()
            log.info("Scheduler stopped successfully")
    except Exception as e:
        log.error(f"Failed to stop scheduler: {e}")

async def trigger_daily_digest():
    """Trigger daily digest generation."""
    try:
        job_id = enqueue_daily_digest()
        log.info(f"Daily digest job queued: {job_id}")
    except Exception as e:
        log.error(f"Failed to queue daily digest: {e}")

async def trigger_email_processing():
    """Trigger email processing."""
    try:
        job_id = enqueue_email_processing()
        log.info(f"Email processing job queued: {job_id}")
    except Exception as e:
        log.error(f"Failed to queue email processing: {e}")

async def trigger_document_monitoring():
    """Trigger document monitoring for new files."""
    try:
        job_id = enqueue_document_monitoring()
        log.info(f"Document monitoring job queued: {job_id}")
    except Exception as e:
        log.error(f"Failed to queue document monitoring: {e}")

async def trigger_document_processing():
    """Trigger document processing."""
    try:
        job_id = enqueue_document_processing()
        log.info(f"Document processing job queued: {job_id}")
    except Exception as e:
        log.error(f"Failed to queue document processing: {e}")

def get_scheduler_status():
    """Get current scheduler status."""
    if not scheduler.running:
        return {"status": "stopped", "jobs": []}
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running",
        "jobs": jobs
    }
