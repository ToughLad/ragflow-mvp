"""
OCR text extraction and cleanup for PDF and image files.
"""
import logging
import io
from typing import Optional
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
try:
    from PyPDF2 import PdfReader
except ImportError:
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None

log = logging.getLogger(__name__)

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using OCR if needed."""
    try:
        # First try to extract text directly from PDF if PyPDF2 is available
        if PdfReader:
            pdf_reader = PdfReader(io.BytesIO(pdf_bytes))
            extracted_text = ""
            
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text.strip():
                    extracted_text += text + "\n"
            
            # If we got substantial text, return it
            if len(extracted_text.strip()) > 50:
                log.info("Successfully extracted text directly from PDF")
                return extracted_text
        
        # Otherwise, use OCR
        log.info("PDF appears to be image-based or PyPDF2 not available, using OCR")
        return extract_text_from_pdf_ocr(pdf_bytes)
        
    except Exception as e:
        log.warning(f"Failed to extract text from PDF: {e}")
        # Fallback to OCR
        return extract_text_from_pdf_ocr(pdf_bytes)

def extract_text_from_pdf_ocr(pdf_bytes: bytes) -> str:
    """Extract text from PDF using OCR."""
    try:
        # Convert PDF pages to images
        images = convert_from_bytes(pdf_bytes, dpi=200)
        
        extracted_text = ""
        for i, image in enumerate(images):
            log.info(f"Processing PDF page {i+1} with OCR")
            page_text = pytesseract.image_to_string(image, lang='eng')
            extracted_text += f"\n--- Page {i+1} ---\n{page_text}\n"
        
        return extracted_text
        
    except Exception as e:
        log.error(f"OCR extraction from PDF failed: {e}")
        return ""

def extract_text_from_image_bytes(image_bytes: bytes, mime_type: str) -> str:
    """Extract text from image bytes using OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Use OCR to extract text
        text = pytesseract.image_to_string(image, lang='eng')
        
        log.info(f"Successfully extracted text from {mime_type} image")
        return text
        
    except Exception as e:
        log.error(f"Failed to extract text from image: {e}")
        return ""

def process_attachment_ocr(file_data: bytes, filename: str, mime_type: str) -> str:
    """Process attachment and extract text content using appropriate method."""
    mime_type = mime_type.lower()
    
    if mime_type == 'application/pdf':
        return extract_text_from_pdf_bytes(file_data)
    elif mime_type.startswith('image/'):
        return extract_text_from_image_bytes(file_data, mime_type)
    elif mime_type.startswith('text/'):
        try:
            return file_data.decode('utf-8', errors='ignore')
        except Exception as e:
            log.warning(f"Failed to decode text file {filename}: {e}")
            return ""
    else:
        log.info(f"OCR not supported for {mime_type} files")
        return ""
