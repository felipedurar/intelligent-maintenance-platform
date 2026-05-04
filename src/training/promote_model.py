from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mlflow
from mlflow.exceptions import MlflowException
from mlflow.tracking import MlflowClient

from training.constants import (
    CANDIDATE_ALIAS,
    CHAMPION_ALIAS,
    MODEL_NAME,
    PREVIOUS_CHAMPION_ALIAS,
)
from training.train_model import default_mlflow_tracking_uri

DEFAULT_REQUIRED_REPORTS = [
    Path("evaluation/reports/model_benchmark_latest.json"),
    Path("evaluation/reports/explainability_fairness_latest.json"),
]

REQUIRED_MODEL_TAGS = {
    "approval_status": "pending",
    "validation_status": "passed",
    "candidate_name": None,
    "best_run_id": None,
}


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _load_report(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Required governance report not found: {path}. "
            "Run the benchmark and explainability/fairness checks before promotion."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def validate_required_reports(required_reports: list[Path]) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for report_path in required_reports:
        report = _load_report(report_path)
        if report.get("status") != "ok":
            raise ValueError(f"Required report is not OK: {report_path}")
        reports[report_path.name] = {
            "status": report.get("status"),
            "best_candidate": report.get("best_candidate"),
        }
    return reports


def validate_candidate_tags(tags: dict[str, str]) -> None:
    missing = [key for key in REQUIRED_MODEL_TAGS if not tags.get(key)]
    if missing:
        raise ValueError(f"Candidate model version is missing required tags: {missing}")

    expected_status = REQUIRED_MODEL_TAGS["approval_status"]
    if tags.get("approval_status") != expected_status:
        raise ValueError(
            "Candidate model version must have approval_status=pending before promotion. "
            f"Found approval_status={tags.get('approval_status')!r}."
        )
    if tags.get("validation_status") != "passed":
        raise ValueError(
            "Candidate model version must have validation_status=passed before promotion. "
            f"Found validation_status={tags.get('validation_status')!r}."
        )


def promote_model_version(
    *,
    model_name: str = MODEL_NAME,
    version: str | None = None,
    approved_by: str,
    reason: str,
    mlflow_tracking_uri: str | None = None,
    required_reports: list[Path] | None = None,
    client: MlflowClient | None = None,
) -> dict[str, Any]:
    """Promote a pending candidate model version to the champion alias."""
    if not approved_by.strip():
        raise ValueError("--approved-by is required for model promotion.")
    if not reason.strip():
        raise ValueError("--reason is required for model promotion.")

    if mlflow_tracking_uri:
        mlflow.set_tracking_uri(mlflow_tracking_uri)
    else:
        mlflow.set_tracking_uri(default_mlflow_tracking_uri())
    resolved_client = client or MlflowClient()
    resolved_reports = required_reports if required_reports is not None else DEFAULT_REQUIRED_REPORTS
    report_summary = validate_required_reports(resolved_reports)

    if version is None:
        candidate = resolved_client.get_model_version_by_alias(model_name, CANDIDATE_ALIAS)
        resolved_version = str(candidate.version)
    else:
        candidate = resolved_client.get_model_version(model_name, version)
        resolved_version = str(version)

    validate_candidate_tags(dict(candidate.tags))

    previous_champion_version: str | None = None
    try:
        previous_champion = resolved_client.get_model_version_by_alias(model_name, CHAMPION_ALIAS)
        previous_champion_version = str(previous_champion.version)
        resolved_client.set_registered_model_alias(
            model_name,
            PREVIOUS_CHAMPION_ALIAS,
            previous_champion_version,
        )
    except MlflowException:
        previous_champion_version = None

    approved_at = _utc_now()
    promotion_tags = {
        "approval_status": "approved",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "promotion_reason": reason,
        "promotion_required": "false",
        "promoted_from_alias": CANDIDATE_ALIAS,
        "previous_champion_version": previous_champion_version or "",
    }
    for key, value in promotion_tags.items():
        resolved_client.set_model_version_tag(model_name, resolved_version, key, value)

    resolved_client.set_registered_model_alias(model_name, CHAMPION_ALIAS, resolved_version)

    return {
        "model_name": model_name,
        "model_version": resolved_version,
        "champion_alias": CHAMPION_ALIAS,
        "previous_champion_alias": PREVIOUS_CHAMPION_ALIAS,
        "previous_champion_version": previous_champion_version,
        "approval_status": "approved",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "promotion_reason": reason,
        "report_summary": report_summary,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Approve and promote a pending MLflow candidate model to champion."
    )
    parser.add_argument("--model-name", default=MODEL_NAME)
    parser.add_argument("--version", default=None)
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--mlflow-tracking-uri", default=os.getenv("MLFLOW_TRACKING_URI"))
    args = parser.parse_args()

    result = promote_model_version(
        model_name=args.model_name,
        version=args.version,
        approved_by=args.approved_by,
        reason=args.reason,
        mlflow_tracking_uri=args.mlflow_tracking_uri,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
