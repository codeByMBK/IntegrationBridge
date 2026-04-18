"""
SOAP service definition for IntegrationBridge.

Exposes a single SubmitInvoice RPC that receives invoice data from legacy
SOAP clients and translates each call into a JSON POST to the downstream REST API.
"""

import structlog
import requests
from spyne import Application, ServiceBase, Unicode, Float, rpc
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication

logger = structlog.get_logger(__name__)

DOWNSTREAM_URL = "http://downstream-api:8001/invoices"


class InvoiceSoapService(ServiceBase):
    """SOAP service that accepts SubmitInvoice calls from legacy clients."""

    @rpc(Unicode, Unicode, Float, Unicode, Unicode, _returns=Unicode)
    def SubmitInvoice(ctx, invoice_id, vendor, amount, currency, date):
        """
        Translate an incoming SOAP SubmitInvoice call into a downstream REST POST.

        Returns a SUCCESS or ERROR string to the SOAP caller.
        """
        log = logger.bind(invoice_id=invoice_id, vendor=vendor, amount=amount)
        log.info("soap_call_received")

        payload = {
            "invoice_id": invoice_id,
            "vendor": vendor,
            "amount": amount,
            "currency": currency,
            "date": date,
        }

        try:
            resp = requests.post(DOWNSTREAM_URL, json=payload, timeout=10)
            resp.raise_for_status()
            log.info("soap_forwarded_success", status_code=resp.status_code)
            return f"SUCCESS: Invoice {invoice_id} forwarded"
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            log.error("soap_forward_http_error", detail=detail)
            return f"ERROR: {detail}"
        except Exception as exc:
            log.error("soap_forward_error", detail=str(exc))
            return f"ERROR: {exc}"


# Build the spyne SOAP application using HttpTransport so it can be mounted
# via a2wsgi's WSGIMiddleware inside FastAPI.
soap_application = Application(
    services=[InvoiceSoapService],
    tns="integrationbridge.soap",
    name="InvoiceSoapService",
    in_protocol=Soap11(validator="lxml"),
    out_protocol=Soap11(),
)

soap_wsgi_app = WsgiApplication(soap_application)
