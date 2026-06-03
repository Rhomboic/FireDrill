"""In-memory invoice repository.

A stand-in data store: it reads seed invoices from data/invoices.json. Services
go through this repository rather than touching the data file directly.
"""

import json
from pathlib import Path

_DATA = Path(__file__).resolve().parents[2] / "data" / "invoices.json"


def all_invoices() -> list[dict]:
    return json.loads(_DATA.read_text())


def get_invoice(invoice_id: str) -> dict | None:
    for inv in all_invoices():
        if inv["id"] == invoice_id:
            return inv
    return None
