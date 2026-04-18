#!/usr/bin/env bash
set -euo pipefail

echo "==> Building and starting IntegrationBridge..."
docker compose build --no-cache
docker compose up -d downstream-api integration-bridge
echo "==> Waiting for services to be healthy..."
docker compose up legacy-service
echo ""
echo "==> Services running:"
echo "    IntegrationBridge REST + SOAP : http://localhost:8000"
echo "    IntegrationBridge Swagger UI  : http://localhost:8000/docs"
echo "    Downstream API               : http://localhost:8001"
echo "    Downstream API Swagger UI    : http://localhost:8001/docs"
echo "    SOAP endpoint                : http://localhost:8000/soap"
echo ""
echo "==> Drop any XML invoice file into ./file_drop/ to trigger file-watcher ingestion."
