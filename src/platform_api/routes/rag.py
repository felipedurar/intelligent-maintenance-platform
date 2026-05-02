from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

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
        "Searches project/governance documentation chunks. The current implementation is a "
        "placeholder until chunking, embeddings, and vector database integration are added."
    ),
)
def search(
    request: RagSearchRequest,
    retriever: RagRetriever = Depends(get_rag_retriever),
) -> RagSearchResponse:
    result = retriever.search(query=request.query, limit=request.limit)
    return RagSearchResponse(**result)
