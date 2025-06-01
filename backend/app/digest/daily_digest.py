"""
Daily digest email generation module.
Generates daily email digest sent to tony@ivc-valves.com with summary and highlights 
of the previous 24 hours' emails across all indexed inboxes.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.config import get_settings
from app.db import SessionLocal, models
from app.llm.summarizer import summarize_email

log = logging.getLogger(__name__)

def get_yesterdays_emails(db: Session) -> List[models.Email]:
    """Get all emails from the previous 24 hours across all indexed inboxes."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    today = datetime.utcnow()
    
    emails = db.query(models.Email).filter(
        and_(
            models.Email.date >= yesterday,
            models.Email.date < today,
            models.Email.processed == True
        )
    ).order_by(models.Email.date.desc()).all()
    
    return emails

def categorize_emails_by_importance(emails: List[models.Email]) -> Dict[str, List[models.Email]]:
    """Categorize emails by importance and urgency for digest structure."""
    categorized = {
        'urgent_very_important': [],
        'urgent_normal': [],
        'normal_very_important': [],
        'normal_normal': [],
        'low_priority': []
    }
    
    for email in emails:
        priority = email.priority or 'Normal'
        importance = email.importance or 'Normal'
        
        if priority == 'Urgent' and importance == 'Very Important':
            categorized['urgent_very_important'].append(email)
        elif priority == 'Urgent':
            categorized['urgent_normal'].append(email)
        elif importance == 'Very Important':
            categorized['normal_very_important'].append(email)
        elif priority == 'Normal':
            categorized['normal_normal'].append(email)
        else:
            categorized['low_priority'].append(email)
    
    return categorized

def generate_email_summary_section(emails: List[models.Email], section_title: str) -> str:
    """Generate a summary section for a group of emails."""
    if not emails:
        return ""
    
    html = f"<h3>{section_title} ({len(emails)} emails)</h3>\n"
    
    for email in emails[:10]:  # Limit to top 10 per section
        # Format date
        date_str = email.date.strftime("%Y-%m-%d %H:%M") if email.date else "Unknown date"
        
        # Get inbox from recipients (simplified)
        inbox = "Unknown"
        if email.recipients:
            for recipient in email.recipients:
                if '@ivc-valves.com' in recipient:
                    inbox = recipient
                    break
        
        html += f"""
        <div style="border-left: 3px solid #007BFF; padding-left: 10px; margin: 10px 0;">
            <p><strong>From:</strong> {email.sender}<br>
            <strong>To:</strong> {inbox}<br>
            <strong>Date:</strong> {date_str}<br>
            <strong>Subject:</strong> {email.subject}</p>
            <p><strong>Summary:</strong> {email.summary or 'No summary available'}</p>
            <p><strong>Category:</strong> {email.category or 'Uncategorized'} | 
            <strong>Priority:</strong> {email.priority or 'Normal'} | 
            <strong>Sentiment:</strong> {email.sentiment or 'Neutral'}</p>
        </div>
        """
    
    if len(emails) > 10:
        html += f"<p><em>... and {len(emails) - 10} more emails in this category</em></p>\n"
    
    return html

def generate_daily_digest_html(emails: List[models.Email]) -> str:
    """Generate HTML content for daily digest email."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    date_str = yesterday.strftime("%B %d, %Y")
    
    # Categorize emails
    categorized = categorize_emails_by_importance(emails)
    
    # Count by inbox
    inbox_counts = {}
    for email in emails:
        if email.recipients:
            for recipient in email.recipients:
                if '@ivc-valves.com' in recipient or '@gmail.com' in recipient:
                    inbox_counts[recipient] = inbox_counts.get(recipient, 0) + 1
    
    # Count by category
    category_counts = {}
    for email in emails:
        category = email.category or 'Uncategorized'
        category_counts[category] = category_counts.get(category, 0) + 1
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            h2 {{ color: #007BFF; }}
            h3 {{ color: #0056b3; }}
            .summary-stats {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .inbox-summary {{ display: inline-block; margin: 10px; padding: 10px; background: #e9ecef; border-radius: 3px; }}
        </style>
    </head>
    <body>
        <h1>Daily Email Digest - {date_str}</h1>
        
        <div class="summary-stats">
            <h2>Summary Statistics</h2>
            <p><strong>Total Emails Processed:</strong> {len(emails)}</p>
            
            <h3>By Inbox:</h3>
            {''.join([f'<span class="inbox-summary">{inbox}: {count}</span>' for inbox, count in inbox_counts.items()])}
            
            <h3>By Category:</h3>
            {''.join([f'<span class="inbox-summary">{category}: {count}</span>' for category, count in category_counts.items()])}
        </div>
        
        {generate_email_summary_section(categorized['urgent_very_important'], "🚨 URGENT & VERY IMPORTANT")}
        {generate_email_summary_section(categorized['urgent_normal'], "⚡ URGENT")}
        {generate_email_summary_section(categorized['normal_very_important'], "⭐ VERY IMPORTANT")}
        {generate_email_summary_section(categorized['normal_normal'], "📧 NORMAL PRIORITY")}
        {generate_email_summary_section(categorized['low_priority'], "📋 LOW PRIORITY")}
        
        <hr>
        <p><em>This digest was automatically generated by the RAG Email System.</em></p>
        <p><em>Generated at: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")} UTC</em></p>
    </body>
    </html>
    """
    
    return html

def send_daily_digest():
    """Generate and send daily digest email to tony@ivc-valves.com."""
    settings = get_settings()
    db = SessionLocal()
    
    try:
        # Get yesterday's emails
        emails = get_yesterdays_emails(db)
        
        if not emails:
            log.info("No emails found for yesterday's digest")
            return
        
        # Generate digest HTML
        html_content = generate_daily_digest_html(emails)
        
        # Create email message
        yesterday = datetime.utcnow() - timedelta(days=1)
        subject = f"Daily Email Digest - {yesterday.strftime('%B %d, %Y')} ({len(emails)} emails)"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = "rag-system@ivc-valves.com"  # Configure this
        msg['To'] = settings.digest_recipient
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
          # Send email if SMTP is configured
        if settings.smtp_username and settings.smtp_password:
            try:
                smtp_server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
                smtp_server.starttls()
                smtp_server.login(settings.smtp_username, settings.smtp_password)
                smtp_server.send_message(msg)
                smtp_server.quit()
                log.info(f"Daily digest email sent successfully to {settings.digest_recipient}")
            except Exception as e:
                log.error(f"Failed to send email: {e}")
                # Fallback to file save
                with open(f"/app/logs/daily_digest_{yesterday.strftime('%Y%m%d')}.html", 'w') as f:
                    f.write(html_content)
                log.info("Email sending failed, digest saved to file instead")
        else:
            # For development, save to file
            with open(f"/app/logs/daily_digest_{yesterday.strftime('%Y%m%d')}.html", 'w') as f:
                f.write(html_content)
            log.info(f"SMTP not configured, daily digest saved to file: /app/logs/daily_digest_{yesterday.strftime('%Y%m%d')}.html")
        
    except Exception as e:
        log.error(f"Failed to generate daily digest: {e}")
    finally:
        db.close()

def generate_weekly_sales_digest():
    """Generate weekly digest of sales quotations sent and sales inquiries received.
    This is for future implementation after the 7-day sprint."""
    # This function would implement the weekly sales digest requirement
    # but is marked for future implementation as per requirements
    pass
