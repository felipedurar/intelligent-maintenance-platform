from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel

from dataset_management.management import DatasetManager, trigger_prefect_deployment
from ingestion.validation import DatasetValidationError
from platform_api.config import Settings, get_settings

router = APIRouter()

INCOMING_DEPLOYMENT = "ingest-incoming-ai4i-batches/incoming-ai4i-batches"
TRAINING_DEPLOYMENT = "train-ai4i-failure-classifier/train-ai4i-failure-classifier"


class PrefectTriggerResponse(BaseModel):
    status: str
    deployment: str
    flow_run_id: str | None = None
    flow_run_name: str | None = None
    message: str


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    original_filename: str
    stored_path: str
    source_hash: str
    row_count: int
    status: str
    ingestion_recommended: bool
    ingestion_trigger: PrefectTriggerResponse | None = None
    message: str


class DatasetUploadRecord(BaseModel):
    dataset_id: str
    original_filename: str
    stored_path: str
    source_hash: str
    row_count: int
    status: str
    ingestion_recommended: bool
    created_at: datetime
    updated_at: datetime


class IngestionBatchRecord(BaseModel):
    batch_id: str
    source_file: str
    source_hash: str
    row_count: int
    status: str
    ingested_at: datetime


class DatasetCollectionResponse(BaseModel):
    status: str
    count: int
    results: list[DatasetUploadRecord] | list[IngestionBatchRecord]


def get_dataset_manager(settings: Settings = Depends(get_settings)) -> DatasetManager:
    return DatasetManager(
        database_url=settings.database_url,
        incoming_dir=settings.dataset_incoming_dir,
    )


async def _trigger(deployment_name: str) -> PrefectTriggerResponse:
    try:
        result = await trigger_prefect_deployment(deployment_name)
        return PrefectTriggerResponse(
            status="submitted",
            deployment=deployment_name,
            flow_run_id=str(result.get("flow_run_id")),
            flow_run_name=str(result.get("flow_run_name")),
            message="Prefect deployment run submitted.",
        )
    except Exception as exc:
        return PrefectTriggerResponse(
            status="not_submitted",
            deployment=deployment_name,
            message=f"Could not submit Prefect deployment run: {exc}",
        )


@router.post(
    "/upload",
    response_model=DatasetUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an AI4I CSV batch",
    description=(
        "Stores a new AI4I-compatible CSV in the controlled incoming folder, validates schema, "
        "records dataset metadata, and optionally triggers the Prefect incoming-ingestion "
        "deployment. Upload does not train or promote a model automatically."
    ),
)
async def upload_dataset(
    file: Annotated[UploadFile, File(description="AI4I-compatible CSV file.")],
    trigger_ingestion: Annotated[
        bool,
        Form(description="Submit the incoming-ingestion Prefect deployment after upload."),
    ] = False,
    settings: Settings = Depends(get_settings),
    manager: DatasetManager = Depends(get_dataset_manager),
) -> DatasetUploadResponse:
    content = await file.read()
    max_bytes = settings.max_dataset_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Dataset exceeds max upload size of {settings.max_dataset_upload_mb} MB.",
        )

    try:
        upload = manager.save_upload(filename=file.filename or "dataset.csv", content=content)
    except DatasetValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    ingestion_trigger = None
    if trigger_ingestion:
        ingestion_trigger = await _trigger(INCOMING_DEPLOYMENT)
        if ingestion_trigger.status == "submitted":
            manager.mark_upload_status(upload.dataset_id, "ingestion_requested")

    return DatasetUploadResponse(
        dataset_id=upload.dataset_id,
        original_filename=upload.original_filename,
        stored_path=upload.stored_path,
        source_hash=upload.source_hash,
        row_count=upload.row_count,
        status="ingestion_requested" if ingestion_trigger and ingestion_trigger.status == "submitted" else upload.status,
        ingestion_recommended=upload.ingestion_recommended,
        ingestion_trigger=ingestion_trigger,
        message=(
            "Dataset uploaded and ingestion requested."
            if ingestion_trigger and ingestion_trigger.status == "submitted"
            else "Dataset uploaded. Run incoming ingestion to process it."
        ),
    )


@router.get(
    "/uploads",
    response_model=DatasetCollectionResponse,
    summary="List uploaded datasets",
)
def list_uploads(
    limit: int = Query(default=50, ge=1, le=200),
    manager: DatasetManager = Depends(get_dataset_manager),
) -> DatasetCollectionResponse:
    results = [DatasetUploadRecord(**row) for row in manager.list_uploads(limit=limit)]
    return DatasetCollectionResponse(status="ok", count=len(results), results=results)


@router.get(
    "/batches",
    response_model=DatasetCollectionResponse,
    summary="List ingested batches",
)
def list_batches(
    limit: int = Query(default=50, ge=1, le=200),
    manager: DatasetManager = Depends(get_dataset_manager),
) -> DatasetCollectionResponse:
    results = [
        IngestionBatchRecord(**row) for row in manager.list_ingestion_batches(limit=limit)
    ]
    return DatasetCollectionResponse(status="ok", count=len(results), results=results)


@router.get(
    "/batches/{batch_id}",
    response_model=IngestionBatchRecord,
    summary="Get one ingested batch",
)
def get_batch(
    batch_id: str,
    manager: DatasetManager = Depends(get_dataset_manager),
) -> IngestionBatchRecord:
    result = manager.get_ingestion_batch(batch_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found.")
    return IngestionBatchRecord(**result)


@router.post(
    "/ingest",
    response_model=PrefectTriggerResponse,
    summary="Trigger incoming dataset ingestion",
    description="Submits the Prefect deployment that scans data/incoming/*.csv.",
)
async def trigger_incoming_ingestion() -> PrefectTriggerResponse:
    return await _trigger(INCOMING_DEPLOYMENT)


@router.post(
    "/retrain",
    response_model=PrefectTriggerResponse,
    summary="Trigger model training",
    description=(
        "Submits the Prefect training deployment. Training creates a candidate model; "
        "production promotion remains a separate human approval step."
    ),
)
async def trigger_retraining() -> PrefectTriggerResponse:
    return await _trigger(TRAINING_DEPLOYMENT)
