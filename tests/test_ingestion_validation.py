import pandas as pd
import pytest

from ingestion.loader import load_ai4i_csv
from ingestion.validation import DatasetValidationError, validate_raw_ai4i_dataframe


def valid_raw_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "UDI": 1,
                "Product ID": "L47181",
                "Type": "L",
                "Air temperature [K]": 298.1,
                "Process temperature [K]": 308.6,
                "Rotational speed [rpm]": 1551,
                "Torque [Nm]": 42.8,
                "Tool wear [min]": 108,
                "Machine failure": 0,
                "TWF": 0,
            }
        ]
    )


def test_validate_raw_ai4i_dataframe_accepts_required_columns_without_optional_modes() -> None:
    validate_raw_ai4i_dataframe(valid_raw_frame())


def test_validate_raw_ai4i_dataframe_rejects_invalid_binary_values() -> None:
    frame = valid_raw_frame()
    frame.loc[0, "Machine failure"] = 2

    with pytest.raises(DatasetValidationError, match="non-binary"):
        validate_raw_ai4i_dataframe(frame)


def test_load_ai4i_csv_normalizes_columns_and_defaults_optional_modes(tmp_path) -> None:
    csv_path = tmp_path / "ai4i.csv"
    valid_raw_frame().to_csv(csv_path, index=False)

    loaded = load_ai4i_csv(csv_path)

    assert set(["hdf", "pwf", "osf", "rnf"]).issubset(loaded.columns)
    assert loaded.loc[0, "udi"] == 1
    assert loaded.loc[0, "product_type"] == "L"
    assert loaded.loc[0, "hdf"] == 0
