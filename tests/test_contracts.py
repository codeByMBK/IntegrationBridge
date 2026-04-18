"""
OpenAPI contract tests for IntegrationBridge.

These tests verify health endpoints, OpenAPI schema availability, and
REST endpoint behavior (valid + invalid submissions).
Assumes services are already running via docker compose.
"""

import requests
import pytest

BRIDGE_URL = "http://localhost:8000"
DOWNSTREAM_URL = "http://localhost:8001"

VALID_INVOICE = {
    "invoice_id": "INV-0100",
    "vendor": "Test Vendor",
    "amount": 250.00,
    "currency": "GBP",
    "date": "2025-06-01",
}


def test_bridge_health():
    resp = requests.get(f"{BRIDGE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "integration-bridge"


def test_downstream_health():
    resp = requests.get(f"{DOWNSTREAM_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "downstream-api"


def test_bridge_openapi_schema_exists():
    resp = requests.get(f"{BRIDGE_URL}/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema


def test_post_invoice_valid():
    resp = requests.post(f"{BRIDGE_URL}/invoices", json=VALID_INVOICE)
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["invoice_id"] == VALID_INVOICE["invoice_id"]


def test_post_invoice_invalid_amount():
    payload = {**VALID_INVOICE, "invoice_id": "INV-0101", "amount": -5}
    resp = requests.post(f"{BRIDGE_URL}/invoices", json=payload)
    assert resp.status_code == 422


def test_post_invoice_invalid_currency():
    payload = {**VALID_INVOICE, "invoice_id": "INV-0102", "currency": "eu"}
    resp = requests.post(f"{BRIDGE_URL}/invoices", json=payload)
    assert resp.status_code == 422


def test_post_invoice_invalid_id_format():
    payload = {**VALID_INVOICE, "invoice_id": "BADINV"}
    resp = requests.post(f"{BRIDGE_URL}/invoices", json=payload)
    assert resp.status_code == 422


def test_get_invoices_returns_list():
    resp = requests.get(f"{BRIDGE_URL}/invoices")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
