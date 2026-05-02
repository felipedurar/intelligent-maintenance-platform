#!/usr/bin/env sh
set -eu

prefect deployment run "ingest-incoming-ai4i-batches/incoming-ai4i-batches"
