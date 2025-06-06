import requests, json
from app.config import get_settings
from app.llm.summary_prompts import (
    EMAIL_PROMPT_TEMPLATE,
    ATTACHMENT_PROMPT_TEMPLATE,
    DOCUMENT_PROMPT_TEMPLATE,
    OCR_CORRECTION_PROMPT,
)

settings = get_settings()

def summarize_email(
    from_email: str,
    to_list: list,
    cc_list: list,
    subject: str,
    date_str: str,
    body: str,
    email_id: str = "",
) -> dict:
    """Summarize email content using the specified prompt template."""
    prompt = EMAIL_PROMPT_TEMPLATE.format(
        from_email=from_email,
        to_list=", ".join(to_list) if to_list else "Not specified",
        cc_list=", ".join(cc_list) if cc_list else "Not specified",
        subject=subject,
        email_date=date_str or "Not specified",
        body=body,
        email_id=email_id,
    )
    
    resp = requests.post(
        f"{settings.ollama_host}/api/generate",
        json={
            "model": settings.llm_model,
            "prompt": prompt,
            "temperature": settings.llm_temperature,
            "top_k": settings.llm_top_k,
            "top_p": settings.llm_top_p,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    
    raw = resp.json()["response"]
    
    try:
        # Try to parse as JSON first
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Parse the expected multiline format
        data = parse_multiline_response(raw)
    
    return data

def summarize_attachment(document_text: str, inbox_email: str = "") -> dict:
    """Summarize email attachment content using the specified prompt template."""
    prompt = ATTACHMENT_PROMPT_TEMPLATE.format(document_text=document_text, inbox_email=inbox_email)
    
    resp = requests.post(
        f"{settings.ollama_host}/api/generate",
        json={
            "model": settings.llm_model,
            "prompt": prompt,
            "temperature": settings.llm_temperature,
            "top_k": settings.llm_top_k,
            "top_p": settings.llm_top_p,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    
    raw = resp.json()["response"]
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = parse_multiline_response(raw)
    
    return data

def summarize_document(document_text: str, department_name: str = "") -> dict:
    """Summarize document content using the specified prompt template."""
    prompt = DOCUMENT_PROMPT_TEMPLATE.format(document_text=document_text, department_name=department_name)
    
    resp = requests.post(
        f"{settings.ollama_host}/api/generate",
        json={
            "model": settings.llm_model,
            "prompt": prompt,
            "temperature": settings.llm_temperature,
            "top_k": settings.llm_top_k,
            "top_p": settings.llm_top_p,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    
    raw = resp.json()["response"]
    
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = parse_multiline_response(raw)
    
    return data

def correct_ocr_text(ocr_text: str) -> str:
    """Correct OCR errors using LLM with domain-specific context."""
    prompt = OCR_CORRECTION_PROMPT.format(ocr_text=ocr_text)
    
    resp = requests.post(
        f"{settings.ollama_host}/api/generate",
        json={
            "model": settings.llm_model,
            "prompt": prompt,
            "temperature": 0.1,  # Lower temperature for correction tasks
            "top_k": settings.llm_top_k,
            "top_p": settings.llm_top_p,
            "stream": False,
        },
        timeout=120,
    )
    resp.raise_for_status()
    
    corrected_text = resp.json()["response"]
    return corrected_text.strip()

def clean_ocr_text(ocr_text: str) -> str:
    """Legacy function - now calls the updated OCR correction."""
    return correct_ocr_text(ocr_text)

def parse_multiline_response(response: str) -> dict:
    """Parse the expected multiline response format."""
    lines = response.strip().split('\n')
    data = {
        'summary': '',
        'urgency': 'Normal',
        'sentiment': 'Neutral', 
        'importance': 'Normal',
        'keywords': [],
        'category': ''
    }
    
    current_field = None
    for line in lines:
        line = line.strip()
        if line.startswith('Summary:'):
            current_field = 'summary'
            data['summary'] = line.replace('Summary:', '').strip()
        elif line.startswith('Urgency:'):
            data['urgency'] = line.replace('Urgency:', '').strip()
            current_field = None
        elif line.startswith('Sentiment:'):
            data['sentiment'] = line.replace('Sentiment:', '').strip()
            current_field = None
        elif line.startswith('Importance:'):
            data['importance'] = line.replace('Importance:', '').strip()
            current_field = None
        elif line.startswith('Keywords:'):
            keywords_str = line.replace('Keywords:', '').strip()
            data['keywords'] = [k.strip() for k in keywords_str.split(',') if k.strip()]
            current_field = None
        elif line.startswith('Category:'):
            data['category'] = line.replace('Category:', '').strip()
            current_field = None
        elif current_field == 'summary' and line:
            # Continue summary on next lines
            data['summary'] += ' ' + line
    
    return data
