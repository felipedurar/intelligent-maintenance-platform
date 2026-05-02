from pathlib import Path

import pandas as pd

from ingestion.schemas import NORMALIZED_COLUMN_MAP, OPTIONAL_FAILURE_MODE_COLUMNS
from ingestion.validation import validate_raw_ai4i_dataframe


def load_ai4i_csv(path: str | Path) -> pd.DataFrame:
    csv_path = Path(path)
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    validate_raw_ai4i_dataframe(df)
    for optional_column in OPTIONAL_FAILURE_MODE_COLUMNS:
        if optional_column not in df.columns:
            df[optional_column] = 0
    return df.rename(columns=NORMALIZED_COLUMN_MAP)
