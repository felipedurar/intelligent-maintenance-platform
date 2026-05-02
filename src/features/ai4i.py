import pandas as pd


TYPE_OVERSTRAIN_THRESHOLDS = {
    "L": 11000.0,
    "M": 12000.0,
    "H": 13000.0,
}


def build_ai4i_features(df: pd.DataFrame) -> pd.DataFrame:
    features = df.copy()

    features["temperature_delta_k"] = (
        features["process_temperature_k"] - features["air_temperature_k"]
    )
    features["rotational_speed_rad_s"] = features["rotational_speed_rpm"] * 2.0 * 3.141592653589793 / 60.0
    features["power_w"] = features["torque_nm"] * features["rotational_speed_rad_s"]
    features["torque_speed_interaction"] = (
        features["torque_nm"] * features["rotational_speed_rpm"]
    )
    features["tool_wear_by_torque"] = features["tool_wear_min"] * features["torque_nm"]
    features["temperature_delta_low_flag"] = (
        (features["temperature_delta_k"] < 8.6)
        & (features["rotational_speed_rpm"] < 1380)
    ).astype(int)
    features["power_low_flag"] = (features["power_w"] < 3500).astype(int)
    features["power_high_flag"] = (features["power_w"] > 9000).astype(int)
    features["overstrain_threshold"] = features["product_type"].map(TYPE_OVERSTRAIN_THRESHOLDS)
    features["overstrain_margin"] = (
        features["tool_wear_by_torque"] - features["overstrain_threshold"]
    )

    type_dummies = pd.get_dummies(features["product_type"], prefix="type", dtype=int)
    for column in ["type_H", "type_L", "type_M"]:
        if column not in type_dummies:
            type_dummies[column] = 0

    return pd.concat([features, type_dummies[["type_H", "type_L", "type_M"]]], axis=1)
