#!/usr/bin/env sh
set -eu

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "OPENAI_API_KEY is required to run RAGAS evaluation." >&2
  exit 1
fi

python -m evaluation.agent_eval \
  --golden-set "${GOLDEN_SET_PATH:-data/golden_set/agent_eval.jsonl}" \
  --report-dir "${AGENT_EVAL_REPORT_DIR:-evaluation/reports}" \
  --ragas \
  --require-ragas \
  "$@"
