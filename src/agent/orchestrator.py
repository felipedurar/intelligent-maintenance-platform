from __future__ import annotations

import json
import os
from typing import Any

from mlflow.tracking import MlflowClient
from openai import OpenAI

from model_serving.service import get_model_serving_service
from rag.retriever import get_rag_retriever
from training.constants import CHAMPION_ALIAS, MODEL_NAME


SYSTEM_PROMPT = """
You are the Datathon Predictive Maintenance assistant.
Help users understand machine-failure risk, the AI4I dataset, the model, the platform architecture,
and governance documentation. Use tools when the answer depends on current model metadata,
platform documentation, or a machine observation.

Rules:
- Do not invent model metrics, versions, or documentation sources.
- Explain predictive-maintenance results in practical operational language.
- Make clear that this is a decision-support model, not an automatic maintenance command.
- If you use retrieved documentation, cite the source filenames in the answer.
""".strip()


TOOLS = [
    {
        "type": "function",
        "name": "search_project_docs",
        "description": "Search project, architecture, model, stack, and governance documentation.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_active_model",
        "description": "Return the active champion model metadata from MLflow.",
        "parameters": {
            "type": "object",
            "properties": {
                "model_name": {
                    "type": "string",
                    "default": MODEL_NAME,
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "predict_machine_failure",
        "description": "Predict machine-failure probability for one AI4I machine observation.",
        "parameters": {
            "type": "object",
            "properties": {
                "product_type": {"type": "string", "enum": ["L", "M", "H"]},
                "air_temperature_k": {"type": "number"},
                "process_temperature_k": {"type": "number"},
                "rotational_speed_rpm": {"type": "number"},
                "torque_nm": {"type": "number"},
                "tool_wear_min": {"type": "number", "minimum": 0},
            },
            "required": [
                "product_type",
                "air_temperature_k",
                "process_temperature_k",
                "rotational_speed_rpm",
                "torque_nm",
                "tool_wear_min",
            ],
            "additionalProperties": False,
        },
    },
]


class AgentOrchestrator:
    """Coordinates chat requests, OpenAI calls, and platform tools."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_CHAT_MODEL", "gpt-4.1-mini")
        self._client = client

    @property
    def client(self) -> OpenAI:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for chat orchestration.")
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def answer(self, message: str, session_id: str | None = None) -> dict[str, object]:
        if not self.api_key:
            return self._fallback_answer(message, session_id)

        input_items: list[dict[str, Any]] = [{"role": "user", "content": message}]
        tool_calls: list[dict[str, object]] = []
        sources: set[str] = set()

        try:
            for _ in range(4):
                response = self.client.responses.create(
                    model=self.model,
                    instructions=SYSTEM_PROMPT,
                    input=input_items,
                    tools=TOOLS,
                )
                function_calls = [
                    item for item in response.output if getattr(item, "type", None) == "function_call"
                ]
                if not function_calls:
                    return {
                        "answer": self._response_text(response),
                        "tool_calls": [call["name"] for call in tool_calls],
                        "sources": sorted(sources),
                        "metadata": {
                            "session_id": session_id,
                            "llm_provider": "openai",
                            "model": self.model,
                            "tool_call_details": tool_calls,
                        },
                    }

                input_items.extend(self._serialize_output_item(item) for item in response.output)
                for function_call in function_calls:
                    result = self._execute_tool(function_call.name, function_call.arguments)
                    tool_calls.append({"name": function_call.name, "arguments": function_call.arguments})
                    for source in result.get("sources", []):
                        sources.add(str(source))
                    input_items.append(
                        {
                            "type": "function_call_output",
                            "call_id": function_call.call_id,
                            "output": json.dumps(result, ensure_ascii=False),
                        }
                    )

            return {
                "answer": "I used the available tools but could not finish within the tool-call limit.",
                "tool_calls": [call["name"] for call in tool_calls],
                "sources": sorted(sources),
                "metadata": {
                    "session_id": session_id,
                    "llm_provider": "openai",
                    "model": self.model,
                    "tool_call_details": tool_calls,
                    "status": "tool_limit_reached",
                },
            }
        except Exception as exc:
            return {
                "answer": (
                    "The OpenAI chat orchestration is not ready right now. "
                    "Check OPENAI_API_KEY, model configuration, and tool dependencies."
                ),
                "tool_calls": [call["name"] for call in tool_calls],
                "sources": sorted(sources),
                "metadata": {
                    "session_id": session_id,
                    "llm_provider": "openai",
                    "model": self.model,
                    "error": str(exc),
                },
            }

    def _fallback_answer(self, message: str, session_id: str | None) -> dict[str, object]:
        rag_result = get_rag_retriever().search(message, limit=3)
        sources = [result["source"] for result in rag_result.get("results", [])]
        context = "\n\n".join(
            f"- {result['source']}: {result['text'][:400]}"
            for result in rag_result.get("results", [])
        )
        answer = (
            "OPENAI_API_KEY is not configured, so I cannot run the LLM agent yet. "
            "I searched the local RAG index and found the context below.\n\n"
            f"{context or rag_result.get('message', 'No context found.')}"
        )
        return {
            "answer": answer,
            "tool_calls": ["search_project_docs"],
            "sources": sources,
            "metadata": {
                "session_id": session_id,
                "received_message": message,
                "llm_provider": "openai",
                "status": "missing_openai_api_key",
                "rag_status": rag_result.get("status"),
            },
        }

    def _execute_tool(self, name: str, encoded_arguments: str) -> dict[str, object]:
        arguments = json.loads(encoded_arguments or "{}")
        if name == "search_project_docs":
            result = get_rag_retriever().search(
                query=arguments["query"],
                limit=int(arguments.get("limit", 5)),
            )
            return {
                **result,
                "sources": [item["source"] for item in result.get("results", [])],
            }

        if name == "get_active_model":
            model_name = arguments.get("model_name") or MODEL_NAME
            try:
                client = MlflowClient(
                    tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
                )
                version = client.get_model_version_by_alias(model_name, CHAMPION_ALIAS)
                return {
                    "status": "active",
                    "model_name": model_name,
                    "model_version": str(version.version),
                    "alias": CHAMPION_ALIAS,
                    "sources": [],
                }
            except Exception as exc:
                return {
                    "status": "not_ready",
                    "model_name": model_name,
                    "error": str(exc),
                    "sources": [],
                }

        if name == "predict_machine_failure":
            result = get_model_serving_service().predict_failure(arguments)
            return {**result, "sources": []}

        return {"status": "unknown_tool", "tool": name, "sources": []}

    def _response_text(self, response: Any) -> str:
        text = getattr(response, "output_text", None)
        if text:
            return str(text)
        parts: list[str] = []
        for item in getattr(response, "output", []):
            if getattr(item, "type", None) != "message":
                continue
            for content in getattr(item, "content", []):
                if getattr(content, "type", None) in {"output_text", "text"}:
                    parts.append(str(getattr(content, "text", "")))
        return "\n".join(part for part in parts if part).strip()

    def _serialize_output_item(self, item: Any) -> dict[str, Any]:
        if hasattr(item, "model_dump"):
            return item.model_dump()
        if isinstance(item, dict):
            return item
        return dict(item)


_orchestrator = AgentOrchestrator()


def get_agent_orchestrator() -> AgentOrchestrator:
    return _orchestrator
