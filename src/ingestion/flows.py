from __future__ import annotations

import argparse
import hashlib
import os
import shutil
from pathlib import Path

from prefect import flow, get_run_logger, task

from features.ai4i import build_ai4i_features
from ingestion.loader import load_ai4i_csv
from ingestion.repository import upsert_ai4i_dataset

DEFAULT_INITIAL_DATASET = "data/raw/ai4i2020.csv"
DEFAULT_INCOMING_DIR = "data/incoming"
DEFAULT_ARCHIVE_DIR = "data/archive"
DEFAULT_PROCESSED_DIR = "data/processed"


def default_database_url() -> str:
    return os.getenv("DATABASE_URL", "postgresql://datathon:datathon@localhost:5433/datathon")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@task
def export_processed_features(path: str, batch_prefix: str, processed_dir: str) -> dict[str, str]:
    csv_path = Path(path)
    source_hash = _file_sha256(csv_path)
    batch_id = f"{batch_prefix}-{source_hash[:12]}"

    observations = load_ai4i_csv(csv_path)
    features = build_ai4i_features(observations)

    output_dir = Path(processed_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    batch_file = output_dir / f"ai4i_features_{batch_id}.csv"
    latest_file = output_dir / "ai4i_features_latest.csv"
    features.to_csv(batch_file, index=False)
    features.to_csv(latest_file, index=False)

    return {
        "processed_file": str(batch_file),
        "latest_processed_file": str(latest_file),
    }


@task
def ingest_csv_file(
    path: str,
    database_url: str,
    batch_prefix: str,
) -> dict[str, object]:
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
def merge_ingestion_result(
    result: dict[str, object],
    processed_artifacts: dict[str, str],
    archived_to: str | None = None,
) -> dict[str, object]:
    merged = {**result, **processed_artifacts}
    if archived_to:
        merged["archived_to"] = archived_to
    return merged


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
    processed_dir: str = DEFAULT_PROCESSED_DIR,
    database_url: str | None = None,
) -> dict[str, object]:
    logger = get_run_logger()
    resolved_database_url = database_url or default_database_url()
    logger.info("Ingesting initial AI4I dataset from %s", csv_path)
    result = ingest_csv_file(csv_path, resolved_database_url, "initial")
    processed_artifacts = export_processed_features(csv_path, "initial", processed_dir)
    merged_result = merge_ingestion_result(result, processed_artifacts)
    logger.info("Initial ingestion finished: %s", merged_result)
    return merged_result


@flow(name="ingest-incoming-ai4i-batches")
def ingest_incoming_ai4i_batches(
    incoming_dir: str = DEFAULT_INCOMING_DIR,
    archive_dir: str = DEFAULT_ARCHIVE_DIR,
    processed_dir: str = DEFAULT_PROCESSED_DIR,
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
        processed_artifacts = export_processed_features(str(csv_file), "incoming", processed_dir)
        archived_to = archive_file(str(csv_file), archive_dir)
        results.append(merge_ingestion_result(result, processed_artifacts, archived_to))

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
    parser.add_argument("--processed-dir", default=DEFAULT_PROCESSED_DIR)
    parser.add_argument("--database-url", default=None)
    args = parser.parse_args()

    if args.flow_name == "initial":
        ingest_initial_ai4i_dataset(
            csv_path=args.csv_path,
            processed_dir=args.processed_dir,
            database_url=args.database_url,
        )
        return

    ingest_incoming_ai4i_batches(
        incoming_dir=args.incoming_dir,
        archive_dir=args.archive_dir,
        processed_dir=args.processed_dir,
        database_url=args.database_url,
    )


if __name__ == "__main__":
    main()
