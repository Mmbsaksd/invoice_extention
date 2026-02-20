from core.extractor.extractor import extract_text
from core.parser.parser import analyze_text
from core.invoice_detector.detector import detect_unique_invoices
from core.validator.validator import validate_invoice

def process_invoice(pdf_path: str):
    """Orchestrates the extraction and validation pipeline."""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"Starting extraction for: {pdf_path}")
    raw_text = extract_text(pdf_path)
    
    if not raw_text.strip():
        logger.warning(f"No text extracted from {pdf_path}")
        return []
    
    logger.info(f"Text extracted (length: {len(raw_text)}). Starting AI analysis...")
    invoices = analyze_text(raw_text)
    
    logger.info(f"AI found {len(invoices)} potential invoices. Deduplicating...")
    unique_invoices = detect_unique_invoices(invoices)
    
    logger.info(f"Unique invoices: {len(unique_invoices)}. Validating...")
    validated_invoices = [validate_invoice(inv) for inv in unique_invoices]
    
    logger.info("Extraction Pipeline Complete.")
    return validated_invoices
