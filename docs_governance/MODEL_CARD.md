# Model Card

## Model Overview

The model predicts the probability of `machine_failure` for industrial machine observations
from the AI4I 2020 predictive-maintenance dataset. It is used as a decision-support component
for maintenance prioritization, not as an automatic shutdown or work-order approval system.

## Intended Use

- Estimate failure risk from process and sensor measurements.
- Explain important operational drivers behind model behavior.
- Support maintenance triage discussions through the FastAPI prediction endpoint and the
  OpenAI-powered assistant.

## Training Data

- Dataset: AI4I 2020 Predictive Maintenance Dataset.
- Raw source: `data/raw/ai4i2020.csv`, tracked with DVC.
- Processed source: `data/processed/ai4i_features_latest.csv`.
- Target: `machine_failure`.
- Fairness axis used in this project: `product_type` (`L`, `M`, `H`).

## Candidate Models

- Balanced logistic regression baseline.
- Class-balanced random forest challenger.
- Class-balanced extra trees benchmark challenger.
- PyTorch MLP deep challenger when PyTorch is available in the training runtime.

The training flow logs candidates to MLflow and registers the best model under
`ai4i-machine-failure-classifier` with the `candidate` alias. Production serving uses the
separate `champion` alias only after human approval.

## Evaluation Evidence

The project generates reproducible benchmark and fairness/explainability artifacts:

- `evaluation/reports/model_benchmark_latest.json`
- `evaluation/reports/model_benchmark_latest.md`
- `evaluation/reports/explainability_fairness_latest.json`
- `evaluation/reports/explainability_fairness_latest.md`

The benchmark ranks candidates by average precision first because machine failures are rare,
then by recall and F1. The explainability/fairness report uses permutation importance and
group metrics by `product_type`, including precision, recall, false positive rate, and false
negative rate.

## Limitations

- AI4I is synthetic and may not represent a specific plant, machine fleet, maintenance policy,
  or sensor calibration profile.
- Failure labels are highly imbalanced, so threshold selection must be reviewed for the actual
  business cost of false positives and false negatives.
- Fairness analysis is limited to operational product groups available in the dataset. It is not
  a demographic fairness analysis.

## Monitoring

The platform includes PSI-based drift detection over the processed feature dataset and
Prometheus/Grafana operational metrics for the serving API.

## Approval Status

MLflow model versions are tagged with governance metadata such as owner, risk level, candidate
name, feature version, training data version, and approval status. Training sets
`approval_status=pending`; the promotion command records `approved_by`, `approved_at`, and
`promotion_reason`, preserves the previous production model as `previous_champion`, and then
updates the production `champion` alias.
