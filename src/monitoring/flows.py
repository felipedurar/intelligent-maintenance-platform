from __future__ import annotations

import argparse
import os
from typing import Any

from prefect import flow, get_run_logger, task

from monitoring.drift import (
    DEFAULT_CURRENT_PATH,
    DEFAULT_REFERENCE_PATH,
    DEFAULT_REPORT_DIR,
    generate_drift_report,
)


def default_mlflow_tracking_uri() -> str:
    return os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


@task
def generate_drift_report_task(
    reference_path: str,
    current_path: str,
    report_dir: str,
    buckets: int,
    mlflow_tracking_uri: str,
) -> dict[str, Any]:
    return generate_drift_report(
        reference_path=reference_path,
        current_path=current_path,
        report_dir=report_dir,
        buckets=buckets,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )


@flow(name="detect-ai4i-drift")
def detect_ai4i_drift(
    reference_path: str = DEFAULT_REFERENCE_PATH,
    current_path: str = DEFAULT_CURRENT_PATH,
    report_dir: str = DEFAULT_REPORT_DIR,
    buckets: int = 10,
    mlflow_tracking_uri: str | None = None,
) -> dict[str, Any]:
    logger = get_run_logger()
    resolved_mlflow_uri = mlflow_tracking_uri or default_mlflow_tracking_uri()
    logger.info("Generating AI4I drift report from %s against %s", current_path, reference_path)
    report = generate_drift_report_task(
        reference_path,
        current_path,
        report_dir,
        buckets,
        resolved_mlflow_uri,
    )
    logger.info("AI4I drift status: %s", report["status"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI4I drift detection.")
    parser.add_argument("--reference-path", default=DEFAULT_REFERENCE_PATH)
    parser.add_argument("--current-path", default=DEFAULT_CURRENT_PATH)
    parser.add_argument("--report-dir", default=DEFAULT_REPORT_DIR)
    parser.add_argument("--buckets", type=int, default=10)
    parser.add_argument("--mlflow-tracking-uri", default=None)
    args = parser.parse_args()

    detect_ai4i_drift(
        reference_path=args.reference_path,
        current_path=args.current_path,
        report_dir=args.report_dir,
        buckets=args.buckets,
        mlflow_tracking_uri=args.mlflow_tracking_uri,
    )


if __name__ == "__main__":
    main()
