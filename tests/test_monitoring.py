import json

import pandas as pd
from fastapi.testclient import TestClient

from monitoring.drift import generate_drift_report, latest_drift_report
from monitoring.psi import calculate_feature_psi, classify_psi
from platform_api.config import get_settings
from platform_api.main import create_app


def test_psi_detects_shifted_feature_distribution() -> None:
    reference = pd.DataFrame({"torque_nm": [35, 36, 37, 38, 39, 40, 41, 42]})
    current = pd.DataFrame({"torque_nm": [70, 71, 72, 73, 74, 75, 76, 77]})

    results = calculate_feature_psi(reference, current, ["torque_nm"], buckets=4)

    assert results[0].feature == "torque_nm"
    assert results[0].psi > 0.2
    assert results[0].status == "drift"


def test_classify_psi_thresholds() -> None:
    assert classify_psi(0.01) == "stable"
    assert classify_psi(0.12) == "warning"
    assert classify_psi(0.25) == "drift"


def test_generate_drift_report_writes_json_and_html(tmp_path) -> None:
    reference = tmp_path / "reference.csv"
    current = tmp_path / "current.csv"
    reports = tmp_path / "reports"
    frame = pd.DataFrame(
        {
            "air_temperature_k": [300, 301, 302],
            "process_temperature_k": [310, 311, 312],
            "temperature_delta_k": [10, 10, 10],
            "rotational_speed_rpm": [1500, 1510, 1520],
            "rotational_speed_rad_s": [157, 158, 159],
            "torque_nm": [35, 36, 80],
            "tool_wear_min": [20, 30, 40],
            "power_w": [5500, 5700, 12000],
            "torque_speed_interaction": [52500, 54360, 121600],
            "tool_wear_by_torque": [700, 1080, 3200],
            "temperature_delta_low_flag": [0, 0, 0],
            "power_low_flag": [0, 0, 0],
            "power_high_flag": [0, 0, 1],
            "overstrain_threshold": [11000, 11000, 11000],
            "overstrain_margin": [-10300, -9920, -7800],
            "type_h": [0, 0, 0],
            "type_l": [1, 1, 1],
            "type_m": [0, 0, 0],
        }
    )
    frame.to_csv(reference, index=False)
    shifted = frame.copy()
    shifted["torque_nm"] = [70, 75, 80]
    shifted.to_csv(current, index=False)

    report = generate_drift_report(
        reference_path=str(reference),
        current_path=str(current),
        report_dir=str(reports),
        log_to_mlflow=False,
    )

    assert report["status"] in {"warning", "drift_detected", "stable"}
    assert report["summary"]["feature_count"] == 18
    assert reports.exists()
    assert latest_drift_report(str(reports))["json_report_path"] == report["json_report_path"]
    assert json.loads((reports / report["json_report_path"].split("/")[-1]).read_text())


def test_monitoring_status_returns_latest_drift_report(tmp_path) -> None:
    report_dir = tmp_path / "drift"
    report_dir.mkdir()
    report = {
        "status": "warning",
        "generated_at": "2026-05-03T00:00:00+00:00",
        "json_report_path": str(report_dir / "psi_latest.json"),
        "summary": {
            "max_feature_psi": 0.12,
            "drifted_features": [],
            "warning_features": ["torque_nm"],
        },
    }
    (report_dir / "psi_latest.json").write_text(json.dumps(report), encoding="utf-8")

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: type(
        "Settings",
        (),
        {"drift_report_dir": str(report_dir), "app_name": "test", "app_version": "0", "app_env": "test"},
    )()
    client = TestClient(app)

    response = client.get("/api/v1/monitoring/status")

    assert response.status_code == 200
    assert response.json()["status"] == "warning"
    assert response.json()["drift"]["warning_features"] == ["torque_nm"]


def test_metrics_endpoint_is_available() -> None:
    client = TestClient(create_app())

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "prediction_requests_total" in response.text
