#!/usr/bin/env sh
set -eu

POOL_NAME="${PREFECT_WORK_POOL:-datathon-local}"

until prefect work-pool ls >/dev/null 2>&1; do
  echo "Waiting for Prefect API..."
  sleep 2
done

prefect work-pool create --type process "$POOL_NAME" >/dev/null 2>&1 || true

prefect deploy src/ingestion/flows.py:ingest_initial_ai4i_dataset \
  --name initial-ai4i-dataset \
  --pool "$POOL_NAME"

prefect deploy src/ingestion/flows.py:ingest_incoming_ai4i_batches \
  --name incoming-ai4i-batches \
  --pool "$POOL_NAME"
