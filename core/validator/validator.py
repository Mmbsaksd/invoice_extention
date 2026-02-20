import re
from datetime import datetime

def validate_invoice(data: dict) -> dict:
    """Production Validation Rules (Section 6)."""
    errors = []
    
    # Clean numeric strings
    amt = re.sub(r"[^\d.]", "", data.get("amount") or "")
    tax = re.sub(r"[^\d.]", "", data.get("tax_amount") or "")
    ref = str(data.get("reference") or "").strip()
    
    # 1. Logic Checks
    if amt and ref and amt == ref:
        errors.append("Amount matches Reference Number")
    if amt and tax and amt == tax:
        errors.append("Amount matches Tax Amount")
    if amt and not re.search(r"\d", amt):
        errors.append("Invalid Amount")
    
    # 2. Date checks
    if not data.get("posting_date"):
        data["posting_date"] = datetime.now().strftime("%d.%m.%Y")
    
    if errors:
        data["validation_error"] = " | ".join(errors)
    return data
