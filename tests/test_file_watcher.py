"""
File watcher integration test for IntegrationBridge.

Drops a valid XML invoice file into ./file_drop/, then polls the Downstream API
to confirm it was ingested within 10 seconds and moved to ./file_drop/processed/.
Assumes services are already running via docker compose.
"""

import os
import shutil
import time
import uuid

import pytest
import requests

BRIDGE_URL = "http://localhost:8000"
DOWNSTREAM_URL = "http://localhost:8001"

FILE_DROP_DIR = os.path.join(os.path.dirname(__file__), "..", "file_drop")
PROCESSED_DIR = os.path.join(FILE_DROP_DIR, "processed")


def _make_xml(invoice_id: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<invoice>
  <invoice_id>{invoice_id}</invoice_id>
  <vendor>Test Watcher Vendor</vendor>
  <amount>999.99</amount>
  <currency>USD</currency>
  <date>2025-07-01</date>
</invoice>
"""


@pytest.mark.timeout(30)
def test_xml_file_triggers_ingestion():
    # Use a unique invoice_id to avoid collisions with other test runs.
    unique_id = f"INV-{uuid.uuid4().hex[:6].upper()}"

    # Normalise to 4-digit format that passes the regex validator.
    # uuid hex digits are 0-9a-f; we'll use a numeric suffix guaranteed to be 4+ chars.
    invoice_id = f"INV-{str(abs(hash(unique_id)))[:4]}"

    # Step 1: baseline count.
    baseline = requests.get(f"{DOWNSTREAM_URL}/invoices").json()
    baseline_count = len(baseline)

    # Step 2: drop the XML file into file_drop.
    filename = f"test_{invoice_id}.xml"
    filepath = os.path.join(FILE_DROP_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as fh:
        fh.write(_make_xml(invoice_id))

    # Step 3: poll for up to 10 seconds.
    found = False
    for _ in range(10):
        time.sleep(1)
        invoices = requests.get(f"{DOWNSTREAM_URL}/invoices").json()
        if len(invoices) > baseline_count:
            # Verify correct invoice is present.
            ids = [inv["invoice_id"] for inv in invoices]
            if invoice_id in ids:
                found = True
                break

    assert found, f"Invoice {invoice_id} was not ingested within 10 seconds"

    # Step 4: verify file moved to processed/.
    processed_path = os.path.join(PROCESSED_DIR, filename)
    assert os.path.exists(processed_path), (
        f"File was not moved to processed/: {processed_path}"
    )
