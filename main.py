import os
import json
from typing import TypedDict, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

# Load environment variables
load_dotenv(override=True)

# 1. SCHEMAS
class ProductItem(BaseModel):
    title: str = Field(description="Title or description of the product/service")
    qty: Optional[float] = Field(None, description="Quantity")
    gross_amount: Optional[float] = Field(None, description="Gross amount in ₹")
    discounts_coupons: Optional[float] = Field(None, description="Discounts or coupons in ₹")
    taxable_value: Optional[float] = Field(None, description="Taxable value in ₹")
    igst: Optional[float] = Field(None, description="IGST in ₹")
    total: Optional[float] = Field(None, description="Total amount for this product in ₹")

class InvoiceData(BaseModel):
    invoice_number: str = Field(description="The unique number of the invoice")
    order_id: Optional[str] = Field(None, description="Order ID associated with the invoice")
    order_date: Optional[str] = Field(None, description="Date of the order")
    products: List[ProductItem] = Field(description="List of items/products in the invoice")
    grand_total: float = Field(description="The grand total amount of the invoice")
    gstin: str = Field(description="GST Identification Number")
    billing_address: str = Field(description="The billing address listed on the invoice")
    shipping_address: str = Field(description="The shipping address listed on the invoice")

# 2. LOADER UTILITIES
# Optional: Add common Tesseract paths for Windows
TESSERACT_CMD = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF text: {e}")

    if len(text.strip()) < 50:
        try:
            images = convert_from_path(pdf_path)
            text = ""
            for i, image in enumerate(images):
                page_text = pytesseract.image_to_string(image)
                text += f"--- Page {i+1} ---\n" + page_text + "\n"
        except Exception as e:
            print(f"OCR Error: {e}")
    
    return text

# 3. EXTRACTION PIPELINE
class GraphState(TypedDict):
    pdf_path: str
    raw_text: str
    extracted_data: dict
    error: str

def get_llm():
    openai_key = os.getenv("OPENAI_API_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    
    if openai_key:
        return ChatOpenAI(model="gpt-4o", temperature=0)
    elif azure_key:
        return AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            api_key=azure_key,
            temperature=0
        )
    elif google_key:
        return ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)
    else:
        raise ValueError("No LLM API keys found. Please check your .env file.")

def extract_text_node(state: GraphState):
    text = extract_text_from_pdf(state["pdf_path"])
    if not text:
        return {"error": "Failed to extract text from PDF."}
    return {"raw_text": text}

def llm_extraction_node(state: GraphState):
    text = state["raw_text"]
    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(InvoiceData)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract structured information from the invoice text. "
                       "Required: Invoice Number, Order ID, Date, Products, Total, GSTIN, Addresses."),
            ("human", "{text}")
        ])
        chain = prompt | structured_llm
        result = chain.invoke({"text": text})
        return {"extracted_data": result.dict()}
    except Exception as e:
        return {"error": str(e)}

workflow = StateGraph(GraphState)
workflow.add_node("extract_text", extract_text_node)
workflow.add_node("llm_extraction", llm_extraction_node)
workflow.set_entry_point("extract_text")
workflow.add_edge("extract_text", "llm_extraction")
workflow.add_edge("llm_extraction", END)
app_engine = workflow.compile()

def process_invoice(pdf_path: str):
    initial_state = {"pdf_path": pdf_path, "raw_text": "", "extracted_data": {}, "error": ""}
    result = app_engine.invoke(initial_state)
    if result.get("error"):
        raise Exception(result["error"])
    return result.get("extracted_data")

if __name__ == "__main__":
    pass
