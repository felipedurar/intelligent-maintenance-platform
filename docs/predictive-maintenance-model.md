# Predictive Maintenance Model

This document defines the model and feature direction for the AI4I 2020 predictive-maintenance use case.

## Task

Primary task:

```text
Predict Machine failure as a binary classification problem.
```

Model output:

- failure probability
- risk class such as `low`, `medium`, `high`
- model version
- feature version
- optional explanation/top contributing features

Failure-mode labels:

- `TWF`
- `HDF`
- `PWF`
- `OSF`
- `RNF`

These labels can support diagnostics and evaluation slices, but they should not be used as input features for the primary failure classifier because they directly encode post-outcome failure information.

## Raw Columns

Expected input columns:

- `UDI`
- `Product ID`
- `Type`
- `Air temperature [K]`
- `Process temperature [K]`
- `Rotational speed [rpm]`
- `Torque [Nm]`
- `Tool wear [min]`
- `Machine failure`
- `TWF`
- `HDF`
- `PWF`
- `OSF`
- `RNF`

## Feature Engineering

Recommended feature columns:

- `type_encoded` or one-hot encoded product type.
- `air_temperature_k`.
- `process_temperature_k`.
- `temperature_delta_k = process_temperature_k - air_temperature_k`.
- `rotational_speed_rpm`.
- `torque_nm`.
- `tool_wear_min`.
- `rotational_speed_rad_s`.
- `power_w = torque_nm * rotational_speed_rad_s`.
- `torque_speed_interaction`.
- `tool_wear_by_torque`.
- `temperature_delta_low_flag`.
- `power_low_flag`.
- `power_high_flag`.
- `overstrain_margin`, using product-type thresholds.

Known physics-inspired conditions from the dataset description can be useful as engineered features:

- Heat dissipation risk: low temperature delta and low rotational speed.
- Power failure risk: power outside expected operating range.
- Overstrain risk: tool wear multiplied by torque relative to product-type threshold.

## Baseline And Challenger Models

Recommended baseline:

- Logistic Regression with class weighting.

Recommended challengers:

- Random Forest.
- Gradient Boosting, XGBoost, or LightGBM if dependencies are acceptable.
- Optional PyTorch MLP for Datathon PyTorch demonstration.

Because the dataset is tabular and relatively small, tree-based models may outperform a neural network and are easier to explain.

## Metrics

Use classification metrics that handle imbalance:

- ROC AUC.
- PR AUC.
- F1.
- Recall for the failure class.
- Precision for the failure class.
- Confusion matrix.

In predictive maintenance, recall is often important because missing an actual failure can be expensive. Precision still matters because too many false alarms can waste maintenance resources.

## MLflow Logging Contract

Training should log:

- model name.
- model type.
- dataset version.
- feature version.
- git SHA.
- random seed.
- train/test split strategy.
- class balance.
- feature list.
- hyperparameters.
- ROC AUC.
- PR AUC.
- F1.
- precision.
- recall.
- confusion matrix artifact.
- feature importance or explanation artifact when available.
- Evidently drift reference artifact.

Current implementation:

- baseline: class-balanced logistic regression with standard scaling.
- challenger: class-balanced random forest.
- deep challenger: PyTorch MLP with standardized tabular inputs, class-imbalance weighting, dropout, and early stopping when PyTorch is available in the training runtime.
- selection metric: average precision first, then recall and F1 as tie-breakers.
- registry name: `ai4i-machine-failure-classifier`.
- training alias: `candidate`.
- serving alias: `champion`.
- serving flavor: MLflow pyfunc wrapper returning `failure_probability`, so sklearn and PyTorch candidates share the same production serving contract.

Required tags:

- `model_name`
- `model_type`
- `owner`
- `risk_level`
- `approval_status`
- `training_data_version`
- `feature_version`
- `git_sha`

## Serving Contract

Serving should:

1. Load only approved/champion model versions from MLflow.
2. Load preprocessing artifacts and the model from cloud object storage through MLflow.
3. Validate incoming feature payloads.
4. Apply the same feature transformations used during training.
5. Return failure probability, risk class, model version, feature version, and explanation metadata.
6. Emit metrics for latency, errors, prediction counts, model version, and risk-class distribution.

## Promotion Gate

Training and production promotion are intentionally separate:

1. The training flow registers the best model version and points the MLflow `candidate` alias to it.
2. The candidate version must have `approval_status=pending` and `validation_status=passed`.
3. Benchmark and explainability/fairness reports must exist and have `status=ok`.
4. A human reviewer runs `scripts/promote_model.sh` with `--approved-by` and `--reason`.
5. The promotion command tags the model version with `approval_status=approved`,
   `approved_by`, `approved_at`, and `promotion_reason`.
6. The previous production version is preserved with the `previous_champion` alias before
   the new version receives the `champion` alias.

## Drift Contract

Evidently jobs should compare reference data against current batches for:

- raw feature drift.
- engineered feature drift.
- prediction drift.
- target drift when labels are available.
- performance drift when labels are available.

The initial static dataset can be split into reference and current/holdout slices to demonstrate drift reports. Future CSV batches should be ingested through `data/incoming/` or cloud object storage and compared against the approved reference dataset.
