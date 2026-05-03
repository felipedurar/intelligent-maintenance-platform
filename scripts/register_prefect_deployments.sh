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

prefect deploy src/training/train_model.py:train_ai4i_failure_classifier \
  --name train-ai4i-failure-classifier \
  --pool "$POOL_NAME"

prefect deploy src/rag/flows.py:index_rag_documentation \
  --name index-rag-documentation \
  --pool "$POOL_NAME"

prefect deploy src/monitoring/flows.py:detect_ai4i_drift \
  --name detect-ai4i-drift \
  --pool "$POOL_NAME"
