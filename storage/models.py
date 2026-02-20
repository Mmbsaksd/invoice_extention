from typing import Optional, List
from pydantic import BaseModel, Field

class InvoiceData(BaseModel):
    """Production Schema with Validation Metadata."""
    supplier: Optional[str] = Field(None)
    invoice_date: Optional[str] = Field(None)
    reference: Optional[str] = Field(None)
    posting_date: Optional[str] = Field(None)
    amount: Optional[str] = Field(None)
    tax_amount: Optional[str] = Field(None)
    validation_error: Optional[str] = Field(None)

class InvoiceList(BaseModel):
    invoices: List[InvoiceData]
