#!/usr/bin/env sh
set -eu

python -m ingestion.flows incoming \
  --incoming-dir "${AI4I_INCOMING_DIR:-data/incoming}" \
  --archive-dir "${AI4I_ARCHIVE_DIR:-data/archive}"
