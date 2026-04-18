#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing test dependencies..."
pip install -r tests/requirements.txt -q

echo "==> Running contract tests..."
pytest tests/test_contracts.py -v

echo "==> Running file watcher tests..."
pytest tests/test_file_watcher.py -v --timeout=30

echo "==> Running SOAP translation tests..."
pytest tests/test_soap_translation.py -v

echo "==> All tests passed."
