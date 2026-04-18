from pydantic import BaseModel


class InvoiceIn(BaseModel):
    invoice_id: str
    vendor: str
    amount: float
    currency: str
    date: str


class InvoiceOut(InvoiceIn):
    id: str
