from __future__ import annotations

import os

import pandas as pd
import psycopg

from training.constants import FEATURE_COLUMNS, TARGET_COLUMN


def default_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://datathon:datathon@localhost:5433/datathon")


def load_training_frame(database_url: str | None = None) -> pd.DataFrame:
    resolved_database_url = database_url or default_database_url()
    columns = ["udi", *FEATURE_COLUMNS, TARGET_COLUMN, "batch_id"]
    query = f"""
        select {", ".join(columns)}
        from ai4i_machine_features
        order by udi
    """

    with psycopg.connect(resolved_database_url) as conn:
        frame = pd.read_sql(query, conn)

    if frame.empty:
        raise ValueError(
            "No rows found in ai4i_machine_features. Run the ingestion flow before training."
        )

    return frame
