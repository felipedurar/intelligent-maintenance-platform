import pandas as pd

from ingestion.schemas import OPTIONAL_FAILURE_MODE_COLUMNS, REQUIRED_RAW_AI4I_COLUMNS


class DatasetValidationError(ValueError):
    pass


def validate_raw_ai4i_dataframe(df: pd.DataFrame) -> None:
    missing_columns = [column for column in REQUIRED_RAW_AI4I_COLUMNS if column not in df.columns]
    if missing_columns:
        raise DatasetValidationError(f"Missing required columns: {missing_columns}")

    if df.empty:
        raise DatasetValidationError("Dataset is empty.")

    if df["UDI"].isna().any():
        raise DatasetValidationError("UDI contains null values.")

    if df["UDI"].duplicated().any():
        raise DatasetValidationError("UDI contains duplicated values.")

    allowed_types = {"L", "M", "H"}
    invalid_types = set(df["Type"].dropna().unique()) - allowed_types
    if invalid_types:
        raise DatasetValidationError(f"Invalid product types: {sorted(invalid_types)}")

    binary_columns = ["Machine failure", "TWF"] + [
        column for column in OPTIONAL_FAILURE_MODE_COLUMNS if column in df.columns
    ]
    for column in binary_columns:
        invalid_values = set(df[column].dropna().unique()) - {0, 1}
        if invalid_values:
            raise DatasetValidationError(
                f"Column {column} has non-binary values: {sorted(invalid_values)}"
            )

    numeric_columns = [
        "Air temperature [K]",
        "Process temperature [K]",
        "Rotational speed [rpm]",
        "Torque [Nm]",
        "Tool wear [min]",
    ]
    if df[numeric_columns].isna().any().any():
        raise DatasetValidationError("One or more numeric columns contain null values.")

    if (df["Tool wear [min]"] < 0).any():
        raise DatasetValidationError("Tool wear contains negative values.")
