from __future__ import annotations

import pandas as pd
import pytest

from training.constants import FEATURE_COLUMNS
from training.model_wrappers import FailureProbabilityPyFunc
from training.train_model import _candidate_models

pytest.importorskip("torch")
from training.pytorch_mlp import TorchMLPClassifier  # noqa: E402


def easy_training_frame() -> tuple[pd.DataFrame, pd.Series]:
    rows = []
    labels = []
    for index in range(40):
        failure = int(index >= 24)
        rows.append(
            {
                "air_temperature_k": 298.0 + failure,
                "process_temperature_k": 308.0 + failure,
                "temperature_delta_k": 10.0 - failure,
                "rotational_speed_rpm": 1500.0 - (failure * 300.0),
                "rotational_speed_rad_s": 157.08 - (failure * 30.0),
                "torque_nm": 35.0 + (failure * 35.0),
                "tool_wear_min": 80.0 + (failure * 160.0),
                "power_w": 5500.0 + (failure * 3000.0),
                "torque_speed_interaction": 52500.0 + (failure * 35000.0),
                "tool_wear_by_torque": 2800.0 + (failure * 14000.0),
                "temperature_delta_low_flag": failure,
                "power_low_flag": 0,
                "power_high_flag": failure,
                "overstrain_threshold": 11000.0,
                "overstrain_margin": -8000.0 + (failure * 14000.0),
                "type_h": 0,
                "type_l": 1,
                "type_m": 0,
            }
        )
        labels.append(failure)
    return pd.DataFrame(rows, columns=FEATURE_COLUMNS), pd.Series(labels)


def test_candidate_models_include_pytorch_mlp() -> None:
    candidates = _candidate_models(random_state=42)

    assert "deep_challenger_pytorch_mlp" in candidates
    assert isinstance(candidates["deep_challenger_pytorch_mlp"], TorchMLPClassifier)


def test_torch_mlp_classifier_fits_and_predicts_probabilities() -> None:
    x, y = easy_training_frame()
    model = TorchMLPClassifier(
        hidden_dims=(8,),
        dropout=0.0,
        learning_rate=0.01,
        epochs=40,
        patience=6,
        random_state=42,
    )

    model.fit(x, y)
    probabilities = model.predict_proba(x)
    predictions = model.predict(x)

    assert probabilities.shape == (len(x), 2)
    assert probabilities[:, 1].min() >= 0.0
    assert probabilities[:, 1].max() <= 1.0
    assert predictions.sum() > 0


def test_pyfunc_wrapper_returns_failure_probability_column() -> None:
    x, y = easy_training_frame()
    model = TorchMLPClassifier(
        hidden_dims=(8,),
        dropout=0.0,
        learning_rate=0.01,
        epochs=10,
        random_state=42,
    ).fit(x, y)
    wrapper = FailureProbabilityPyFunc(model)

    result = wrapper.predict(context=None, model_input=x.head(2))  # type: ignore[arg-type]

    assert list(result.columns) == ["failure_probability"]
    assert len(result) == 2
