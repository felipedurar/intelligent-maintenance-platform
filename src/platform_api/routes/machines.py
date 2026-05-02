from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class DatasetStatusResponse(BaseModel):
    status: str
    dataset: str
    message: str
    expected_columns: list[str]


@router.get(
    "/dataset/status",
    response_model=DatasetStatusResponse,
    summary="Get dataset ingestion status",
    description=(
        "Returns the expected AI4I 2020 dataset schema and current ingestion placeholder status."
    ),
)
def dataset_status() -> DatasetStatusResponse:
    return DatasetStatusResponse(
        status="not_ingested",
        dataset="AI4I 2020 Predictive Maintenance Dataset",
        message="CSV ingestion and PostgreSQL persistence will be implemented in ingestion flows.",
        expected_columns=[
            "UDI",
            "Product ID",
            "Type",
            "Air temperature [K]",
            "Process temperature [K]",
            "Rotational speed [rpm]",
            "Torque [Nm]",
            "Tool wear [min]",
            "Machine failure",
            "TWF",
            "HDF",
            "PWF",
            "OSF",
            "RNF",
        ],
    )
