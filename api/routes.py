from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
from tempfile import NamedTemporaryFile
from core.engine import process_invoice
from storage.models import InvoiceData
from storage.session_store import session_store
from shared.config import init_config

import logging

# Initialize environment variables
init_config()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Invoice Extraction API")

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload", response_model=List[InvoiceData])
async def upload_invoices(files: List[UploadFile] = File(...)):
    import traceback
    all_results = []
    from fastapi.concurrency import run_in_threadpool
    import asyncio
    from fastapi.concurrency import run_in_threadpool
    
    async def process_single_file(file):
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            path = tmp.name
        try:
            logger.info(f"Processing uploaded file: {file.filename}")
            return await run_in_threadpool(process_invoice, path)
        finally:
            if os.path.exists(path):
                os.remove(path)

    try:
        # Process all files concurrently
        tasks = [process_single_file(file) for file in files]
        results_nested = await asyncio.gather(*tasks)
        
        # Flatten results
        for results in results_nested:
            all_results.extend(results)
        
        session_store.add_invoices(all_results)
        return all_results
    except ValueError as ve:
        logger.error(f"Processing Error: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"Upload Error: {error_msg}")
        raise HTTPException(status_code=500, detail=f"Backend Processing Error:\n{error_msg}")

@app.get("/invoices")
async def get_invoices():
    return session_store.get_all_invoices()

@app.delete("/invoices")
async def clear_invoices():
    session_store.clear()
    return {"status": "success", "message": "Invoices cleared"}

@app.delete("/invoices/{index}")
async def remove_invoice(index: int):
    session_store.remove_invoice(index)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
