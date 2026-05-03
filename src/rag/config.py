from __future__ import annotations

import os


DEFAULT_RAG_PATHS = [
    "README.md",
    "AGENTS.md",
    "docs",
    "docs_governance",
]


def qdrant_url() -> str:
    return os.getenv("QDRANT_URL", "http://localhost:6333")


def collection_name() -> str:
    return os.getenv("RAG_COLLECTION_NAME", "datathon_docs")


def embedding_model() -> str:
    return os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def embedding_dimensions() -> int:
    return int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", "1536"))
