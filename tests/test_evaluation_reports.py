from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from evaluation.explainability_fairness import (
    build_explainability_fairness_report,
    write_reports as write_explainability_reports,
)
from evaluation.model_benchmark import benchmark_candidates, write_reports as write_benchmark_reports
from training.constants import FEATURE_COLUMNS, TARGET_COLUMN


def _sample_feature_frame(rows: int = 80) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    product_types = np.resize(np.array(["L", "M", "H"]), rows)
    torque = rng.normal(42, 8, rows).clip(15, 80)
    wear = rng.integers(0, 240, rows)
    speed = rng.normal(1500, 120, rows).clip(1000, 2200)
    air = rng.normal(300, 2, rows)
    process = air + rng.normal(10, 1, rows)
    rad_s = speed * 2.0 * np.pi / 60.0
    power = torque * rad_s
    tool_wear_by_torque = wear * torque
    overstrain_threshold = np.select(
        [product_types == "L", product_types == "M", product_types == "H"],
        [11000.0, 12000.0, 13000.0],
    )
    overstrain_margin = tool_wear_by_torque - overstrain_threshold
    target = (
        (power < 3500)
        | (power > 9000)
        | ((process - air < 8.6) & (speed < 1380))
        | (overstrain_margin > 0)
    ).astype(int)
    target[:12] = [0, 1] * 6

    frame = pd.DataFrame(
        {
            "product_type": product_types,
            "air_temperature_k": air,
            "process_temperature_k": process,
            "temperature_delta_k": process - air,
            "rotational_speed_rpm": speed,
            "rotational_speed_rad_s": rad_s,
            "torque_nm": torque,
            "tool_wear_min": wear,
            "power_w": power,
            "torque_speed_interaction": torque * speed,
            "tool_wear_by_torque": tool_wear_by_torque,
            "temperature_delta_low_flag": ((process - air < 8.6) & (speed < 1380)).astype(int),
            "power_low_flag": (power < 3500).astype(int),
            "power_high_flag": (power > 9000).astype(int),
            "overstrain_threshold": overstrain_threshold,
            "overstrain_margin": overstrain_margin,
            "type_h": (product_types == "H").astype(int),
            "type_l": (product_types == "L").astype(int),
            "type_m": (product_types == "M").astype(int),
            TARGET_COLUMN: target,
        }
    )
    return frame[[*FEATURE_COLUMNS, "product_type", TARGET_COLUMN]]


def _lightweight_candidates() -> dict[str, object]:
    return {
        "baseline_logistic_regression": Pipeline(
            steps=[
                ("scaler", StandardScaler()),
                ("classifier", LogisticRegression(class_weight="balanced", max_iter=500)),
            ]
        ),
        "challenger_random_forest": RandomForestClassifier(
            class_weight="balanced",
            n_estimators=20,
            min_samples_leaf=1,
            random_state=42,
        ),
    }


def test_model_benchmark_report_generation(tmp_path):
    report = benchmark_candidates(
        _sample_feature_frame(),
        random_state=42,
        candidates=_lightweight_candidates(),
    )
    paths = write_benchmark_reports(report, tmp_path)

    assert report["status"] == "ok"
    assert report["best_candidate"] in {
        "baseline_logistic_regression",
        "challenger_random_forest",
    }
    assert len(report["results"]) == 2
    assert paths["json"].exists()
    assert "Model Benchmark Report" in paths["markdown"].read_text(encoding="utf-8")


def test_explainability_fairness_report_generation(tmp_path):
    report = build_explainability_fairness_report(
        _sample_feature_frame(),
        random_state=42,
        candidates=_lightweight_candidates(),
    )
    paths = write_explainability_reports(report, tmp_path)

    assert report["status"] == "ok"
    assert report["fairness_axis"] == "product_type"
    assert {group["group"] for group in report["group_metrics"]} == {"H", "L", "M"}
    assert report["top_features"]
    assert paths["json"].exists()
    assert "Explainability and Fairness Report" in paths["markdown"].read_text(
        encoding="utf-8"
    )
