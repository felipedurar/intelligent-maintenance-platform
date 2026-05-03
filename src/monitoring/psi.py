from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd


PSI_WARNING_THRESHOLD = 0.10
PSI_DRIFT_THRESHOLD = 0.20


@dataclass(frozen=True)
class PsiFeatureResult:
    feature: str
    psi: float
    status: str


def classify_psi(value: float) -> str:
    if value >= PSI_DRIFT_THRESHOLD:
        return "drift"
    if value >= PSI_WARNING_THRESHOLD:
        return "warning"
    return "stable"


def calculate_psi(
    reference: pd.Series,
    current: pd.Series,
    buckets: int = 10,
    epsilon: float = 1e-6,
) -> float:
    reference_values = pd.to_numeric(reference, errors="coerce").dropna()
    current_values = pd.to_numeric(current, errors="coerce").dropna()
    if reference_values.empty or current_values.empty:
        return 0.0

    quantiles = reference_values.quantile([index / buckets for index in range(buckets + 1)])
    edges = sorted(set(float(value) for value in quantiles.tolist() if math.isfinite(float(value))))
    if len(edges) < 2:
        minimum = float(reference_values.min())
        maximum = float(reference_values.max())
        if minimum == maximum:
            return 0.0
        edges = [minimum, maximum]

    edges[0] = -math.inf
    edges[-1] = math.inf

    expected = pd.cut(reference_values, bins=edges, include_lowest=True).value_counts(normalize=True)
    actual = pd.cut(current_values, bins=edges, include_lowest=True).value_counts(normalize=True)
    expected, actual = expected.align(actual, fill_value=0.0)

    expected = expected.clip(lower=epsilon)
    actual = actual.clip(lower=epsilon)
    return float(((actual - expected) * (actual / expected).apply(math.log)).sum())


def calculate_feature_psi(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    features: list[str],
    buckets: int = 10,
) -> list[PsiFeatureResult]:
    results: list[PsiFeatureResult] = []
    for feature in features:
        if feature not in reference_df.columns or feature not in current_df.columns:
            continue
        value = calculate_psi(reference_df[feature], current_df[feature], buckets=buckets)
        results.append(PsiFeatureResult(feature=feature, psi=value, status=classify_psi(value)))
    return results
