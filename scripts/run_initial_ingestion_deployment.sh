#!/usr/bin/env sh
set -eu

prefect deployment run "ingest-initial-ai4i-dataset/initial-ai4i-dataset"
