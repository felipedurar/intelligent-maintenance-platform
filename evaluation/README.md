# Evaluation Assets

This folder contains lightweight assets for manual and automated platform checks.

## Prediction Payloads

`prediction_payloads/` contains example API requests for `/api/v1/predictions`:

- `low_risk.json`: nominal operating condition.
- `medium_risk.json`: elevated wear and torque.
- `high_risk.json`: strong failure-rule indicators.
- `invalid_payload.json`: intentionally invalid product type for API validation checks.

## Expected Behavior

`expected_prediction_bands.json` defines broad risk-band expectations for the sample payloads.
These are not strict model-accuracy labels; they are smoke-test expectations to detect obvious
serving regressions after retraining.

## Run Smoke Test

With Docker Compose running and a champion model registered in MLflow:

```bash
./evaluation/run_prediction_smoke.sh
```

Override the API URL when needed:

```bash
API_BASE_URL=http://localhost:8080 ./evaluation/run_prediction_smoke.sh
```

## Agent Golden-Set Evaluation

`data/golden_set/agent_eval.jsonl` contains question, expected answer, expected tool, and
expected context cases for the RAG/agent layer.

Run deterministic checks only:

```bash
docker compose exec prefect-worker ./scripts/run_agent_evaluation.sh
```

Run OpenAI LLM-as-judge and log the report to MLflow:

```bash
docker compose exec prefect-worker ./scripts/run_agent_evaluation.sh --judge --mlflow
```

Run optional RAGAS metrics after installing evaluation extras:

```bash
pip install -e ".[eval]"
python -m evaluation.agent_eval --judge --ragas --mlflow
```

Reports are written to `evaluation/reports/agent_eval_latest.json` and
`evaluation/reports/agent_eval_latest.md`.

## Security Guardrail Evaluation

`data/golden_set/security_eval.jsonl` contains adversarial prompts for prompt injection,
secret extraction, topic restriction, and safe allowed-domain checks.

Run it with:

```bash
docker compose exec prefect-worker ./scripts/run_security_evaluation.sh
```

The latest report is written to `evaluation/reports/security_eval_latest.json`.
