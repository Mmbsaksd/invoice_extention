import os
import re
from datetime import datetime
from typing import Optional, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

load_dotenv(override=True)

def get_llm():
    """Deterministic LLM Factory."""
    if os.getenv("AZURE_OPENAI_API_KEY"):
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            temperature=0
        )
    if os.getenv("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o", temperature=0)
    if os.getenv("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    raise ValueError("Missing API Keys")

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

class InvoiceData(BaseModel):
    """Production Schema with Validation Metadata."""
    supplier: Optional[str] = Field(None)
    invoice_date: Optional[str] = Field(None)
    reference: Optional[str] = Field(None)
    posting_date: Optional[str] = Field(None)
    amount: Optional[str] = Field(None)
    tax_amount: Optional[str] = Field(None)
    validation_error: Optional[str] = Field(None) # Flag for UI

class InvoiceList(BaseModel):
    invoices: List[InvoiceData]

def analyze_text(text: str) -> List[dict]:
    """Boundary-aware extraction (Scenario B)."""
    llm = get_llm().with_structured_output(InvoiceList)
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a production-grade extraction agent. Detect UNIQUE invoice boundaries "
            "using Reference #, Vendor restarts, and Totals. Extract: supplier, invoice_date, "
            "reference, posting_date, amount, tax_amount. No guessing. Missing=null."
        )),
        ("human", "{text}")
    ])
    result = (prompt | llm).invoke({"text": text})
    return [inv.model_dump() for inv in result.invoices]

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

def process_invoice(pdf_path: str) -> List[dict]:
    """Modular production pipeline."""
    raw = extract_text(pdf_path)
    if not raw.strip(): return []
    invoices = analyze_text(raw)
    
    # Refined loop for deduplication and validation
    final = []
    seen = set()
    for inv in invoices:
        ref_key = f"{inv.get('supplier')}_{inv.get('reference')}".lower()
        if ref_key in seen: continue
        seen.add(ref_key)
        final.append(validate_invoice(inv))
    return final
