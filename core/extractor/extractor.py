from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

import shutil
import logging

logger = logging.getLogger(__name__)

def extract_text(pdf_path: str) -> str:
    """Extracts text with OCR fallback."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {str(e)}")

    if len(text.strip()) < 50:
        logger.info("Text density low, attempting OCR fallback...")
        
        # Check dependencies
        has_poppler = shutil.which("pdftoppm") is not None
        has_tesseract = shutil.which("tesseract") is not None
        
        if not has_poppler or not has_tesseract:
            missing = []
            if not has_poppler: missing.append("Poppler (pdftoppm)")
            if not has_tesseract: missing.append("Tesseract-OCR")
            logger.error(f"OCR required but missing dependencies: {', '.join(missing)}")
            return text # Return whatever we got from reader (probably empty)

        try:
            images = convert_from_path(pdf_path)
            text = "\n".join([pytesseract.image_to_string(img) for img in images])
        except Exception as e:
            logger.error(f"OCR processing failed: {str(e)}")
            
    return text
