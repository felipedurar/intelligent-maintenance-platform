from __future__ import annotations

from typing import Any

import mlflow.pyfunc
import pandas as pd
from mlflow.pyfunc import PythonModel


class FailureProbabilityPyFunc(PythonModel):
    """MLflow pyfunc wrapper that returns failure probabilities for any candidate."""

    def __init__(self, model: Any) -> None:
        self.model = model

    def predict(
        self,
        context: Any,
        model_input: pd.DataFrame,
        params: dict[str, Any] | None = None,
    ) -> pd.DataFrame:
        if hasattr(self.model, "predict_proba"):
            probabilities = self.model.predict_proba(model_input)[:, 1]
        else:
            probabilities = self.model.predict(model_input)
        return pd.DataFrame({"failure_probability": probabilities})


def log_probability_model(model: Any, artifact_path: str = "model") -> None:
    mlflow.pyfunc.log_model(
        artifact_path=artifact_path,
        python_model=FailureProbabilityPyFunc(model),
    )
