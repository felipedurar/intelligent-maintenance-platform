from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mlflow
import pandas as pd

from monitoring.psi import PSI_DRIFT_THRESHOLD, PSI_WARNING_THRESHOLD, calculate_feature_psi
from training.constants import FEATURE_COLUMNS


DEFAULT_REFERENCE_PATH = "data/reference/ai4i_reference.csv"
DEFAULT_CURRENT_PATH = "data/processed/ai4i_features_latest.csv"
DEFAULT_REPORT_DIR = "reports/drift"


def _normalise_feature_columns(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.rename(columns={"type_H": "type_h", "type_L": "type_l", "type_M": "type_m"})


def _overall_status(feature_results: list[dict[str, Any]]) -> str:
    if any(result["status"] == "drift" for result in feature_results):
        return "drift_detected"
    if any(result["status"] == "warning" for result in feature_results):
        return "warning"
    return "stable"


def _write_html_report(report: dict[str, Any], path: Path) -> None:
    rows = "\n".join(
        "<tr>"
        f"<td>{item['feature']}</td>"
        f"<td>{item['psi']:.6f}</td>"
        f"<td>{item['status']}</td>"
        "</tr>"
        for item in report["features"]
    )
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>AI4I Drift Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2937; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>AI4I Drift Report</h1>
  <p>Status: <strong>{report['status']}</strong></p>
  <p>Generated at: {report['generated_at']}</p>
  <p>Max feature PSI: {report['summary']['max_feature_psi']:.6f}</p>
  <table>
    <thead><tr><th>Feature</th><th>PSI</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")


def generate_drift_report(
    reference_path: str = DEFAULT_REFERENCE_PATH,
    current_path: str = DEFAULT_CURRENT_PATH,
    report_dir: str = DEFAULT_REPORT_DIR,
    buckets: int = 10,
    mlflow_tracking_uri: str | None = None,
    log_to_mlflow: bool = True,
) -> dict[str, Any]:
    reference_file = Path(reference_path)
    current_file = Path(current_path)
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not current_file.exists():
        raise FileNotFoundError(f"Current dataset not found: {current_file}")

    if not reference_file.exists():
        reference_file.parent.mkdir(parents=True, exist_ok=True)
        reference_file.write_bytes(current_file.read_bytes())
        baseline_initialized = True
    else:
        baseline_initialized = False

    reference_df = _normalise_feature_columns(pd.read_csv(reference_file))
    current_df = _normalise_feature_columns(pd.read_csv(current_file))
    feature_results = [
        {
            "feature": result.feature,
            "psi": result.psi,
            "status": result.status,
        }
        for result in calculate_feature_psi(reference_df, current_df, FEATURE_COLUMNS, buckets=buckets)
    ]

    status = "baseline_initialized" if baseline_initialized else _overall_status(feature_results)
    drifted_features = [item["feature"] for item in feature_results if item["status"] == "drift"]
    warning_features = [item["feature"] for item in feature_results if item["status"] == "warning"]
    max_feature_psi = max((float(item["psi"]) for item in feature_results), default=0.0)
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    report_id = generated_at.replace(":", "").replace("+", "Z")
    json_path = output_dir / f"psi_{report_id}.json"
    html_path = output_dir / f"psi_{report_id}.html"

    report: dict[str, Any] = {
        "status": status,
        "generated_at": generated_at,
        "reference_path": str(reference_file),
        "current_path": str(current_file),
        "json_report_path": str(json_path),
        "html_report_path": str(html_path),
        "thresholds": {
            "warning": PSI_WARNING_THRESHOLD,
            "drift": PSI_DRIFT_THRESHOLD,
        },
        "summary": {
            "feature_count": len(feature_results),
            "max_feature_psi": max_feature_psi,
            "drifted_features": drifted_features,
            "warning_features": warning_features,
            "reference_rows": len(reference_df),
            "current_rows": len(current_df),
        },
        "features": feature_results,
    }
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_html_report(report, html_path)

    if log_to_mlflow:
        try:
            if mlflow_tracking_uri:
                mlflow.set_tracking_uri(mlflow_tracking_uri)
            mlflow.set_experiment("ai4i-monitoring")
            with mlflow.start_run(run_name="ai4i-drift-report"):
                mlflow.log_metric("max_feature_psi", report["summary"]["max_feature_psi"])
                mlflow.log_metric("drifted_feature_count", len(drifted_features))
                mlflow.log_metric("warning_feature_count", len(warning_features))
                mlflow.log_artifact(str(json_path), artifact_path="drift")
                mlflow.log_artifact(str(html_path), artifact_path="drift")
        except Exception as exc:
            report["mlflow_warning"] = str(exc)
            json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def latest_drift_report(report_dir: str = DEFAULT_REPORT_DIR) -> dict[str, Any] | None:
    reports = sorted(Path(report_dir).glob("psi_*.json"), reverse=True)
    if not reports:
        return None
    return json.loads(reports[0].read_text(encoding="utf-8"))
