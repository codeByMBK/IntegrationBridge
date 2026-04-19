# IntegrationBridge

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-009688?logo=fastapi)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)
![Tests](https://img.shields.io/badge/tests-10%20passed-brightgreen)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

A middleware layer facilitating integration between a legacy file-based SOAP system and a modern REST API, with OpenAPI documentation and containerised deployment. IntegrationBridge acts as the translation and routing hub: it accepts SOAP calls from legacy clients, picks up XML invoice files from a watched directory, and exposes its own REST API — forwarding all ingested data to a downstream CRM/ERP REST service.

---

## Architecture

```
┌─────────────────────────────┐
│  Legacy System (SOAP client) │
│  legacy-service container    │
└─────────────┬───────────────┘
              │ SOAP SubmitInvoice
              ▼
┌─────────────────────────────────────────┐
│         IntegrationBridge :8000          │
│                                         │
│  POST /soap       ← SOAP endpoint       │
│  POST /invoices   ← REST endpoint       │
│  GET  /invoices   ← REST proxy          │
│  GET  /health                           │
│  GET  /docs       ← Swagger UI          │
│  /app/file_drop   ← File watcher        │
└─────────────┬───────────────────────────┘
              │ HTTP POST (JSON)
              ▼
┌─────────────────────────────┐
│     Downstream API :8001     │
│                             │
│  POST /invoices  (store)    │
│  GET  /invoices  (list)     │
│  GET  /health               │
└─────────────────────────────┘

File system:
./file_drop/*.xml  ──►  IntegrationBridge file watcher  ──►  Downstream API
                                                         ──►  ./file_drop/processed/
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| REST Framework | FastAPI 0.111.0 |
| SOAP Framework | spyne 2.14.0 |
| WSGI/ASGI Bridge | a2wsgi 1.10.4 |
| XML Parsing | lxml 5.1.0 |
| File Watching | watchdog 4.0.0 |
| Structured Logging | structlog 24.1.0 |
| Data Validation | pydantic 2.7.1 |
| HTTP Client | requests 2.31.0 |
| ASGI Server | uvicorn 0.29.0 |
| Containerisation | Docker + Docker Compose |
| Testing | pytest 8.2.0, zeep 4.2.1, pytest-timeout 2.3.1 |

---

## Project Structure

```
IntegrationBridge/
├── docker-compose.yml
├── setup.sh                  # Build + start all services
├── teardown.sh               # Stop + remove all containers
├── README.md
├── PROGRESS.md               # Build checklist (agent handoff doc)
│
├── downstream-api/           # Service 3 — modern CRM/ERP mock
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── models.py             # InvoiceIn + InvoiceOut Pydantic models
│   └── main.py               # FastAPI app, in-memory store, port 8001
│
├── integration-bridge/       # Service 2 — main middleware (port 8000)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── models.py             # InvoiceIn with full validation constraints
│   ├── soap_service.py       # spyne SOAP service definition
│   ├── file_watcher.py       # watchdog file watcher
│   ├── main.py               # FastAPI app + SOAP mount + lifespan
│   └── openapi_description.md
│
├── legacy-service/           # Service 1 — one-shot SOAP client
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py               # zeep SOAP client, submits INV-9001, exits
│
├── tests/
│   ├── requirements.txt
│   ├── run_tests.sh          # Installs deps + runs all pytest suites
│   ├── test_contracts.py     # Health + REST contract tests (8 cases)
│   ├── test_file_watcher.py  # End-to-end file drop ingestion test
│   └── test_soap_translation.py  # Raw SOAP HTTP → downstream REST test
│
└── file_drop/
    ├── sample_invoice.xml    # Example XML invoice for manual testing
    └── processed/            # Watcher moves files here after ingestion
```

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v4+)
- Docker Compose (bundled with Docker Desktop)

No local Python installation required — all services run in containers.

---

## Quick Start

```bash
git clone https://github.com/codeByMBK/IntegrationBridge.git
cd IntegrationBridge
chmod +x setup.sh teardown.sh tests/run_tests.sh
./setup.sh
```

`setup.sh` will:
1. Build all 3 Docker images from scratch
2. Start `downstream-api` and `integration-bridge` (with health checks)
3. Run `legacy-service` once — prints `SUCCESS: Invoice INV-9001 forwarded` and exits

---

## Endpoints

### IntegrationBridge (port 8000)

| Method | Path | Description |
|---|---|---|
| `POST` | `/invoices` | Accept JSON invoice, validate, forward to downstream |
| `GET` | `/invoices` | Proxy list of all invoices from downstream |
| `GET` | `/health` | Returns `{"status":"ok","service":"integration-bridge"}` |
| `POST` | `/soap` | SOAP endpoint — `SubmitInvoice(invoice_id, vendor, amount, currency, date)` |
| `GET` | `/soap?wsdl` | WSDL descriptor for the SOAP service |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc UI |

### Downstream API (port 8001)

| Method | Path | Description |
|---|---|---|
| `POST` | `/invoices` | Accept JSON invoice, store in memory, return with UUID |
| `GET` | `/invoices` | Return list of all stored invoices |
| `GET` | `/health` | Returns `{"status":"ok","service":"downstream-api"}` |
| `GET` | `/docs` | Swagger UI |

---

## File Watcher

Drop any `.xml` file matching the invoice schema into `./file_drop/`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<invoice>
  <invoice_id>INV-0001</invoice_id>
  <vendor>Acme Corp</vendor>
  <amount>1500.00</amount>
  <currency>EUR</currency>
  <date>2025-01-15</date>
</invoice>
```

The IntegrationBridge file watcher picks it up within ~1 second, forwards it to the Downstream API, and moves the file to `./file_drop/processed/`.

**Invoice validation rules (enforced by Pydantic):**

| Field | Constraint |
|---|---|
| `invoice_id` | Must match `^INV-[0-9]{4,}$` (e.g. `INV-0001`) |
| `vendor` | 2–100 characters |
| `amount` | Must be > 0 |
| `currency` | Exactly 3 uppercase letters (e.g. `EUR`, `USD`, `GBP`) |
| `date` | Format `YYYY-MM-DD` |

---

## Using the SOAP Endpoint Directly

```bash
curl -X POST http://localhost:8000/soap \
  -H "Content-Type: text/xml" \
  -H "SOAPAction: SubmitInvoice" \
  -d '<?xml version="1.0" encoding="utf-8"?>
<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:tns="integrationbridge.soap">
  <soap-env:Body>
    <tns:SubmitInvoice>
      <tns:invoice_id>INV-0001</tns:invoice_id>
      <tns:vendor>Acme Corp</tns:vendor>
      <tns:amount>1500.00</tns:amount>
      <tns:currency>EUR</tns:currency>
      <tns:date>2025-01-15</tns:date>
    </tns:SubmitInvoice>
  </soap-env:Body>
</soap-env:Envelope>'
```

WSDL: `http://localhost:8000/soap?wsdl`

---

## Running Tests

Services must be running before executing tests.

```bash
./teardown.sh          # ensure clean state
./setup.sh             # start services
./tests/run_tests.sh   # install deps + run all suites
```

**Test suites:**

| File | Coverage |
|---|---|
| `test_contracts.py` | Health checks, OpenAPI schema, valid POST, 3× 422 validation rejections, GET list |
| `test_file_watcher.py` | Drops XML, polls downstream for 10s, asserts ingestion + file moved to `processed/` |
| `test_soap_translation.py` | Raw SOAP HTTP POST → asserts `SUCCESS` response + record in downstream |

All 10 tests pass in ~1.3 seconds.

---

## Stopping

```bash
./teardown.sh
```

---

## Implementation Notes

- **SOAP routing**: Starlette's `Mount` only matches paths with a trailing slash prefix, so `POST /soap` (no trailing slash) would 404. Fixed with a custom `SoapDispatchMiddleware` ASGI wrapper that intercepts `/soap*` before Starlette routing.
- **WSDL endpoint address**: spyne embeds the request `Host` header into the WSDL's `<wsdl:address location>`. The legacy-service uses `zeep`'s `create_service()` to override this with the Docker network hostname.
- **Pydantic v2**: All validators use `@field_validator` (the v2 API); the deprecated `@validator` from v1 is not used.
- **Structlog**: Configured with `PrintLoggerFactory` + `structlog.processors.add_log_level` (not the stdlib-specific `add_logger_name` which requires a stdlib Logger).
- **In-memory storage**: The downstream API stores invoices in a Python list. Data is lost on container restart — intentional per the spec.

