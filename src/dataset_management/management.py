from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from ingestion.loader import load_ai4i_csv


def file_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).name).strip("._")
    return cleaned or "dataset.csv"


@dataclass(frozen=True)
class DatasetUpload:
    dataset_id: str
    original_filename: str
    stored_path: str
    source_hash: str
    row_count: int
    status: str
    ingestion_recommended: bool


class DatasetManager:
    def __init__(
        self,
        *,
        database_url: str,
        incoming_dir: str = "data/incoming",
    ) -> None:
        self.database_url = database_url
        self.incoming_dir = Path(incoming_dir)

    def initialize_schema(self) -> None:
        statement = """
        create table if not exists dataset_uploads (
            dataset_id text primary key,
            original_filename text not null,
            stored_path text not null,
            source_hash text not null,
            row_count integer not null,
            status text not null,
            ingestion_recommended boolean not null,
            created_at timestamptz not null default now(),
            updated_at timestamptz not null default now()
        )
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(statement)
            conn.commit()

    def save_upload(self, *, filename: str, content: bytes) -> DatasetUpload:
        if not filename.lower().endswith(".csv"):
            raise ValueError("Only CSV files are accepted for AI4I ingestion.")
        if not content:
            raise ValueError("Uploaded dataset is empty.")

        self.initialize_schema()
        self.incoming_dir.mkdir(parents=True, exist_ok=True)
        dataset_id = str(uuid4())
        digest = file_sha256(content)
        cleaned_name = safe_filename(filename)
        destination = self.incoming_dir / f"{dataset_id}_{cleaned_name}"
        destination.write_bytes(content)

        try:
            observations = load_ai4i_csv(destination)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

        upload = DatasetUpload(
            dataset_id=dataset_id,
            original_filename=filename,
            stored_path=str(destination),
            source_hash=digest,
            row_count=len(observations),
            status="uploaded",
            ingestion_recommended=True,
        )
        self._insert_upload(upload)
        return upload

    def _insert_upload(self, upload: DatasetUpload) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into dataset_uploads (
                        dataset_id, original_filename, stored_path, source_hash,
                        row_count, status, ingestion_recommended
                    )
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        upload.dataset_id,
                        upload.original_filename,
                        upload.stored_path,
                        upload.source_hash,
                        upload.row_count,
                        upload.status,
                        upload.ingestion_recommended,
                    ),
                )
            conn.commit()

    def mark_upload_status(self, dataset_id: str, status: str) -> None:
        self.initialize_schema()
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    update dataset_uploads
                    set status = %s, updated_at = now()
                    where dataset_id = %s
                    """,
                    (status, dataset_id),
                )
            conn.commit()

    def list_uploads(self, limit: int = 50) -> list[dict[str, object]]:
        self.initialize_schema()
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select dataset_id, original_filename, stored_path, source_hash, row_count,
                           status, ingestion_recommended, created_at, updated_at
                    from dataset_uploads
                    order by created_at desc
                    limit %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def list_ingestion_batches(self, limit: int = 50) -> list[dict[str, object]]:
        self._ensure_ingestion_table_exists()
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select batch_id, source_file, source_hash, row_count, status, ingested_at
                    from ingestion_batches
                    order by ingested_at desc
                    limit %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def get_ingestion_batch(self, batch_id: str) -> dict[str, object] | None:
        self._ensure_ingestion_table_exists()
        with psycopg.connect(self.database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select batch_id, source_file, source_hash, row_count, status, ingested_at
                    from ingestion_batches
                    where batch_id = %s
                    """,
                    (batch_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None

    def _ensure_ingestion_table_exists(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    create table if not exists ingestion_batches (
                        batch_id text primary key,
                        source_file text not null,
                        source_hash text not null,
                        row_count integer not null,
                        status text not null,
                        ingested_at timestamptz not null default now()
                    )
                    """
                )
            conn.commit()


async def trigger_prefect_deployment(deployment_name: str) -> dict[str, object]:
    """Create a flow run from a Prefect deployment name."""
    from prefect.client.orchestration import get_client

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(deployment_name)
        flow_run = await client.create_flow_run_from_deployment(deployment.id)

    return {
        "deployment": deployment_name,
        "flow_run_id": str(flow_run.id),
        "flow_run_name": flow_run.name,
        "status": "submitted",
    }
