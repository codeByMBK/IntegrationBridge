"""
Downstream API — simulates a modern internal CRM/ERP system.
Stores invoices in memory and exposes REST endpoints for create and retrieval.
"""

import uuid
from typing import List

import uvicorn
from fastapi import FastAPI

from models import InvoiceIn, InvoiceOut

app = FastAPI(
    title="Downstream API",
    description=__doc__,
    version="1.0.0",
)

# In-memory invoice store.
invoices: List[InvoiceOut] = []


@app.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(invoice: InvoiceIn) -> InvoiceOut:
    """Accept a JSON invoice, assign a UUID, store and return it."""
    record = InvoiceOut(id=str(uuid.uuid4()), **invoice.model_dump())
    invoices.append(record)
    return record


@app.get("/invoices", response_model=List[InvoiceOut])
def list_invoices() -> List[InvoiceOut]:
    """Return all stored invoices."""
    return invoices


@app.get("/health")
def health():
    return {"status": "ok", "service": "downstream-api"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8001)
