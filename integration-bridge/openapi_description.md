# IntegrationBridge API

A middleware API gateway that translates between legacy SOAP/XML systems and modern REST APIs.

## Features

- **SOAP → REST translation**: Accepts SOAP `SubmitInvoice` calls and forwards them as JSON to the Downstream API.
- **REST API**: Exposes `POST /invoices` and `GET /invoices` with full validation.
- **File Watcher**: Monitors `/app/file_drop` for XML invoice files and ingests them automatically.
- **Structured Logging**: All actions logged as structured JSON using `structlog`.

## Invoice Schema

All invoices must conform to:

| Field | Type | Constraint |
|---|---|---|
| `invoice_id` | string | Pattern `INV-NNNN` (4+ digits) |
| `vendor` | string | 2–100 characters |
| `amount` | float | Must be > 0 |
| `currency` | string | Exactly 3 uppercase letters |
| `date` | string | Format `YYYY-MM-DD` |
