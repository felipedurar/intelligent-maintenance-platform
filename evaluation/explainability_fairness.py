from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split

from evaluation.model_benchmark import DEFAULT_INPUT_PATH, DEFAULT_REPORT_DIR, normalize_feature_columns
from training.constants import FEATURE_COLUMNS, TARGET_COLUMN
from training.metrics import evaluate_classifier
from training.train_model import _candidate_models, _positive_probability

GROUP_COLUMN = "product_type"


def _false_rates(confusion_matrix: list[list[int]]) -> dict[str, float]:
    if len(confusion_matrix) < 2 or len(confusion_matrix[0]) < 2:
        return {"false_positive_rate": 0.0, "false_negative_rate": 0.0}
    tn, fp = confusion_matrix[0]
    fn, tp = confusion_matrix[1]
    false_positive_rate = fp / max(fp + tn, 1)
    false_negative_rate = fn / max(fn + tp, 1)
    return {
        "false_positive_rate": false_positive_rate,
        "false_negative_rate": false_negative_rate,
    }


def _train_best_candidate(
    x_train: pd.DataFrame,
    x_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series,
    random_state: int,
    candidates: dict[str, Any] | None = None,
) -> tuple[str, Any, dict[str, Any]]:
    resolved_candidates = candidates or _candidate_models(random_state)
    scored: list[tuple[str, Any, dict[str, Any]]] = []
    for candidate_name, model in resolved_candidates.items():
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        scores = _positive_probability(model, x_test)
        metrics = evaluate_classifier(y_test, predictions, scores)
        scored.append((candidate_name, model, metrics))
    return max(
        scored,
        key=lambda item: (
            float(item[2].get("average_precision", 0.0)),
            float(item[2].get("recall", 0.0)),
            float(item[2].get("f1", 0.0)),
        ),
    )


def compute_group_metrics(
    frame: pd.DataFrame,
    predictions: Any,
    scores: Any,
    y_test: pd.Series,
) -> list[dict[str, Any]]:
    scored_frame = frame.copy()
    scored_frame["prediction"] = predictions
    scored_frame["score"] = scores
    scored_frame["actual"] = y_test.to_numpy()

    group_results: list[dict[str, Any]] = []
    for group_value, group in scored_frame.groupby(GROUP_COLUMN):
        y_group = group["actual"].astype(int)
        metrics = evaluate_classifier(y_group, group["prediction"], group["score"])
        group_results.append(
            {
                "group": str(group_value),
                "rows": len(group),
                "failure_rate": float(y_group.mean()),
                "metrics": {
                    key: value
                    for key, value in metrics.items()
                    if key != "confusion_matrix"
                },
                "confusion_matrix": metrics["confusion_matrix"],
                **_false_rates(metrics["confusion_matrix"]),
            }
        )
    return sorted(group_results, key=lambda item: item["group"])


def compute_permutation_importance(
    model: Any,
    x_test: pd.DataFrame,
    y_test: pd.Series,
    *,
    random_state: int,
    n_repeats: int = 8,
) -> list[dict[str, float | str]]:
    scoring = "average_precision" if y_test.nunique() > 1 else "f1"
    result = permutation_importance(
        model,
        x_test,
        y_test,
        n_repeats=n_repeats,
        random_state=random_state,
        scoring=scoring,
        n_jobs=1,
    )
    rows = [
        {
            "feature": feature,
            "importance_mean": float(mean),
            "importance_std": float(std),
        }
        for feature, mean, std in zip(
            FEATURE_COLUMNS,
            result.importances_mean,
            result.importances_std,
            strict=True,
        )
    ]
    return sorted(rows, key=lambda item: float(item["importance_mean"]), reverse=True)


def build_explainability_fairness_report(
    frame: pd.DataFrame,
    *,
    test_size: float = 0.20,
    random_state: int = 42,
    candidates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    missing_columns = [
        column for column in [*FEATURE_COLUMNS, TARGET_COLUMN, GROUP_COLUMN] if column not in frame
    ]
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {missing_columns}")

    x = frame[FEATURE_COLUMNS]
    y = frame[TARGET_COLUMN].astype(int)
    stratify = y if y.nunique() > 1 else None
    x_train, x_test, y_train, y_test, _, group_test = train_test_split(
        x,
        y,
        frame[[GROUP_COLUMN]],
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
    )

    best_candidate, model, overall_metrics = _train_best_candidate(
        x_train,
        x_test,
        y_train,
        y_test,
        random_state,
        candidates=candidates,
    )
    predictions = model.predict(x_test)
    scores = _positive_probability(model, x_test)
    group_frame = group_test.reset_index(drop=True)
    group_metrics = compute_group_metrics(group_frame, predictions, scores, y_test.reset_index(drop=True))
    feature_importance = compute_permutation_importance(
        model,
        x_test,
        y_test,
        random_state=random_state,
    )

    return {
        "status": "ok",
        "objective": "Explain model drivers and compare performance across AI4I product groups.",
        "best_candidate": best_candidate,
        "fairness_axis": GROUP_COLUMN,
        "overall_metrics": {
            key: value for key, value in overall_metrics.items() if key != "confusion_matrix"
        },
        "overall_confusion_matrix": overall_metrics["confusion_matrix"],
        "group_metrics": group_metrics,
        "top_features": feature_importance[:10],
        "feature_importance_method": "permutation_importance",
        "feature_importance_scoring": "average_precision",
        "test_size": test_size,
        "random_state": random_state,
    }


def write_reports(report: dict[str, Any], report_dir: Path = DEFAULT_REPORT_DIR) -> dict[str, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "explainability_fairness_latest.json"
    md_path = report_dir / "explainability_fairness_latest.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Explainability and Fairness Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Objective: {report['objective']}",
        f"- Model analyzed: `{report['best_candidate']}`",
        f"- Fairness axis: `{report['fairness_axis']}`",
        f"- Feature importance method: `{report['feature_importance_method']}`",
        "",
        "## Group Metrics",
        "",
        "| Product type | Rows | Failure rate | ROC AUC | PR AUC | F1 | Precision | Recall | FPR | FNR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for group in report["group_metrics"]:
        metrics = group["metrics"]
        lines.append(
            "| {group_name} | {rows} | {failure_rate:.4f} | {roc_auc:.4f} | {ap:.4f} | "
            "{f1:.4f} | {precision:.4f} | {recall:.4f} | {fpr:.4f} | {fnr:.4f} |".format(
                group_name=group["group"],
                rows=group["rows"],
                failure_rate=group["failure_rate"],
                roc_auc=float(metrics.get("roc_auc", 0.0)),
                ap=float(metrics.get("average_precision", 0.0)),
                f1=float(metrics.get("f1", 0.0)),
                precision=float(metrics.get("precision", 0.0)),
                recall=float(metrics.get("recall", 0.0)),
                fpr=float(group["false_positive_rate"]),
                fnr=float(group["false_negative_rate"]),
            )
        )
    lines.extend(
        [
            "",
            "## Top Model Drivers",
            "",
            "| Feature | Importance mean | Importance std |",
            "|---|---:|---:|",
        ]
    )
    for feature in report["top_features"]:
        lines.append(
            "| {feature} | {mean:.6f} | {std:.6f} |".format(
                feature=feature["feature"],
                mean=float(feature["importance_mean"]),
                std=float(feature["importance_std"]),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Fairness is evaluated across AI4I product quality groups because the dataset encodes "
            "different product variants as `L`, `M`, and `H`. The report highlights whether "
            "failure detection quality is materially different across these operational groups.",
            "",
            "Permutation importance is model-agnostic, so the same explainability method can be "
            "used for scikit-learn and PyTorch-backed candidates.",
            "",
        ]
    )
    return "\n".join(lines)


def run_explainability_fairness(
    input_path: Path = DEFAULT_INPUT_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:
    if not input_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {input_path}. Run ingestion first."
        )
    frame = normalize_feature_columns(pd.read_csv(input_path))
    report = build_explainability_fairness_report(
        frame,
        test_size=test_size,
        random_state=random_state,
    )
    paths = write_reports(report, report_dir)
    return {**report, "report_paths": {key: str(path) for key, path in paths.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AI4I explainability and fairness report."
    )
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    result = run_explainability_fairness(
        input_path=args.input_path,
        report_dir=args.report_dir,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    print(json.dumps(result["report_paths"], indent=2))


if __name__ == "__main__":
    main()
