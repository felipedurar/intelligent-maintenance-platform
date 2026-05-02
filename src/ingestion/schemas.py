REQUIRED_RAW_AI4I_COLUMNS = [
    "UDI",
    "Product ID",
    "Type",
    "Air temperature [K]",
    "Process temperature [K]",
    "Rotational speed [rpm]",
    "Torque [Nm]",
    "Tool wear [min]",
    "Machine failure",
    "TWF",
]

OPTIONAL_FAILURE_MODE_COLUMNS = [
    "HDF",
    "PWF",
    "OSF",
    "RNF",
]

RAW_AI4I_COLUMNS = REQUIRED_RAW_AI4I_COLUMNS + OPTIONAL_FAILURE_MODE_COLUMNS

NORMALIZED_COLUMN_MAP = {
    "UDI": "udi",
    "Product ID": "product_id",
    "Type": "product_type",
    "Air temperature [K]": "air_temperature_k",
    "Process temperature [K]": "process_temperature_k",
    "Rotational speed [rpm]": "rotational_speed_rpm",
    "Torque [Nm]": "torque_nm",
    "Tool wear [min]": "tool_wear_min",
    "Machine failure": "machine_failure",
    "TWF": "twf",
    "HDF": "hdf",
    "PWF": "pwf",
    "OSF": "osf",
    "RNF": "rnf",
}

CURATED_COLUMNS = list(NORMALIZED_COLUMN_MAP.values())
