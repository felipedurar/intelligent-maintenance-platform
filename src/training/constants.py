MODEL_NAME = "ai4i-machine-failure-classifier"
EXPERIMENT_NAME = "ai4i-predictive-maintenance"
CHAMPION_ALIAS = "champion"
TARGET_COLUMN = "machine_failure"

FEATURE_COLUMNS = [
    "air_temperature_k",
    "process_temperature_k",
    "temperature_delta_k",
    "rotational_speed_rpm",
    "rotational_speed_rad_s",
    "torque_nm",
    "tool_wear_min",
    "power_w",
    "torque_speed_interaction",
    "tool_wear_by_torque",
    "temperature_delta_low_flag",
    "power_low_flag",
    "power_high_flag",
    "overstrain_threshold",
    "overstrain_margin",
    "type_h",
    "type_l",
    "type_m",
]

RISK_THRESHOLDS = {
    "high": 0.70,
    "medium": 0.35,
}
