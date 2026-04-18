"""
IntegrationBridge — Core Service

Middleware gateway that:
- Accepts SOAP SubmitInvoice calls from legacy systems and translates them to REST
- Exposes its own REST API (POST/GET /invoices) forwarding data to the Downstream API
- Watches /app/file_drop for XML files and ingests them automatically
- Provides OpenAPI documentation at /docs and /redoc
"""

import structlog
import structlog.stdlib
import logging
import requests
import uvicorn

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Response
from a2wsgi import WSGIMiddleware

from models import InvoiceIn
from soap_service import soap_wsgi_app
from file_watcher import start_file_watcher

# ---------------------------------------------------------------------------
# Structlog configuration — output structured JSON to stdout.
# Must be done at module level so all loggers pick it up.
# ---------------------------------------------------------------------------
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

DOWNSTREAM_URL = "http://downstream-api:8001"


# ---------------------------------------------------------------------------
# Application lifespan — start file watcher before accepting traffic.
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup_starting_file_watcher")
    start_file_watcher()
    logger.info("startup_complete")
    yield
    logger.info("shutdown")

from starlette.types import ASGIApp, Receive, Scope, Send

# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title="IntegrationBridge",
    version="1.0.0",
    description=__doc__,
    contact={"name": "SMBC Integration Team"},
    lifespan=lifespan,
    redirect_slashes=False,
)

# ---------------------------------------------------------------------------
# SOAP dispatch middleware
#
# Starlette's Mount only matches paths with a trailing slash prefix, so
# POST /soap (bare, no slash) never reaches a mounted sub-app. Instead we
# intercept at the middleware level: any request whose path starts with /soap
# is forwarded directly to the spyne WSGI app via a2wsgi, before Starlette's
# router even sees it.
# ---------------------------------------------------------------------------
_soap_asgi = WSGIMiddleware(soap_wsgi_app)


class SoapDispatchMiddleware:
    """Route /soap* requests to the spyne WSGI app; everything else to FastAPI."""

    def __init__(self, fastapi_app: ASGIApp, soap_app: ASGIApp) -> None:
        self._fastapi = fastapi_app
        self._soap = soap_app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            path: str = scope.get("path", "")
            if path.startswith("/soap"):
                # Strip the /soap prefix so spyne sees / or /?wsdl.
                scope = dict(scope)
                scope["path"] = path[len("/soap"):] or "/"
                scope["raw_path"] = scope["path"].encode()
                await self._soap(scope, receive, send)
                return
        await self._fastapi(scope, receive, send)



# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.post("/invoices")
def create_invoice(invoice: InvoiceIn):
    """Validate and forward a JSON invoice to the Downstream API."""
    log = logger.bind(invoice_id=invoice.invoice_id)
    log.info("rest_post_invoice_received")

    try:
        resp = requests.post(
            f"{DOWNSTREAM_URL}/invoices",
            json=invoice.model_dump(),
            timeout=10,
        )
    except requests.RequestException as exc:
        log.error("downstream_unreachable", detail=str(exc))
        raise HTTPException(status_code=502, detail=f"Downstream API unreachable: {exc}")

    log.info("rest_post_invoice_forwarded", status_code=resp.status_code)
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@app.get("/invoices")
def list_invoices():
    """Proxy the invoice list from the Downstream API."""
    try:
        resp = requests.get(f"{DOWNSTREAM_URL}/invoices", timeout=10)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail=f"Downstream API unreachable: {exc}")
    return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")


@app.get("/health")
def health():
    return {"status": "ok", "service": "integration-bridge"}


# ---------------------------------------------------------------------------
# Wrap the FastAPI app with the SOAP dispatcher so /soap* paths are handled
# before Starlette's routing layer. uvicorn.run targets this wrapper.
# ---------------------------------------------------------------------------
asgi_app = SoapDispatchMiddleware(app, _soap_asgi)

if __name__ == "__main__":
    uvicorn.run(asgi_app, host="0.0.0.0", port=8000)
