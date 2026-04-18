"""
SOAP-to-REST translation test for IntegrationBridge.

Sends a raw SOAP XML envelope to the /soap endpoint and verifies:
1. HTTP 200 response with SUCCESS in the body.
2. The invoice subsequently appears in the Downstream API store.
Assumes services are already running via docker compose.
"""

import requests
import pytest

BRIDGE_URL = "http://localhost:8000"
DOWNSTREAM_URL = "http://localhost:8001"

SOAP_ENVELOPE = """<?xml version="1.0" encoding="utf-8"?>
<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:tns="integrationbridge.soap">
  <soap-env:Body>
    <tns:SubmitInvoice>
      <tns:invoice_id>INV-SOAP-001</tns:invoice_id>
      <tns:vendor>SOAP Vendor</tns:vendor>
      <tns:amount>999.0</tns:amount>
      <tns:currency>GBP</tns:currency>
      <tns:date>2025-06-01</tns:date>
    </tns:SubmitInvoice>
  </soap-env:Body>
</soap-env:Envelope>"""

SOAP_HEADERS = {
    "Content-Type": "text/xml",
    "SOAPAction": "SubmitInvoice",
}


def test_soap_submit_invoice():
    # Step 1: Send the raw SOAP envelope.
    resp = requests.post(f"{BRIDGE_URL}/soap", data=SOAP_ENVELOPE, headers=SOAP_HEADERS)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert "SUCCESS" in resp.text, f"Expected SUCCESS in response: {resp.text}"

    # Step 2: Verify the invoice was forwarded to the Downstream API.
    invoices_resp = requests.get(f"{DOWNSTREAM_URL}/invoices")
    assert invoices_resp.status_code == 200
    invoice_ids = [inv["invoice_id"] for inv in invoices_resp.json()]
    assert "INV-SOAP-001" in invoice_ids, (
        f"INV-SOAP-001 not found in downstream invoices: {invoice_ids}"
    )
