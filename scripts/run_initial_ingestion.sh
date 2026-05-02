#!/usr/bin/env sh
set -eu

python -m ingestion.flows initial --csv-path "${AI4I_CSV_PATH:-data/raw/ai4i2020.csv}"
