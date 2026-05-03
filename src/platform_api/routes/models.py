import os

from fastapi import APIRouter
from mlflow.tracking import MlflowClient
from pydantic import BaseModel

from training.constants import CHAMPION_ALIAS

router = APIRouter()


class ModelStatusResponse(BaseModel):
    model_name: str
    status: str
    model_version: str | None = None
    registry: str
    message: str


@router.get(
    "/{model_name}/active",
    response_model=ModelStatusResponse,
    summary="Get active model metadata",
    description=(
        "Returns active/champion model metadata from the MLflow Model Registry."
    ),
)
def get_active_model(model_name: str) -> ModelStatusResponse:
    try:
        client = MlflowClient(tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
        version = client.get_model_version_by_alias(model_name, CHAMPION_ALIAS)
        return ModelStatusResponse(
            model_name=model_name,
            status="active",
            model_version=str(version.version),
            registry="mlflow",
            message=f"Active model resolved from alias '{CHAMPION_ALIAS}'.",
        )
    except Exception as exc:
        return ModelStatusResponse(
            model_name=model_name,
            status="not_ready",
            model_version=None,
            registry="mlflow",
            message=f"No active MLflow champion model found yet: {exc}",
        )
