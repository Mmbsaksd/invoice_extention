import json
import os
from typing import List, Set

STORAGE_FILE = "session_data.json"

class SessionStore:
    """Manages processed invoices with reactive JSON persistence."""
    def __init__(self):
        self._pending_invoices: List[dict] = []
        self._processed_file_hashes: Set[str] = set()
        self._sap_url: str = ""
        self._load()

    def _load(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r") as f:
                    data = json.load(f)
                    self._pending_invoices = data.get("invoices", [])
                    self._processed_file_hashes = set(data.get("hashes", []))
                    self._sap_url = data.get("sap_url", "")
            except: pass

    def _save(self):
        try:
            with open(STORAGE_FILE, "w") as f:
                json.dump({
                    "invoices": self._pending_invoices,
                    "hashes": list(self._processed_file_hashes),
                    "sap_url": self._sap_url
                }, f, indent=2)
        except: pass

    @property
    def pending_invoices(self) -> List[dict]:
        self._load()
        return self._pending_invoices

    @property
    def processed_file_hashes(self) -> Set[str]:
        self._load()
        return self._processed_file_hashes

    @property
    def sap_url(self) -> str:
        self._load()
        return self._sap_url

    @sap_url.setter
    def sap_url(self, value: str):
        self._sap_url = value
        self._save()

    def get_all_invoices(self) -> List[dict]:
        return self.pending_invoices

    def add_invoices(self, invoices: List[dict], file_hash: str = None):
        self._load()
        self._pending_invoices.extend(invoices)
        if file_hash:
            self._processed_file_hashes.add(file_hash)
        self._save()

    def remove_invoice(self, index: int):
        self._load()
        if 0 <= index < len(self._pending_invoices):
            self._pending_invoices.pop(index)
            self._save()

    def clear(self):
        self._pending_invoices = []
        self._processed_file_hashes = set()
        self._save()

session_store = SessionStore()
