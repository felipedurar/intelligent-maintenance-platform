#!/usr/bin/env sh
set -eu

python -m evaluation.agent_eval \
  --golden-set "${GOLDEN_SET_PATH:-data/golden_set/agent_eval.jsonl}" \
  --report-dir "${AGENT_EVAL_REPORT_DIR:-evaluation/reports}" \
  "$@"
