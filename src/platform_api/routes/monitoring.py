from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class MonitoringStatusResponse(BaseModel):
    status: str
    metrics: list[str]
    message: str


@router.get(
    "/status",
    response_model=MonitoringStatusResponse,
    summary="Get monitoring integration status",
    description=(
        "Returns expected operational and drift metrics. The current implementation is a "
        "placeholder until Prometheus/Grafana and Evidently integrations are connected."
    ),
)
def monitoring_status() -> MonitoringStatusResponse:
    return MonitoringStatusResponse(
        status="not_configured",
        metrics=[
            "api_latency",
            "prediction_requests",
            "prediction_risk_class_distribution",
            "agent_tool_calls",
            "feature_drift",
            "prediction_drift",
        ],
        message="Prometheus/Grafana and Evidently integrations will be added in monitoring modules.",
    )
