from typing import List
from langchain_core.prompts import ChatPromptTemplate
from core.llm_engine.llm_engine import get_llm
from storage.models import InvoiceList

def analyze_text(text: str) -> List[dict]:
    """Boundary-aware extraction (Scenario B)."""
    llm = get_llm().with_structured_output(InvoiceList)
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "You are a production-grade SAP extraction agent. Detect UNIQUE invoice boundaries. "
            "Extract: supplier, invoice_date, reference (invoice number), posting_date, amount, tax_amount. "
            "\n- **reference**: Look for 'Invoice #', 'Reference', 'Doc No'. "
            "\n- **posting_date**: Usually same as invoice_date. If missing, use invoice_date. "
            "\n- **tax_amount**: Extract explicitly. If not found, use 0.0. "
            "\n- **amount**: This is the TOTAL gross amount. "
            "\nFormat dates as DD.MM.YYYY. No guessing. All amounts as strings."
        )),
        ("human", "{text}")
    ])
    result = (prompt | llm).invoke({"text": text})
    return [inv.model_dump() for inv in result.invoices]
