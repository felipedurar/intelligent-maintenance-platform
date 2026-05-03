from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from monitoring.metrics import elapsed_seconds, record_rag_search, timer_start
from rag.retriever import RagRetriever, get_rag_retriever

router = APIRouter()


class RagSearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        examples=["What features are used by the predictive-maintenance model?"],
    )
    limit: int = Field(default=5, ge=1, le=20)


class RagSearchResult(BaseModel):
    text: str
    source: str
    score: float | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RagSearchResponse(BaseModel):
    query: str
    status: str
    results: list[RagSearchResult]
    message: str


@router.post(
    "/search",
    response_model=RagSearchResponse,
    summary="Search indexed documentation",
    description=(
        "Searches project/governance documentation chunks indexed in Qdrant using OpenAI "
        "embeddings."
    ),
)
def search(
    request: RagSearchRequest,
    retriever: RagRetriever = Depends(get_rag_retriever),
) -> RagSearchResponse:
    started_at = timer_start()
    result = retriever.search(query=request.query, limit=request.limit)
    record_rag_search(
        status=str(result.get("status", "unknown")),
        latency_seconds=elapsed_seconds(started_at),
    )
    return RagSearchResponse(**result)
