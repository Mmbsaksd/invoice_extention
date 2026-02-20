import re
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def clean_numeric(val: str) -> str:
# ... (same)
    if not val: return "0.00"
    s = str(val).strip()
    # Handle European format (1.234,56) vs US (1,234.56)
    if ',' in s and '.' in s:
        if s.rfind(',') > s.rfind('.'): # European 1.000,00
            s = s.replace('.', '').replace(',', '.')
        else: # US 1,000.00
            s = s.replace(',', '')
    elif ',' in s: # Simple European 1234,56
        s = s.replace(',', '.')
    
    # Final strip of anything not digit or dot
    s = re.sub(r"[^\d.]", "", s)
    return s if s else "0.00"

def validate_invoice(data: dict) -> dict:
    """Production Validation Rules (Section 6)."""
    errors = []
    
    # Clean numeric strings
    data["amount"] = clean_numeric(data.get("amount"))
    data["tax_amount"] = clean_numeric(data.get("tax_amount"))
    
    amt = data["amount"]
    tax = data["tax_amount"]
    ref = str(data.get("reference") or "").strip()
    
    # 1. Logic Checks
    if amt and ref and amt == ref:
        errors.append("Amount matches Reference Number")
    if amt and tax and amt == tax:
        errors.append("Amount matches Tax Amount")
    if amt and not re.search(r"\d", amt):
        errors.append("Invalid Amount")
    
    # 2. Date checks
    # Posting Date must ALWAYS be the day of posting (Today)
    old_posting = data.get("posting_date")
    data["posting_date"] = datetime.now().strftime("%d.%m.%Y")
    
    logger.info(f"Date Audit: InvoiceDate={data.get('invoice_date')} | PostingDate={data['posting_date']} (overwrote {old_posting})")
    
    if errors:
        data["validation_error"] = " | ".join(errors)
    return data
