from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from mlflow.exceptions import MlflowException

from training.constants import CANDIDATE_ALIAS, CHAMPION_ALIAS, PREVIOUS_CHAMPION_ALIAS
from training.promote_model import promote_model_version


@dataclass
class FakeModelVersion:
    version: str
    tags: dict[str, str] = field(default_factory=dict)


class FakeMlflowClient:
    def __init__(self) -> None:
        self.versions = {
            "2": FakeModelVersion(
                version="2",
                tags={
                    "approval_status": "pending",
                    "validation_status": "passed",
                    "candidate_name": "challenger_random_forest",
                    "best_run_id": "run-123",
                },
            ),
            "1": FakeModelVersion(version="1", tags={"approval_status": "approved"}),
        }
        self.aliases = {CANDIDATE_ALIAS: "2", CHAMPION_ALIAS: "1"}
        self.updated_tags: dict[tuple[str, str], str] = {}

    def get_model_version_by_alias(self, name: str, alias: str) -> FakeModelVersion:
        if alias not in self.aliases:
            raise MlflowException(f"No alias {alias}")
        return self.versions[self.aliases[alias]]

    def get_model_version(self, name: str, version: str) -> FakeModelVersion:
        return self.versions[str(version)]

    def set_model_version_tag(self, name: str, version: str, key: str, value: str) -> None:
        self.versions[str(version)].tags[key] = value
        self.updated_tags[(key, str(version))] = value

    def set_registered_model_alias(self, name: str, alias: str, version: str) -> None:
        self.aliases[alias] = str(version)


def _write_ok_report(path: Path) -> None:
    path.write_text(json.dumps({"status": "ok", "best_candidate": "challenger"}), encoding="utf-8")


def test_promote_model_requires_pending_candidate(tmp_path):
    benchmark_path = tmp_path / "benchmark.json"
    fairness_path = tmp_path / "fairness.json"
    _write_ok_report(benchmark_path)
    _write_ok_report(fairness_path)
    client = FakeMlflowClient()
    client.versions["2"].tags["approval_status"] = "approved"

    with pytest.raises(ValueError, match="approval_status=pending"):
        promote_model_version(
            version="2",
            approved_by="felipe",
            reason="reviewed",
            required_reports=[benchmark_path, fairness_path],
            client=client,  # type: ignore[arg-type]
        )


def test_promote_model_sets_champion_and_preserves_previous(tmp_path):
    benchmark_path = tmp_path / "benchmark.json"
    fairness_path = tmp_path / "fairness.json"
    _write_ok_report(benchmark_path)
    _write_ok_report(fairness_path)
    client = FakeMlflowClient()

    result = promote_model_version(
        approved_by="felipe",
        reason="Benchmark and fairness reports reviewed.",
        required_reports=[benchmark_path, fairness_path],
        client=client,  # type: ignore[arg-type]
    )

    assert result["model_version"] == "2"
    assert result["approval_status"] == "approved"
    assert client.aliases[CHAMPION_ALIAS] == "2"
    assert client.aliases[PREVIOUS_CHAMPION_ALIAS] == "1"
    assert client.versions["2"].tags["approved_by"] == "felipe"
    assert client.versions["2"].tags["promotion_reason"] == "Benchmark and fairness reports reviewed."
