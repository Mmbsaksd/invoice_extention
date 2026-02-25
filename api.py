import os
import json
import logging
import asyncio
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from tempfile import NamedTemporaryFile

from core.engine import process_invoice
from core.storage import session_store, InvoiceData
from core.config import init_config

init_config()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Invoice Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload", response_model=List[InvoiceData])
async def upload_invoices(files: List[UploadFile] = File(...)):
    """Upload PDF invoices and extract their details."""
    async def process_file(file):
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(await file.read())
            path = tmp.name
        try:
            return await run_in_threadpool(process_invoice, path)
        finally:
            if os.path.exists(path): os.remove(path)

    try:
        results = await asyncio.gather(*(process_file(f) for f in files))
        flat_results = [item for sublist in results for item in sublist]
        session_store.add_invoices(flat_results)
        return flat_results
    except Exception as e:
        logger.error(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/invoices")
async def get_invoices():
    """Retrieve all pending invoices."""
    return session_store.get_all_invoices()

@app.delete("/invoices")
async def clear_all():
    """Clear session data."""
    session_store.clear()
    return {"status": "success"}

@app.delete("/invoices/{index}")
async def remove_one(index: int):
    """Remove a specific invoice by index."""
    session_store.remove_invoice(index)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
