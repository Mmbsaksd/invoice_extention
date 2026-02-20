from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract

def extract_text(pdf_path: str) -> str:
    """Extracts text with OCR fallback."""
    text = ""
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except: pass
    if len(text.strip()) < 50:
        images = convert_from_path(pdf_path)
        text = "\n".join([pytesseract.image_to_string(img) for img in images])
    return text
