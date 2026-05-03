#!/usr/bin/env sh
set -eu

python -m evaluation.security_eval \
  --security-set "${SECURITY_EVAL_SET_PATH:-data/golden_set/security_eval.jsonl}" \
  --report-dir "${SECURITY_EVAL_REPORT_DIR:-evaluation/reports}" \
  "$@"
