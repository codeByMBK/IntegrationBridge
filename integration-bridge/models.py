import re

from pydantic import BaseModel, field_validator


class InvoiceIn(BaseModel):
    invoice_id: str
    vendor: str
    amount: float
    currency: str
    date: str

    @field_validator("invoice_id")
    @classmethod
    def validate_invoice_id(cls, v: str) -> str:
        if not re.match(r"^INV-[0-9]{4,}$", v):
            raise ValueError("invoice_id must match pattern INV-NNNN (4+ digits), e.g. INV-0001")
        return v

    @field_validator("vendor")
    @classmethod
    def validate_vendor(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 100:
            raise ValueError("vendor must be between 2 and 100 characters")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("amount must be greater than 0")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not re.match(r"^[A-Z]{3}$", v):
            raise ValueError("currency must be exactly 3 uppercase letters, e.g. USD")
        return v

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "invoice_id": "INV-0001",
                    "vendor": "Acme Corp",
                    "amount": 1500.00,
                    "currency": "EUR",
                    "date": "2025-01-15",
                }
            ]
        }
    }
