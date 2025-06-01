from functools import lru_cache
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    # Database settings
    postgres_user: str = Field(..., env="POSTGRES_USER")
    postgres_password: str = Field(..., env="POSTGRES_PASSWORD")
    postgres_db: str = Field(..., env="POSTGRES_DB")
    postgres_host: str = Field(default="postgres", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")

    # External services
    ragflow_host: str = Field(default="http://ragflow:3000", env="RAGFLOW_HOST")
    ragflow_api_key: str = Field(default="", env="RAGFLOW_API_KEY")  # Add if RAGFlow needs auth
    ollama_host: str = Field(default="http://ollama:11434", env="OLLAMA_HOST")
    redis_host: str = Field(default="redis", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")

    # Google OAuth & API settings - Exact from requirements
    google_client_id: str = Field(..., env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(..., env="GOOGLE_CLIENT_SECRET")
    google_project_id: str = Field(..., env="GOOGLE_PROJECT_ID")
    
    # Gmail inboxes to index in the specified sequence from requirements
    gmail_inboxes: str = Field(
        default="storesnproduction@ivc-valves.com,hr.ivcvalves@gmail.com,umesh.jadhav@ivc-valves.com,arpatil@ivc-valves.com,exports@ivc-valves.com,sumit.basu@ivc-valves.com,hr@ivc-valves.com", 
        env="GMAIL_INBOXES"
    )
    
    # Google Drive folder IDs - Exact from requirements
    attachment_folder_id: str = Field(default="1dEjEogfE3WlHypaY8vuaWiBeZjjuVTGV", env="ATTACHMENT_FOLDER_ID")  # RAG-Email Attachments
    documents_folder_id: str = Field(default="1oas1TEtW26ZNvW2jekk6Y8R2Hb85IUmn", env="DOCUMENTS_FOLDER_ID")  # RAG-IVC Documents
    
    # LLM Model specification from requirements
    llm_model: str = Field(default="mistral-7b-instruct-v0.3", env="LLM_MODEL")
    
    # Daily digest settings from requirements
    digest_recipient: str = Field(default="tony@ivc-valves.com", env="DIGEST_RECIPIENT")
    digest_time: str = Field(default="08:00", env="DIGEST_TIME")  # Format: HH:MM
    
    # SMTP settings for email sending
    smtp_server: str = Field(default="smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_from_email: str = Field(default="rag-system@ivc-valves.com", env="SMTP_FROM_EMAIL")

    # Optional settings
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")  # Optional fallback
    
    class Config:
        env_file = ".env"

@lru_cache
def get_settings():
    return Settings()
