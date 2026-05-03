import pandas as pd

from features.ai4i import build_ai4i_features


def test_build_ai4i_features_creates_expected_engineered_columns() -> None:
    source = pd.DataFrame(
        [
            {
                "udi": 1,
                "product_id": "L47181",
                "product_type": "L",
                "air_temperature_k": 298.1,
                "process_temperature_k": 308.6,
                "rotational_speed_rpm": 1200.0,
                "torque_nm": 50.0,
                "tool_wear_min": 230.0,
                "machine_failure": 1,
            }
        ]
    )

    features = build_ai4i_features(source)
    row = features.iloc[0]

    assert row["temperature_delta_k"] == 10.5
    assert round(row["rotational_speed_rad_s"], 4) == 125.6637
    assert round(row["power_w"], 2) == 6283.19
    assert row["torque_speed_interaction"] == 60000.0
    assert row["tool_wear_by_torque"] == 11500.0
    assert row["overstrain_threshold"] == 11000.0
    assert row["overstrain_margin"] == 500.0
    assert row["type_L"] == 1
    assert row["type_M"] == 0
    assert row["type_H"] == 0


def test_build_ai4i_features_flags_known_failure_rules() -> None:
    source = pd.DataFrame(
        [
            {
                "udi": 1,
                "product_id": "M00001",
                "product_type": "M",
                "air_temperature_k": 300.0,
                "process_temperature_k": 307.0,
                "rotational_speed_rpm": 1000.0,
                "torque_nm": 20.0,
                "tool_wear_min": 10.0,
                "machine_failure": 0,
            },
            {
                "udi": 2,
                "product_id": "H00001",
                "product_type": "H",
                "air_temperature_k": 300.0,
                "process_temperature_k": 313.0,
                "rotational_speed_rpm": 2000.0,
                "torque_nm": 50.0,
                "tool_wear_min": 10.0,
                "machine_failure": 1,
            },
        ]
    )

    features = build_ai4i_features(source)

    assert features.loc[0, "temperature_delta_low_flag"] == 1
    assert features.loc[0, "power_low_flag"] == 1
    assert features.loc[1, "power_high_flag"] == 1
