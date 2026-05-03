from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any


PROMPT_INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore (all )?(previous|prior|above) (instructions|rules|messages)\b",
        r"\b(disregard|override|bypass) (the )?(system|developer|security|safety) "
        r"(prompt|instructions|rules|policy)\b",
        r"\b(reveal|show|print|dump|exfiltrate|leak).{0,80}\b(system prompt|hidden "
        r"instructions|developer message|internal policy|api key|secret|token|password)\b",
        r"\byou are now (developer|system|admin|root)\b",
        r"\bdisable (all )?(tools|guardrails|safety|security|filters)\b",
        r"\bpretend (you are|to be) (the )?(system|developer|admin)\b",
    )
]

SECRET_PATTERNS = [
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[REDACTED_OPENAI_KEY]"),
    (re.compile(r"\b[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\b"), "[REDACTED_JWT]"),
    (
        re.compile(r"(postgres(?:ql)?://[^:\s/@]+:)([^@\s]+)(@)", re.IGNORECASE),
        r"\1[REDACTED]\3",
    ),
    (
        re.compile(r"((?:api[_-]?key|secret|token|password)\s*[:=]\s*)([^\s,;]+)", re.IGNORECASE),
        r"\1[REDACTED]",
    ),
]

SYSTEM_LEAK_PATTERNS = [
    re.compile(r"(?is)system prompt\s*:\s*.*"),
    re.compile(r"(?is)developer message\s*:\s*.*"),
    re.compile(r"(?is)hidden instructions\s*:\s*.*"),
]

UNSAFE_AUTOMATION_PATTERNS = [
    re.compile(
        r"\b(the )?(model|agent|platform|system)\b.{0,80}\b(automatically|directly)\b"
        r".{0,80}\b(stop|stops|shutdown|shut down|shuts down|turn off|halts?)\b"
        r".{0,40}\b(machine|equipment|asset)s?\b",
        re.IGNORECASE,
    )
]

ALLOWED_TOPIC_KEYWORDS = {
    "agent",
    "ai4i",
    "air temperature",
    "api",
    "architecture",
    "chat",
    "dataset",
    "docker",
    "drift",
    "evaluation",
    "failure",
    "feature",
    "features",
    "governance",
    "guardrail",
    "hdf",
    "industrial",
    "ingestion",
    "lgpd",
    "machine",
    "maintenance",
    "mlflow",
    "model",
    "monitoring",
    "osf",
    "postgres",
    "prediction",
    "prefect",
    "process temperature",
    "qdrant",
    "rag",
    "ragas",
    "risk",
    "rnf",
    "rotational speed",
    "sensor",
    "tool wear",
    "torque",
    "training",
    "twf",
}

ALLOWED_SMALLTALK = {
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank you",
    "ok",
    "great",
}

BLOCKED_TOPIC_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(phishing|malware|ransomware|keylogger|credential theft)\b",
        r"\b(hack|bypass auth|steal|exfiltrate)\b",
        r"\bmedical diagnosis\b",
        r"\blegal advice\b",
        r"\binvestment advice\b",
    )
]


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    category: str = "allowed"
    reason: str | None = None
    sanitized_message: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


def message_hash(message: str) -> str:
    return hashlib.sha256(message.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]


def evaluate_input(message: str) -> GuardrailDecision:
    normalized = " ".join(message.lower().split())
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(message):
            return GuardrailDecision(
                allowed=False,
                category="prompt_injection",
                reason="The message attempts to override instructions or reveal hidden information.",
                metadata={"message_hash": message_hash(message)},
            )

    for pattern in BLOCKED_TOPIC_PATTERNS:
        if pattern.search(message):
            return GuardrailDecision(
                allowed=False,
                category="blocked_topic",
                reason="The request is outside the safe operational scope of this assistant.",
                metadata={"message_hash": message_hash(message)},
            )

    if normalized not in ALLOWED_SMALLTALK and not _has_allowed_topic(normalized):
        return GuardrailDecision(
            allowed=False,
            category="topic_restriction",
            reason="The request is outside the predictive-maintenance platform scope.",
            metadata={"message_hash": message_hash(message)},
        )

    sanitized = sanitize_text(message)
    return GuardrailDecision(
        allowed=True,
        sanitized_message=sanitized,
        metadata={"sanitized_input": sanitized != message},
    )


def _has_allowed_topic(normalized_message: str) -> bool:
    for keyword in ALLOWED_TOPIC_KEYWORDS:
        if " " in keyword:
            if keyword in normalized_message:
                return True
            continue
        if re.search(rf"\b{re.escape(keyword)}\b", normalized_message):
            return True
    return False


def blocked_chat_response(decision: GuardrailDecision, session_id: str | None) -> dict[str, object]:
    if decision.category == "topic_restriction":
        answer = (
            "I am focused on this predictive-maintenance platform. I can help with the AI4I "
            "dataset, machine-failure prediction, model training, RAG, monitoring, governance, "
            "deployment, and security controls."
        )
    else:
        answer = (
            "I can help with predictive maintenance, model behavior, architecture, governance, "
            "and platform operations, but I cannot follow requests that attempt to override "
            "security rules, reveal secrets, or move outside the safe project scope."
        )
    return {
        "answer": answer,
        "tool_calls": [],
        "sources": [],
        "metadata": {
            "session_id": session_id,
            "status": "blocked",
            "guardrail": decision.category,
            "reason": decision.reason,
            **decision.metadata,
        },
    }


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern, replacement in SECRET_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    for pattern in SYSTEM_LEAK_PATTERNS:
        sanitized = pattern.sub("[REDACTED_INTERNAL_INSTRUCTIONS]", sanitized)
    for pattern in UNSAFE_AUTOMATION_PATTERNS:
        sanitized = pattern.sub(
            "The platform supports maintenance decisions; it does not automatically stop machines",
            sanitized,
        )
    return sanitized


def sanitize_output(result: dict[str, object]) -> tuple[dict[str, object], bool]:
    sanitized: dict[str, object] = {}
    changed = False
    for key, value in result.items():
        new_value = _sanitize_value(value)
        sanitized[key] = new_value
        changed = changed or new_value != value

    metadata = sanitized.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    if changed:
        metadata = {**metadata, "output_sanitized": True}
        sanitized["metadata"] = metadata
    return sanitized, changed


def _sanitize_value(value: object) -> object:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _sanitize_value(item) for key, item in value.items()}
    return value


def safe_metadata(metadata: dict[str, Any]) -> dict[str, object]:
    return {str(key): _sanitize_value(value) for key, value in metadata.items()}
