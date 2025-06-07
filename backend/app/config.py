import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    # Database settings
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")

    # External services
    ragflow_host: str = "http://localhost:9380"
    ragflow_api_key: str = "ragflow-YWRtaW46cmFnZmxvdzEyMw"
    ollama_host: str = "http://localhost:11434"
    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")

    # Google OAuth & API settings
    google_client_id: str = "792999098406-hmolqmci0o9op9t2vpknmhespml53bau.apps.googleusercontent.com"
    google_client_secret: str = "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"
    google_project_id: str = Field(..., env="GOOGLE_PROJECT_ID")
    google_redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # Gmail inboxes to index in this sequence
    gmail_inboxes: str = Field(
        default="storesnproduction@ivc-valves.com,hr.ivcvalves@gmail.com,umesh.jadhav@ivc-valves.com,arpatil@ivc-valves.com,exports@ivc-valves.com,sumit.basu@ivc-valves.com,hr@ivc-valves.com", 
        env="GMAIL_INBOXES"
    )
    
    # Google Drive folder IDs used by the application
    attachment_folder_id: str = "1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV"
    documents_folder_id: str = "1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn"
    
    # LLM model configuration
    llm_model: str = "mistral:7b-instruct-v0.3-q4_K_M"
    llm_temperature: float = 0.3
    llm_top_k: int = 40
    llm_top_p: float = 0.9
    
    # Daily digest settings
    digest_recipient: str = "tony@ivc-valves.com"
    digest_time: str = "08:00"
    
    # SMTP settings for email sending
    smtp_server: str = Field(default="smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="rag-system@ivc-valves.com", env="SMTP_FROM_EMAIL")

    # Optional settings
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")  # Optional fallback
    
    # Google Drive Folders - Tony's Gmail Account
    gdrive_documents_folder_id: str = "1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn"
    gdrive_attachments_folder_id: str = "1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV"
    gdrive_service_account_email: str = "tony.mukherjee1@gmail.com"
    
    # Email Processing Configuration
    inbox_sequence: List[str] = [
        "storesnproduction@ivc-valves.com",
        "hr.ivcvalves@gmail.com",
        "umesh.jadhav@ivc-valves.com",
        "arpatil@ivc-valves.com",
        "exports@ivc-valves.com",
        "sumit.basu@ivc-valves.com",
        "hr@ivc-valves.com"
    ]
    
    # Domain-wide delegation for @ivc-valves.com emails
    google_domain_wide_scope: str = "https://www.googleapis.com/auth/gmail.readonly"
    
    # Processing Configuration
    max_emails_per_batch: int = 100
    processing_timeout: int = 300
    ocr_enabled: bool = True
    
    # Daily/Weekly Digest Configuration (for future phases)
    daily_digest_time: str = "08:00"
    weekly_digest_day: str = "monday"
    
    # System Resources Configuration
    max_concurrent_processes: int = 4
    night_mode_enabled: bool = False
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    token_encryption_key: str = "your-encryption-key-here-32-chars-long"
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "ragflow.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache
def get_settings():
    return Settings()

# Email Categories - Exact list from boss requirements
EMAIL_CATEGORIES = [
    "Delay/Follow-up/Reminder/Pending/Shortage",
    "Maintenance/Repair/Problem/Defect/Issue/Support Request",
    "Drawing/GAD",
    "Inspection/TPI",
    "Quality Assurance/QAP",
    "Customer Sales Inquiry/Request for Quotation",
    "Customer Quotation",
    "Quotation from Vendor/Supplier",
    "Project Documentation/Approval Process",
    "Job Application",
    "Purchase Order",
    "Advance Bank Guarantee/ABG",
    "Performance Bank Guarantee/PBG",
    "Financial Compliance/Document Submission",
    "Documentation/Compliance",
    "Vendor Invoice/Bill/Outgoing Payment/Due",
    "Customer Invoice/Incoming Payment/LC/Letter of Credit/RTGS",
    "Unsolicited marketing/Newsletter/Promotion",
    "Operations/Logistics"
]

# Document Categories - For attachments and Google Drive documents
DOCUMENT_CATEGORIES = [
    "Sales Inquiry/Request for Quotation",
    "Quotation",
    "Drawing/GAD",
    "Purchase Order",
    "Invoice/Bill",
    "Challan",
    "Report",
    "Test Certificate",
    "Specifications",
    "Inspection/TPI",
    "Quality Assurance Plan/QAP",
    "Bank Guarantee/ABG/PBG",
    "Contract",
    "Accounts",
    "Compliance",
    "Legal Document",
    "Receipt",
    "Plan",
    "Presentation",
    "Correspondence",
    "Meeting Minutes",
    "Customer Support",
    "Internal Communication",
    "HR/Recruitment",
    "IT/Technical Support",
    "Marketing/PR",
    "Operations/Logistics"
]

# Priority levels
PRIORITY_LEVELS = ["Urgent", "Normal", "Low Priority"]

# Sentiment levels
SENTIMENT_LEVELS = ["Positive", "Neutral", "Negative"]

# Importance levels
IMPORTANCE_LEVELS = ["Very Important", "Normal", "Low Importance"]
