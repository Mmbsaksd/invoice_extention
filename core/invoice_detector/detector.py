from typing import List

def detect_unique_invoices(invoices: List[dict]) -> List[dict]:
    """Ensures unique invoices based on supplier and reference."""
    final = []
    seen = set()
    for inv in invoices:
        ref_key = f"{inv.get('supplier')}_{inv.get('reference')}".lower()
        if ref_key in seen: continue
        seen.add(ref_key)
        final.append(inv)
    return final
