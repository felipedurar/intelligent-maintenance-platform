from fastapi import APIRouter
from pydantic import BaseModel

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
        "Returns active/champion model metadata from the model registry. "
        "The current implementation is a placeholder until MLflow is integrated."
    ),
)
def get_active_model(model_name: str) -> ModelStatusResponse:
    return ModelStatusResponse(
        model_name=model_name,
        status="not_configured",
        model_version=None,
        registry="mlflow",
        message="MLflow Model Registry integration will be implemented in model_serving.",
    )
