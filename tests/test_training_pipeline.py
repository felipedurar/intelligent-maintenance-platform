import pandas as pd

from training.constants import FEATURE_COLUMNS
from training.metrics import evaluate_classifier
from training.train_model import _candidate_models, _positive_probability


def synthetic_training_frame() -> tuple[pd.DataFrame, pd.Series]:
    rows = []
    labels = []
    for index in range(24):
        failure = int(index >= 16)
        rows.append(
            {
                "air_temperature_k": 298.0 + failure,
                "process_temperature_k": 308.0 + failure,
                "temperature_delta_k": 10.0,
                "rotational_speed_rpm": 1500.0 - (failure * 250.0),
                "rotational_speed_rad_s": 157.08 - (failure * 25.0),
                "torque_nm": 35.0 + (failure * 30.0),
                "tool_wear_min": 80.0 + (failure * 140.0),
                "power_w": 5500.0 + (failure * 2500.0),
                "torque_speed_interaction": 52500.0 + (failure * 30000.0),
                "tool_wear_by_torque": 2800.0 + (failure * 11500.0),
                "temperature_delta_low_flag": 0,
                "power_low_flag": 0,
                "power_high_flag": failure,
                "overstrain_threshold": 11000.0,
                "overstrain_margin": -8000.0 + (failure * 12000.0),
                "type_h": 0,
                "type_l": 1,
                "type_m": 0,
            }
        )
        labels.append(failure)

    return pd.DataFrame(rows, columns=FEATURE_COLUMNS), pd.Series(labels)


def test_candidate_models_fit_and_emit_metrics() -> None:
    x, y = synthetic_training_frame()

    for model in _candidate_models(random_state=42).values():
        model.fit(x, y)
        predictions = model.predict(x)
        scores = _positive_probability(model, x)
        metrics = evaluate_classifier(y, predictions, scores)

        assert metrics["recall"] >= 0.75
        assert metrics["f1"] >= 0.75
        assert "confusion_matrix" in metrics
