#!/usr/bin/env python3
"""
Model setup script for RAGFlow MVP.
Downloads and verifies Ollama models.
"""

import requests
import time
import logging
import sys
from app.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wait_for_ollama():
    """Wait for Ollama service to be ready."""
    settings = get_settings()
    max_retries = 30
    retry_count = 0
    
    logger.info("Waiting for Ollama service to be ready...")
    
    while retry_count < max_retries:
        try:
            response = requests.get(f"{settings.ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Ollama service is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        retry_count += 1
        logger.info(f"Retrying... ({retry_count}/{max_retries})")
        time.sleep(2)
    
    logger.error("❌ Ollama service is not responding")
    return False

def pull_model():
    """Pull the required Mistral model."""
    settings = get_settings()
    model_name = settings.llm_model
    
    logger.info(f"Pulling model: {model_name}")
    
    try:
        # Start model pull
        response = requests.post(
            f"{settings.ollama_host}/api/pull",
            json={"name": model_name},
            stream=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if response.status_code == 200:
            logger.info("Model pull started...")
            # Monitor progress
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    try:
                        import json
                        data = json.loads(line)
                        if "status" in data:
                            logger.info(f"Status: {data['status']}")
                        if data.get("status") == "success":
                            logger.info("✅ Model pulled successfully!")
                            return True
                    except json.JSONDecodeError:
                        pass
        
        logger.error(f"❌ Failed to pull model. Status: {response.status_code}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error pulling model: {e}")
        return False

def verify_model():
    """Verify the model is working."""
    settings = get_settings()
    
    logger.info("Verifying model functionality...")
    
    try:
        response = requests.post(
            f"{settings.ollama_host}/api/generate",
            json={
                "model": settings.llm_model,
                "prompt": "Hello, can you respond with 'Model is working correctly'?",
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            if "response" in result:
                logger.info(f"✅ Model verification successful: {result['response'][:100]}...")
                return True
        
        logger.error(f"❌ Model verification failed. Status: {response.status_code}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error verifying model: {e}")
        return False

def list_available_models():
    """List all available models."""
    settings = get_settings()
    
    try:
        response = requests.get(f"{settings.ollama_host}/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            logger.info(f"Available models: {[m['name'] for m in models]}")
            return models
        return []
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return []

def main():
    """Main setup function."""
    logger.info("🚀 Starting Ollama model setup...")
    
    # Step 1: Wait for Ollama to be ready
    if not wait_for_ollama():
        sys.exit(1)
    
    # Step 2: Check if model already exists
    models = list_available_models()
    settings = get_settings()
    
    model_exists = any(settings.llm_model in model['name'] for model in models)
    
    if model_exists:
        logger.info(f"✅ Model {settings.llm_model} already exists!")
    else:
        # Step 3: Pull the model
        if not pull_model():
            sys.exit(1)
    
    # Step 4: Verify model works
    if not verify_model():
        sys.exit(1)
    
    logger.info("🎉 Model setup completed successfully!")
    logger.info("Your Ollama models are ready to go!")

if __name__ == "__main__":
    main() 