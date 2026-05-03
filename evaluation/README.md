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
