from fastapi.testclient import TestClient

from model_serving.service import get_model_serving_service
from platform_api.main import create_app
from platform_api.routes import models


class FakePredictionService:
    def predict_failure(self, observation, request_id=None):
        return {
            "status": "ok",
            "failure_probability": 0.42,
            "risk_class": "medium",
            "model_version": "unit-test",
            "message": "fake prediction",
            "metadata": {"request_id": request_id, "received_observation": observation},
        }


class FakeMlflowClient:
    def __init__(self, tracking_uri=None):
        self.tracking_uri = tracking_uri

    def get_model_version_by_alias(self, model_name, alias):
        return type("ModelVersion", (), {"version": "7"})()


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predictions_endpoint_uses_serving_dependency_override() -> None:
    app = create_app()
    app.dependency_overrides[get_model_serving_service] = lambda: FakePredictionService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/predictions",
        json={
            "request_id": "api-unit-test",
            "observation": {
                "product_type": "L",
                "air_temperature_k": 298.1,
                "process_temperature_k": 308.6,
                "rotational_speed_rpm": 1551,
                "torque_nm": 42.8,
                "tool_wear_min": 108,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["failure_probability"] == 0.42
    assert response.json()["model_version"] == "unit-test"


def test_predictions_endpoint_rejects_invalid_product_type() -> None:
    app = create_app()
    app.dependency_overrides[get_model_serving_service] = lambda: FakePredictionService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/predictions",
        json={
            "request_id": "api-invalid-test",
            "observation": {
                "product_type": "X",
                "air_temperature_k": 298.1,
                "process_temperature_k": 308.6,
                "rotational_speed_rpm": 1551,
                "torque_nm": 42.8,
                "tool_wear_min": 108,
            },
        },
    )

    assert response.status_code == 422


def test_active_model_endpoint_reads_mlflow_alias(monkeypatch) -> None:
    monkeypatch.setattr(models, "MlflowClient", FakeMlflowClient)
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/models/ai4i-machine-failure-classifier/active")

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["model_version"] == "7"
