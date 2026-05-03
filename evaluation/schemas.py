from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GoldenSample:
    id: str
    query: str
    expected_answer: str
    expected_tools: list[str] = field(default_factory=list)
    expected_contexts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RetrievedContext:
    text: str
    source: str
    score: float | None = None


@dataclass(frozen=True)
class AgentEvalResult:
    sample: GoldenSample
    answer: str
    tool_calls: list[str]
    sources: list[str]
    contexts: list[RetrievedContext]
    metadata: dict[str, Any]
    deterministic_scores: dict[str, float]
    judge_scores: dict[str, Any] | None = None
    ragas_scores: dict[str, float] | None = None

    @property
    def passed(self) -> bool:
        deterministic_passed = all(score >= 1.0 for score in self.deterministic_scores.values())
        judge_passed = True
        if self.judge_scores and "passed" in self.judge_scores:
            judge_passed = bool(self.judge_scores["passed"])
        return deterministic_passed and judge_passed
