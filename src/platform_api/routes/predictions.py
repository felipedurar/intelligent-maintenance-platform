from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from model_serving.service import ModelServingService, get_model_serving_service

router = APIRouter()


class MachineObservation(BaseModel):
    product_type: Literal["L", "M", "H"] = Field(..., examples=["L"])
    air_temperature_k: float = Field(..., examples=[298.1])
    process_temperature_k: float = Field(..., examples=[308.6])
    rotational_speed_rpm: float = Field(..., examples=[1551.0])
    torque_nm: float = Field(..., examples=[42.8])
    tool_wear_min: float = Field(..., ge=0, examples=[108.0])


class PredictionRequest(BaseModel):
    observation: MachineObservation
    request_id: str | None = Field(default=None, examples=["prediction-demo-001"])


class PredictionResponse(BaseModel):
    status: str
    failure_probability: float | None = None
    risk_class: str | None = None
    model_version: str | None = None
    message: str
    metadata: dict[str, object] = Field(default_factory=dict)


@router.post(
    "",
    response_model=PredictionResponse,
    summary="Predict machine failure risk",
    description=(
        "Scores one machine/process observation and returns failure probability, risk class, "
        "model version, and metadata from the registered MLflow champion model."
    ),
)
def predict_failure(
    request: PredictionRequest,
    service: ModelServingService = Depends(get_model_serving_service),
) -> PredictionResponse:
    result = service.predict_failure(
        observation=request.observation.model_dump(),
        request_id=request.request_id,
    )
    return PredictionResponse(**result)
