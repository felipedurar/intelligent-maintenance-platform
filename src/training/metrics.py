from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_classifier(y_true: pd.Series, y_pred: Any, y_score: Any) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }

    if y_true.nunique() > 1:
        metrics["roc_auc"] = roc_auc_score(y_true, y_score)
        metrics["average_precision"] = average_precision_score(y_true, y_score)
    else:
        metrics["roc_auc"] = 0.0
        metrics["average_precision"] = 0.0

    return metrics
