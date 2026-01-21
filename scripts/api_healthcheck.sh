#!/bin/bash
set -euo pipefail

# Settings
TARGET_URL="${TARGET_URL:-http://host.docker.internal:8001/openapi.json}"
MAX_RETRIES="${MAX_RETRIES:-5}"
SLEEP_TIME="${SLEEP_TIME:-2}"

echo "Starting API Health-check for $TARGET_URL..."

for i in $(seq 1 "$MAX_RETRIES"); do
  HTTP_STATUS="$(curl -o /dev/null -s -w "%{http_code}" "$TARGET_URL" || true)"

  if [ "$HTTP_STATUS" -eq 200 ] 2>/dev/null; then
    echo "SUCCESS: API is live and routes are loaded (Status 200)."
    exit 0
  else
    echo "RETRY $i/$MAX_RETRIES: API returned ${HTTP_STATUS:-unknown}. Waiting ${SLEEP_TIME}s..."
    sleep "$SLEEP_TIME"
  fi
done

echo "ERROR: API Health-check failed after $MAX_RETRIES attempts."
exit 1