from __future__ import annotations

from time import perf_counter

from prometheus_client import Counter, Histogram


PREDICTION_REQUESTS = Counter(
    "prediction_requests_total",
    "Total prediction requests by result status.",
    labelnames=("status",),
)
PREDICTION_ERRORS = Counter(
    "prediction_errors_total",
    "Total prediction requests that did not produce a valid score.",
)
PREDICTION_LATENCY = Histogram(
    "prediction_latency_seconds",
    "Prediction endpoint latency in seconds.",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
PREDICTION_RISK_CLASS = Counter(
    "prediction_risk_class_total",
    "Total predictions by assigned risk class.",
    labelnames=("risk_class",),
)
PREDICTION_PROBABILITY = Histogram(
    "prediction_probability",
    "Distribution of returned machine-failure probabilities.",
    buckets=(0.0, 0.05, 0.1, 0.2, 0.35, 0.5, 0.7, 0.85, 1.0),
)

CHAT_REQUESTS = Counter(
    "chat_requests_total",
    "Total assistant chat requests by result status.",
    labelnames=("status",),
)
CHAT_LATENCY = Histogram(
    "chat_latency_seconds",
    "Chat endpoint latency in seconds.",
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
AGENT_TOOL_CALLS = Counter(
    "agent_tool_calls_total",
    "Total agent tool calls by tool name.",
    labelnames=("tool",),
)

RAG_SEARCH_REQUESTS = Counter(
    "rag_search_requests_total",
    "Total RAG search requests by result status.",
    labelnames=("status",),
)
RAG_SEARCH_LATENCY = Histogram(
    "rag_search_latency_seconds",
    "RAG search endpoint latency in seconds.",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def timer_start() -> float:
    return perf_counter()


def elapsed_seconds(started_at: float) -> float:
    return perf_counter() - started_at


def record_prediction(status: str, latency_seconds: float, probability: float | None, risk_class: str | None) -> None:
    PREDICTION_REQUESTS.labels(status=status).inc()
    PREDICTION_LATENCY.observe(latency_seconds)
    if status != "ok":
        PREDICTION_ERRORS.inc()
    if probability is not None:
        PREDICTION_PROBABILITY.observe(probability)
    if risk_class:
        PREDICTION_RISK_CLASS.labels(risk_class=risk_class).inc()


def record_chat(status: str, latency_seconds: float, tool_calls: list[str]) -> None:
    CHAT_REQUESTS.labels(status=status).inc()
    CHAT_LATENCY.observe(latency_seconds)
    for tool in tool_calls:
        AGENT_TOOL_CALLS.labels(tool=tool).inc()


def record_rag_search(status: str, latency_seconds: float) -> None:
    RAG_SEARCH_REQUESTS.labels(status=status).inc()
    RAG_SEARCH_LATENCY.observe(latency_seconds)
