from __future__ import annotations

import argparse
import json
import os
from numbers import Real
from tempfile import TemporaryDirectory
from typing import Any

import mlflow
import mlflow.pyfunc
from mlflow.tracking import MlflowClient
from prefect import flow, get_run_logger, task
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from training.constants import (
    CHAMPION_ALIAS,
    EXPERIMENT_NAME,
    FEATURE_COLUMNS,
    MODEL_NAME,
    TARGET_COLUMN,
)
from training.data import default_database_url, load_training_frame
from training.metrics import evaluate_classifier
from training.model_wrappers import log_probability_model

try:
    from training.pytorch_mlp import TorchMLPClassifier as ImportedTorchMLPClassifier
except ImportError:
    _TorchMLPClassifier: Any = None
else:
    _TorchMLPClassifier = ImportedTorchMLPClassifier


def default_mlflow_tracking_uri() -> str:
    return os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def _positive_probability(model: Any, x_test: Any) -> Any:
    if hasattr(model, "predict_proba"):
        return model.predict_proba(x_test)[:, 1]
    if hasattr(model, "decision_function"):
        return model.decision_function(x_test)
    return model.predict(x_test)


def _candidate_models(random_state: int) -> dict[str, Any]:
    candidates: dict[str, Any] = {
        "baseline_logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        class_weight="balanced",
                        max_iter=1000,
                        random_state=random_state,
                    ),
                ),
            ]
        ),
        "challenger_random_forest": RandomForestClassifier(
            class_weight="balanced",
            n_estimators=300,
            min_samples_leaf=2,
            random_state=random_state,
            n_jobs=-1,
        ),
    }
    if _TorchMLPClassifier is not None:
        candidates["deep_challenger_pytorch_mlp"] = _TorchMLPClassifier(
            hidden_dims=(32, 16),
            dropout=0.2,
            learning_rate=0.003,
            epochs=80,
            patience=10,
            random_state=random_state,
        )
    return candidates


@task
def train_candidates(
    database_url: str,
    mlflow_tracking_uri: str,
    test_size: float,
    random_state: int,
) -> list[dict[str, Any]]:
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(EXPERIMENT_NAME)

    frame = load_training_frame(database_url)
    x = frame[FEATURE_COLUMNS]
    y = frame[TARGET_COLUMN].astype(int)

    stratify = y if y.nunique() > 1 else None
    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    runs: list[dict[str, Any]] = []
    for candidate_name, model in _candidate_models(random_state).items():
        with mlflow.start_run(run_name=candidate_name) as run:
            model.fit(x_train, y_train)
            predictions = model.predict(x_test)
            scores = _positive_probability(model, x_test)
            metrics = evaluate_classifier(y_test, predictions, scores)

            mlflow.set_tags(
                {
                    "use_case": "predictive-maintenance",
                    "dataset": "AI4I 2020",
                    "target": TARGET_COLUMN,
                    "candidate": candidate_name,
                    "model_type": "classification",
                    "framework": "pytorch" if "pytorch" in candidate_name else "scikit-learn",
                    "owner": "datathon-ai-platform",
                    "risk_level": "medium",
                    "approval_status": "candidate",
                    "training_data_version": os.getenv("TRAINING_DATA_VERSION", "local-postgres"),
                    "feature_version": "ai4i-v1",
                    "git_sha": os.getenv("GIT_SHA", "local"),
                }
            )
            mlflow.log_params(
                {
                    "candidate_name": candidate_name,
                    "feature_count": len(FEATURE_COLUMNS),
                    "train_rows": len(x_train),
                    "test_rows": len(x_test),
                    "test_size": test_size,
                    "random_state": random_state,
                }
            )
            mlflow.log_metrics(
                {
                    key: float(value)
                    for key, value in metrics.items()
                    if isinstance(value, Real)
                }
            )

            with TemporaryDirectory() as tmp_dir:
                feature_path = os.path.join(tmp_dir, "feature_columns.json")
                confusion_path = os.path.join(tmp_dir, "confusion_matrix.json")
                with open(feature_path, "w", encoding="utf-8") as feature_file:
                    json.dump(FEATURE_COLUMNS, feature_file, indent=2)
                with open(confusion_path, "w", encoding="utf-8") as confusion_file:
                    json.dump(metrics["confusion_matrix"], confusion_file, indent=2)
                mlflow.log_artifact(feature_path, artifact_path="metadata")
                mlflow.log_artifact(confusion_path, artifact_path="metrics")

            log_probability_model(model, artifact_path="model")

            runs.append(
                {
                    "candidate_name": candidate_name,
                    "run_id": run.info.run_id,
                    "metrics": metrics,
                    "model_uri": f"runs:/{run.info.run_id}/model",
                }
            )

    return runs


@task
def register_best_model(
    candidates: list[dict[str, Any]],
    mlflow_tracking_uri: str,
) -> dict[str, Any]:
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    best = max(
        candidates,
        key=lambda item: (
            float(item["metrics"].get("average_precision", 0.0)),
            float(item["metrics"].get("recall", 0.0)),
            float(item["metrics"].get("f1", 0.0)),
        ),
    )

    model_version = mlflow.register_model(best["model_uri"], MODEL_NAME)
    client = MlflowClient()
    client.set_model_version_tag(
        name=MODEL_NAME,
        version=model_version.version,
        key="candidate_name",
        value=best["candidate_name"],
    )
    client.set_registered_model_alias(MODEL_NAME, CHAMPION_ALIAS, model_version.version)

    return {
        "model_name": MODEL_NAME,
        "model_version": model_version.version,
        "champion_alias": CHAMPION_ALIAS,
        "best_candidate": best["candidate_name"],
        "best_run_id": best["run_id"],
        "best_metrics": best["metrics"],
    }


@flow(name="train-ai4i-failure-classifier")
def train_ai4i_failure_classifier(
    database_url: str | None = None,
    mlflow_tracking_uri: str | None = None,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:
    logger = get_run_logger()
    resolved_database_url = database_url or default_database_url()
    resolved_mlflow_uri = mlflow_tracking_uri or default_mlflow_tracking_uri()

    logger.info("Training AI4I classifier with MLflow at %s", resolved_mlflow_uri)
    candidates = train_candidates(
        resolved_database_url,
        resolved_mlflow_uri,
        test_size,
        random_state,
    )
    result = register_best_model(candidates, resolved_mlflow_uri)
    logger.info("Training finished: %s", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train AI4I predictive-maintenance models.")
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--mlflow-tracking-uri", default=None)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    train_ai4i_failure_classifier(
        database_url=args.database_url,
        mlflow_tracking_uri=args.mlflow_tracking_uri,
        test_size=args.test_size,
        random_state=args.random_state,
    )


if __name__ == "__main__":
    main()
