from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

from prefect import flow, get_run_logger, task

from features.ai4i import build_ai4i_features
from ingestion.loader import load_ai4i_csv
from ingestion.repository import IngestionResult, upsert_ai4i_dataset

DEFAULT_INITIAL_DATASET = "data/raw/ai4i2020.csv"
DEFAULT_INCOMING_DIR = "data/incoming"
DEFAULT_ARCHIVE_DIR = "data/archive"


def default_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://datathon:datathon@localhost:5433/datathon")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@task
def ingest_csv_file(path: str, database_url: str, batch_prefix: str) -> dict[str, object]:
    csv_path = Path(path)
    source_hash = _file_sha256(csv_path)
    batch_id = f"{batch_prefix}-{source_hash[:12]}"

    observations = load_ai4i_csv(csv_path)
    features = build_ai4i_features(observations)
    result = upsert_ai4i_dataset(
        database_url=database_url,
        batch_id=batch_id,
        source_file=csv_path,
        source_hash=source_hash,
        observations=observations,
        features=features,
    )
    return {
        "batch_id": result.batch_id,
        "source_file": result.source_file,
        "row_count": result.row_count,
        "feature_count": result.feature_count,
    }


@task
def archive_file(path: str, archive_dir: str) -> str:
    source = Path(path)
    archive_path = Path(archive_dir)
    archive_path.mkdir(parents=True, exist_ok=True)
    destination = archive_path / source.name
    shutil.move(str(source), destination)
    return str(destination)


@flow(name="ingest-initial-ai4i-dataset")
def ingest_initial_ai4i_dataset(
    csv_path: str = DEFAULT_INITIAL_DATASET,
    database_url: str | None = None,
) -> dict[str, object]:
    logger = get_run_logger()
    resolved_database_url = database_url or default_database_url()
    logger.info("Ingesting initial AI4I dataset from %s", csv_path)
    result = ingest_csv_file(csv_path, resolved_database_url, "initial")
    logger.info("Initial ingestion finished: %s", result)
    return result


@flow(name="ingest-incoming-ai4i-batches")
def ingest_incoming_ai4i_batches(
    incoming_dir: str = DEFAULT_INCOMING_DIR,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
    database_url: str | None = None,
) -> list[dict[str, object]]:
    logger = get_run_logger()
    resolved_database_url = database_url or default_database_url()
    incoming_path = Path(incoming_dir)
    incoming_path.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(incoming_path.glob("*.csv"))
    logger.info("Found %d incoming CSV files in %s", len(csv_files), incoming_path)

    results = []
    for csv_file in csv_files:
        result = ingest_csv_file(str(csv_file), resolved_database_url, "incoming")
        archived_to = archive_file(str(csv_file), archive_dir)
        result["archived_to"] = archived_to
        results.append(result)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI4I ingestion flows.")
    parser.add_argument(
        "flow_name",
        choices=["initial", "incoming"],
        help="Which ingestion flow to run.",
    )
    parser.add_argument("--csv-path", default=DEFAULT_INITIAL_DATASET)
    parser.add_argument("--incoming-dir", default=DEFAULT_INCOMING_DIR)
    parser.add_argument("--archive-dir", default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    if args.flow_name == "initial":
        ingest_initial_ai4i_dataset(csv_path=args.csv_path, database_url=args.database_url)
        return

    ingest_incoming_ai4i_batches(
        incoming_dir=args.incoming_dir,
        archive_dir=args.archive_dir,
        database_url=args.database_url,
    )


if __name__ == "__main__":
    main()
