#!/usr/bin/env sh
set -eu

API_BASE_URL="${API_BASE_URL:-http://localhost:8080}"
PAYLOAD_DIR="${PAYLOAD_DIR:-evaluation/prediction_payloads}"
EXPECTATIONS="${EXPECTATIONS:-evaluation/expected_prediction_bands.json}"

python evaluation/check_prediction_payloads.py \
  --api-base-url "$API_BASE_URL" \
  --payload-dir "$PAYLOAD_DIR" \
  --expectations "$EXPECTATIONS"
