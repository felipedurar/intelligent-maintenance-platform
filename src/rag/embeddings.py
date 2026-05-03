from __future__ import annotations

import os

from openai import OpenAI

from rag.config import embedding_model


class EmbeddingService:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or embedding_model()
        self._client: OpenAI | None = None

    @property
    def client(self) -> OpenAI:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for RAG embeddings.")
        if self._client is None:
            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]
