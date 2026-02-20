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
            "\n- **supplier**: Legal entity name of the vendor. "
            "\n- **reference**: Look for 'Invoice #', 'Reference', 'Doc No', 'Bill No'. "
            "\n- **invoice_date**: The date the invoice was issued (DD.MM.YYYY). "
            "\n- **posting_date**: Leave empty. "
            "\n- **tax_amount**: Explicitly find 'Tax', 'VAT', 'GST', 'MwSt'. Use '0.00' if not found. "
            "\n- **amount**: This is the TOTAL gross amount (including tax). "
            "\nFormat dates as DD.MM.YYYY. Ensure all amounts are numeric strings with '.' as decimal separator and NO thousands separators or currency symbols (e.g., '2724.57')."
        )),
        ("human", "{text}")
    ])
    result = (prompt | llm).invoke({"text": text})
    return [inv.model_dump() for inv in result.invoices]
