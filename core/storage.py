import json
import os
from typing import List, Optional
from pydantic import BaseModel, Field

STORAGE_FILE = "session_data.json"

class InvoiceData(BaseModel):
    """Production Schema for Validated Invoices."""
    supplier: Optional[str] = Field(None)
    invoice_date: Optional[str] = Field(None)
    reference: Optional[str] = Field(None)
    posting_date: Optional[str] = Field(None)
    amount: Optional[str] = Field(None)
    tax_amount: Optional[str] = Field(None)
    validation_error: Optional[str] = Field(None)

class InvoiceList(BaseModel):
    invoices: List[InvoiceData]

class SessionStore:
    """Persistently manages pending invoices with robust deduplication."""
    def __init__(self):
        self.invoices: List[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r") as f:
                    self.invoices = json.load(f).get("invoices", [])
            except: pass

    def _save(self):
        try:
            with open(STORAGE_FILE, "w") as f:
                json.dump({"invoices": self.invoices}, f, indent=2)
        except: pass

    def get_all_invoices(self):
        self._load()
        return self.invoices

    def add_invoices(self, new_invoices: List[dict]):
        self._load()
        # Robust deduplication using composite key (Supplier + Reference)
        existing_keys = {
            f"{i.get('supplier')}_{i.get('reference')}".lower().strip() 
            for i in self.invoices
        }
        
        added_count = 0
        for inv in new_invoices:
            key = f"{inv.get('supplier')}_{inv.get('reference')}".lower().strip()
            if key not in existing_keys:
                self.invoices.append(inv)
                existing_keys.add(key)
                added_count += 1
        
        if added_count > 0:
            self._save()

    def remove_invoice(self, index: int):
        self._load()
        if 0 <= index < len(self.invoices):
            self.invoices.pop(index)
            self._save()

    def clear(self):
        self.invoices = []
        self._save()

session_store = SessionStore()
