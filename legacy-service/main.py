"""
Legacy Service — simulates a legacy accounts-payable ERP system.

On startup, waits for IntegrationBridge to be ready, then submits one sample
invoice via SOAP and exits. This is a one-shot runner, not a long-lived server.
"""

import sys
import time

from zeep import Client
from zeep.transports import Transport
import requests

WSDL_URL = "http://integration-bridge:8000/soap?wsdl"

# The spyne WSDL encodes the endpoint address using the Host header from the
# WSDL request. When running inside Docker, the WSDL returns localhost:8000
# which is unreachable from another container. We override the binding address
# to the correct Docker network hostname after fetching the WSDL.
SOAP_ENDPOINT = "http://integration-bridge:8000/soap"

SAMPLE_INVOICE = {
    "invoice_id": "INV-9001",
    "vendor": "Legacy Corp",
    "amount": 4200.0,
    "currency": "USD",
    "date": "2025-03-10",
}


def main() -> None:
    # Give IntegrationBridge time to fully initialise (health check may pass
    # before SOAP is mounted, so we add a safety buffer).
    print("[legacy-service] Waiting 8 seconds for IntegrationBridge to initialise...")
    time.sleep(8)

    print(f"[legacy-service] Connecting to SOAP WSDL at {WSDL_URL}")
    transport = Transport(session=requests.Session())
    client = Client(wsdl=WSDL_URL, transport=transport)

    # Override the endpoint so requests go to the Docker network address
    # (the WSDL embeds localhost:8000 which is only valid on the bridge host).
    service = client.create_service(
        "{integrationbridge.soap}InvoiceSoapService",
        SOAP_ENDPOINT,
    )

    print(f"[legacy-service] Calling SubmitInvoice with {SAMPLE_INVOICE}")
    result = service.SubmitInvoice(**SAMPLE_INVOICE)

    print(f"[legacy-service] Result: {result}")
    sys.exit(0)


if __name__ == "__main__":
    main()
