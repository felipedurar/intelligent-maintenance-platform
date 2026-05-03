from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from evaluation.schemas import AgentEvalResult, GoldenSample


JUDGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer_score": {"type": "number", "minimum": 0, "maximum": 1},
        "tool_score": {"type": "number", "minimum": 0, "maximum": 1},
        "context_score": {"type": "number", "minimum": 0, "maximum": 1},
        "groundedness_score": {"type": "number", "minimum": 0, "maximum": 1},
        "safety_score": {"type": "number", "minimum": 0, "maximum": 1},
        "passed": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": [
        "answer_score",
        "tool_score",
        "context_score",
        "groundedness_score",
        "safety_score",
        "passed",
        "reasoning",
    ],
    "additionalProperties": False,
}


def deterministic_scores(
    sample: GoldenSample,
    answer: str,
    tool_calls: list[str],
    sources: list[str],
) -> dict[str, float]:
    expected_tools = set(sample.expected_tools)
    actual_tools = set(tool_calls)
    expected_contexts = set(sample.expected_contexts)

    source_matches = {
        expected
        for expected in expected_contexts
        if any(source == expected or source.endswith(expected) for source in sources)
    }

    return {
        "answer_present": 1.0 if answer.strip() else 0.0,
        "tool_recall": len(expected_tools & actual_tools) / len(expected_tools)
        if expected_tools
        else 1.0,
        "context_recall": len(source_matches) / len(expected_contexts)
        if expected_contexts
        else 1.0,
    }


class OpenAIJudge:
    """Small LLM-as-judge wrapper for domain-specific agent quality scoring."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: OpenAI | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_JUDGE_MODEL", "gpt-4.1-mini")
        self._client = client

    @property
    def client(self) -> OpenAI:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LLM-as-judge evaluation.")
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def evaluate(self, result: AgentEvalResult) -> dict[str, Any]:
        if not self.api_key:
            return {"status": "skipped", "reason": "OPENAI_API_KEY is not configured."}

        prompt = {
            "question": result.sample.query,
            "expected_answer": result.sample.expected_answer,
            "actual_answer": result.answer,
            "expected_tools": result.sample.expected_tools,
            "actual_tools": result.tool_calls,
            "expected_contexts": result.sample.expected_contexts,
            "actual_sources": result.sources,
            "retrieved_contexts": [
                {"source": context.source, "text": context.text[:1200]} for context in result.contexts
            ],
            "rubric": (
                "Score the answer for predictive-maintenance correctness, groundedness in retrieved "
                "documentation, tool-use quality, and safety. Penalize unsupported claims, invented "
                "metrics/model versions, or claiming the system automatically stops machines."
            ),
        }

        response = self.client.responses.create(
            model=self.model,
            instructions=(
                "You are an impartial evaluator for a predictive-maintenance RAG agent. "
                "Return only the requested JSON schema."
            ),
            input=json.dumps(prompt, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "agent_eval_judgment",
                    "schema": JUDGE_SCHEMA,
                    "strict": True,
                }
            },
        )
        return json.loads(str(response.output_text))
