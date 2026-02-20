import os
from tempfile import NamedTemporaryFile
from core.engine import process_invoice
from automation.autofill_engine.engine import run_single_fill
from storage.session_store import session_store

def handle_file_upload(file):
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(file.getvalue())
        path = tmp.name
    try:
        results = process_invoice(path)
        # Unified save for both results and hash
        session_store.add_invoices(results, file_hash=file.name)
    finally:
        if os.path.exists(path): os.remove(path)

async def handle_fill_sap(inv, url, use_existing):
    return await run_single_fill(inv, url, use_existing)
