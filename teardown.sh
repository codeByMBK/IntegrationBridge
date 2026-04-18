#!/usr/bin/env bash
set -euo pipefail
echo "==> Stopping and removing all IntegrationBridge containers..."
docker compose down -v --remove-orphans
echo "==> Done."
