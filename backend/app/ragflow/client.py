import requests
import logging
from app.config import get_settings
from typing import Dict, Any

log = logging.getLogger(__name__)
settings = get_settings()

def get_or_create_kb(kb_name: str, description: str = "") -> str:
    """Get existing knowledge base ID or create new one."""
    try:
        headers = {"Content-Type": "application/json"}
        if not settings.ragflow_api_key:
            raise ValueError("RAGFlow API key is required")
        headers["Authorization"] = f"Bearer {settings.ragflow_api_key}"
        
        # First, try to list existing KBs to find the one we want
        list_response = requests.get(
            f"{settings.ragflow_host}/api/kb",
            headers=headers,
            timeout=30
        )
        
        if list_response.status_code == 200:
            kbs = list_response.json().get('data', [])
            for kb in kbs:
                if kb.get('name') == kb_name:
                    log.info(f"Found existing KB: {kb_name} with ID: {kb.get('id')}")
                    return kb.get('id')
        
        # KB doesn't exist, create it
        create_response = requests.post(
            f"{settings.ragflow_host}/api/kb",
            json={
                "name": kb_name,
                "description": description or f"Knowledge base for {kb_name}",
                "language": "English",
                "embedding_model": "BAAI/bge-large-en-v1.5",
                "permission": "me"
            },
            headers=headers,
            timeout=30
        )
        
        if create_response.status_code in [200, 201]:
            kb_data = create_response.json()
            kb_id = kb_data.get('data', {}).get('id') or kb_data.get('id')
            log.info(f"Created new KB: {kb_name} with ID: {kb_id}")
            return kb_id
        else:
            log.error(f"Failed to create KB {kb_name}: {create_response.status_code} - {create_response.text}")
            return None
            
    except Exception as e:
        log.error(f"Error in get_or_create_kb for {kb_name}: {e}")
        return None

def push_text(kb_name: str, text: str, metadata: dict):
    """Push text content to RAGFlow knowledge base."""
    try:
        if not settings.ragflow_api_key:
            raise ValueError("RAGFlow API key is required")
            
        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {settings.ragflow_api_key}"
        
        # Get or create the knowledge base
        kb_id = get_or_create_kb(kb_name, f"Knowledge base for {kb_name}")
        
        if not kb_id:
            log.error(f"Failed to get/create knowledge base: {kb_name}")
            return {"error": "KB creation failed"}
        
        # Push document to the knowledge base
        r = requests.post(
            f"{settings.ragflow_host}/api/document",
            json={
                "kb_id": kb_id,
                "name": f"doc_{metadata.get('email_id', 'unknown')}_{metadata.get('type', 'content')}",
                "type": "text",
                "text": text,
                "metadata": metadata
            },
            headers=headers,
            timeout=30
        )
        
        if r.status_code in [200, 201]:
            log.info(f"Successfully pushed text to RAGFlow KB: {kb_name}")
            return r.json()
        else:
            log.warning(f"RAGFlow push failed with status {r.status_code}: {r.text}")
            return {"error": f"HTTP {r.status_code}", "message": r.text}
            
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to push to RAGFlow: {e}")
        return {"error": "Request failed", "message": str(e)}

def query_ragflow(question: str, kb_names: list = None) -> Dict[str, Any]:
    """Query RAGFlow for answers across knowledge bases."""
    try:
        headers = {"Content-Type": "application/json"}
        if settings.ragflow_api_key:
            headers["Authorization"] = f"Bearer {settings.ragflow_api_key}"
            
        payload = {
            "question": question,
            "kb_ids": kb_names or [],  # Empty means search all KBs
            "top_k": 5,
            "similarity_threshold": 0.1,
            "vector_similarity_weight": 0.3
        }
        
        r = requests.post(
            f"{settings.ragflow_host}/api/completion",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        if r.status_code == 200:
            response_data = r.json()
            log.info(f"RAGFlow query successful for: {question[:50]}...")
            return response_data
        else:
            log.warning(f"RAGFlow query failed with status {r.status_code}: {r.text}")
            return {
                "error": f"HTTP {r.status_code}",
                "message": r.text,
                "answer": "Sorry, I couldn't process your query at this time."
            }
            
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to query RAGFlow: {e}")
        return {
            "error": "Request failed", 
            "message": str(e),
            "answer": "Sorry, the search service is currently unavailable."
        }

def list_knowledge_bases() -> Dict[str, Any]:
    """List all available knowledge bases in RAGFlow."""
    try:
        headers = {"Content-Type": "application/json"}
        if settings.ragflow_api_key:
            headers["Authorization"] = f"Bearer {settings.ragflow_api_key}"
            
        r = requests.get(
            f"{settings.ragflow_host}/api/kb", 
            headers=headers,
            timeout=30
        )
        
        if r.status_code == 200:
            return r.json()
        else:
            log.warning(f"Failed to list KBs: {r.status_code} - {r.text}")
            return {"error": f"HTTP {r.status_code}", "message": r.text}
            
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to list knowledge bases: {e}")
        return {"error": "Request failed", "message": str(e)}

def create_knowledge_base(name: str, description: str = "") -> Dict[str, Any]:
    """Create a new knowledge base in RAGFlow."""
    try:
        headers = {"Content-Type": "application/json"}
        if settings.ragflow_api_key:
            headers["Authorization"] = f"Bearer {settings.ragflow_api_key}"
            
        r = requests.post(
            f"{settings.ragflow_host}/api/kb",
            json={
                "name": name,
                "description": description,
                "language": "English",
                "embedding_model": "BAAI/bge-large-en-v1.5",
                "permission": "me"
            },
            headers=headers,
            timeout=30
        )
        
        if r.status_code in [200, 201]:
            log.info(f"Successfully created knowledge base: {name}")
            return r.json()
        else:
            log.warning(f"Failed to create KB {name}: {r.status_code} - {r.text}")
            return {"error": f"HTTP {r.status_code}", "message": r.text}
            
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to create knowledge base: {e}")
        return {"error": "Request failed", "message": str(e)}
