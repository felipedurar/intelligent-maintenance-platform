from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from agent.orchestrator import AgentOrchestrator, get_agent_orchestrator

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        examples=["Explain the failure risk for a machine with high torque and high tool wear."],
    )
    session_id: str | None = Field(
        default=None,
        examples=["demo-session-001"],
    )


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask the predictive-maintenance assistant",
    description=(
        "Receives a natural-language question and routes it to the agent orchestrator. "
        "Future implementations will use OpenAI tool calling, model metadata, prediction, "
        "drift status, and RAG tools."
    ),
)
def chat(
    request: ChatRequest,
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> ChatResponse:
    result = orchestrator.answer(message=request.message, session_id=request.session_id)
    return ChatResponse(**result)
