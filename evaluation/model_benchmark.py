from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.model_selection import train_test_split

from training.constants import FEATURE_COLUMNS, TARGET_COLUMN
from training.metrics import evaluate_classifier
from training.train_model import _candidate_models, _positive_probability

DEFAULT_INPUT_PATH = Path("data/processed/ai4i_features_latest.csv")
DEFAULT_REPORT_DIR = Path("evaluation/reports")


def normalize_feature_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize CSV-exported feature names to the training contract."""
    return frame.rename(columns={"type_H": "type_h", "type_L": "type_l", "type_M": "type_m"})


def load_feature_frame(input_path: Path = DEFAULT_INPUT_PATH) -> pd.DataFrame:
    """Load the processed feature dataset used by offline evaluation scripts."""
    if not input_path.exists():
        raise FileNotFoundError(
            f"Processed dataset not found at {input_path}. Run ingestion first."
        )
    frame = normalize_feature_columns(pd.read_csv(input_path))
    missing_columns = [column for column in [*FEATURE_COLUMNS, TARGET_COLUMN] if column not in frame]
    if missing_columns:
        raise ValueError(f"Processed dataset is missing required columns: {missing_columns}")
    return frame


def benchmark_candidates(
    frame: pd.DataFrame,
    *,
    test_size: float = 0.20,
    random_state: int = 42,
    candidates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train and compare model candidates with quality and latency metrics."""
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

    resolved_candidates = candidates or _benchmark_candidate_models(random_state)
    results: list[dict[str, Any]] = []
    for candidate_name, model in resolved_candidates.items():
        fit_started_at = time.perf_counter()
        model.fit(x_train, y_train)
        fit_seconds = time.perf_counter() - fit_started_at

        predict_started_at = time.perf_counter()
        predictions = model.predict(x_test)
        scores = _positive_probability(model, x_test)
        predict_seconds = time.perf_counter() - predict_started_at

        metrics = evaluate_classifier(y_test, predictions, scores)
        results.append(
            {
                "candidate_name": candidate_name,
                "framework": "pytorch" if "pytorch" in candidate_name else "scikit-learn",
                "metrics": {
                    key: value
                    for key, value in metrics.items()
                    if key != "confusion_matrix"
                },
                "confusion_matrix": metrics["confusion_matrix"],
                "fit_seconds": fit_seconds,
                "predict_seconds": predict_seconds,
                "latency_ms_per_row": predict_seconds / max(len(x_test), 1) * 1000.0,
                "train_rows": len(x_train),
                "test_rows": len(x_test),
            }
        )

    ranked = sorted(
        results,
        key=lambda item: (
            float(item["metrics"].get("average_precision", 0.0)),
            float(item["metrics"].get("recall", 0.0)),
            float(item["metrics"].get("f1", 0.0)),
        ),
        reverse=True,
    )
    return {
        "status": "ok",
        "objective": "Compare at least three predictive-maintenance model configurations.",
        "ranking_metric": "average_precision, then recall, then f1",
        "feature_count": len(FEATURE_COLUMNS),
        "test_size": test_size,
        "random_state": random_state,
        "best_candidate": ranked[0]["candidate_name"] if ranked else None,
        "results": ranked,
    }


def _benchmark_candidate_models(random_state: int) -> dict[str, Any]:
    """Return benchmark candidates, guaranteeing at least three configurations."""
    candidates = dict(_candidate_models(random_state))
    candidates["challenger_extra_trees"] = ExtraTreesClassifier(
        class_weight="balanced",
        n_estimators=300,
        min_samples_leaf=2,
        random_state=random_state,
        n_jobs=-1,
    )
    return candidates


def write_reports(report: dict[str, Any], report_dir: Path = DEFAULT_REPORT_DIR) -> dict[str, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / "model_benchmark_latest.json"
    md_path = report_dir / "model_benchmark_latest.md"

    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Model Benchmark Report",
        "",
        f"- Status: `{report['status']}`",
        f"- Objective: {report['objective']}",
        f"- Ranking metric: `{report['ranking_metric']}`",
        f"- Best candidate: `{report['best_candidate']}`",
        f"- Feature count: `{report['feature_count']}`",
        "",
        "## Results",
        "",
        "| Candidate | Framework | ROC AUC | PR AUC | F1 | Precision | Recall | Latency ms/row |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in report["results"]:
        metrics = result["metrics"]
        lines.append(
            "| {candidate} | {framework} | {roc_auc:.4f} | {average_precision:.4f} | "
            "{f1:.4f} | {precision:.4f} | {recall:.4f} | {latency:.4f} |".format(
                candidate=result["candidate_name"],
                framework=result["framework"],
                roc_auc=float(metrics.get("roc_auc", 0.0)),
                average_precision=float(metrics.get("average_precision", 0.0)),
                f1=float(metrics.get("f1", 0.0)),
                precision=float(metrics.get("precision", 0.0)),
                recall=float(metrics.get("recall", 0.0)),
                latency=float(result["latency_ms_per_row"]),
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The benchmark prioritizes PR AUC because the failure class is rare in AI4I. "
            "Recall is used as the second ordering criterion because missing a real failure "
            "is usually more expensive than inspecting a false alarm in predictive maintenance.",
            "",
        ]
    )
    return "\n".join(lines)


def run_benchmark(
    input_path: Path = DEFAULT_INPUT_PATH,
    report_dir: Path = DEFAULT_REPORT_DIR,
    test_size: float = 0.20,
    random_state: int = 42,
) -> dict[str, Any]:
    frame = load_feature_frame(input_path)
    report = benchmark_candidates(frame, test_size=test_size, random_state=random_state)
    paths = write_reports(report, report_dir)
    return {**report, "report_paths": {key: str(path) for key, path in paths.items()}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AI4I model benchmark report.")
    parser.add_argument("--input-path", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    parser.add_argument("--test-size", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    result = run_benchmark(
        input_path=args.input_path,
        report_dir=args.report_dir,
        test_size=args.test_size,
        random_state=args.random_state,
    )
    print(json.dumps(result["report_paths"], indent=2))


if __name__ == "__main__":
    main()
