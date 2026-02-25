import re
import logging
import shutil
import os
from datetime import datetime
from typing import List

from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from core.config import get_env
from core.storage import InvoiceData, InvoiceList

logger = logging.getLogger(__name__)

def get_llm():
    """
    This is the 'Brain Factory'. It picks which AI service to use 
    based on your secret keys in the .env file.
    """
    if get_env("AZURE_OPENAI_API_KEY"):
        return AzureChatOpenAI(
            azure_endpoint=get_env("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=get_env("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=get_env("AZURE_OPENAI_API_VERSION"),
            temperature=0,
            request_timeout=60
        )
    if get_env("OPENAI_API_KEY"):
        return ChatOpenAI(model="gpt-4o", temperature=0, request_timeout=60)
    if get_env("GOOGLE_API_KEY"):
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0, request_timeout=60)
    raise ValueError("Missing API Keys. Please check your .env file.")

def extract_text(pdf_path: str) -> str:
    """
    Step 1: Get text from the PDF.
    If the PDF is an image (scanned), it uses OCR (Tesseract) as a backup.
    """
    text = ""
    try:
        reader = PdfReader(pdf_path)
        text = "\n".join([p.extract_text() for p in reader.pages if p.extract_text()])
    except Exception as e:
        logger.warning(f"Could not read text metadata: {e}")

    # If the text is too short, the PDF is likely just an image
    if len(text.strip()) < 50:
        logger.info("Scanned document detected. Running OCR...")
        if shutil.which("pdftoppm") and shutil.which("tesseract"):
            try:
                images = convert_from_path(pdf_path)
                text = "\n".join([pytesseract.image_to_string(img) for img in images])
            except Exception as e:
                logger.error(f"OCR failed: {e}")
    return text

def analyze_text(text: str) -> List[dict]:
    """High-precision extraction using production-grade prompts."""
    llm = get_llm().with_structured_output(InvoiceList)
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a production-grade SAP extraction agent. Your goal is absolute accuracy.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "1. Detect UNIQUE invoice boundaries. A single PDF might contain one or multiple invoices. "
            "Only split if there is clear evidence of a separate document (different reference, different date, or new header).\n"
            "2. Extract exactly these fields:\n"
            "   - **supplier**: Legal entity name of the vendor.\n"
            "   - **invoice_date**: The date of issue (format: DD.MM.YYYY).\n"
            "   - **reference**: The Invoice Number or ID. Look for 'Invoice #', 'Bill No', 'Doc No'.\n"
            "   - **amount**: The TOTAL gross amount (including tax).\n"
            "   - **tax_amount**: The explicit tax amount. Use 0.00 if none found.\n"
            "3. Formatting:\n"
            "   - Dates MUST be DD.MM.YYYY.\n"
            "   - Amounts MUST be numeric strings with '.' as decimal separator. Remove all currency symbols or commas.\n"
            "4. If info is missing, leave the field null."
        )),
        ("human", "Extact invoices from this text:\n\n{text}")
    ])
    result = (prompt | llm).invoke({"text": text})
    return [inv.model_dump() for inv in result.invoices]

def validate_invoice(data: dict) -> dict:
    """Standardizes and validates extracted invoice data."""
    def clean_num(val):
        if not val: return "0.00"
        s = str(val).strip().replace(',', '.')
        # Remove anything that isn't a digit or a dot
        s = re.sub(r"[^\d.]", "", s)
        # Handle multiple dots if any (take the last one as decimal)
        if s.count('.') > 1:
            parts = s.split('.')
            s = "".join(parts[:-1]) + "." + parts[-1]
        return s if s else "0.00"
    
    data["amount"] = clean_num(data.get("amount"))
    data["tax_amount"] = clean_num(data.get("tax_amount"))
    
    # Logic sanity check
    if data["amount"] == data.get("reference"):
        data["validation_error"] = "Suspicious: Amount matches Reference"
    
    # Force Posting Date to CURRENT day
    data["posting_date"] = datetime.now().strftime("%d.%m.%Y")
    return data

def process_invoice(pdf_path: str):
    """Main pipeline for extraction and validation."""
    logger.info(f"Processing invoice: {os.path.basename(pdf_path)}")
    raw_text = extract_text(pdf_path)
    if not raw_text.strip():
        logger.error("No text found.")
        return []
    
    invoices = analyze_text(raw_text)
    logger.info(f"AI extracted {len(invoices)} document results.")
    
    final = []
    seen = set()
    for inv in invoices:
        # Create a composite key to prevent incorrect splitting/duplication
        key = f"{inv.get('supplier')}_{inv.get('reference')}".lower().strip()
        if key and key not in seen:
            seen.add(key)
            final.append(validate_invoice(inv))
            
    logger.info(f"Audit complete. {len(final)} unique invoices validated.")
    return final
