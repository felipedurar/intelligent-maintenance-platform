import numpy as np

from model_serving.service import ModelServingService


class DummyModel:
    def predict_proba(self, features):
        assert list(features.columns)
        return np.array([[0.2, 0.8]])


def test_model_serving_uses_engineered_features_and_returns_risk_class() -> None:
    service = ModelServingService()
    service.__dict__["model"] = DummyModel()
    service.__dict__["model_version"] = "test-version"

    result = service.predict_failure(
        {
            "product_type": "L",
            "air_temperature_k": 298.1,
            "process_temperature_k": 308.6,
            "rotational_speed_rpm": 1551,
            "torque_nm": 42.8,
            "tool_wear_min": 108,
        },
        request_id="unit-test",
    )

    assert result["status"] == "ok"
    assert result["failure_probability"] == 0.8
    assert result["risk_class"] == "high"
    assert result["model_version"] == "test-version"
