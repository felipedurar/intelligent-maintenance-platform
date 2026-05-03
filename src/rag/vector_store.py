from __future__ import annotations

import uuid
from dataclasses import dataclass

from qdrant_client import QdrantClient
from qdrant_client.http import models

from rag.chunking import DocumentChunk
from rag.config import collection_name, embedding_dimensions, qdrant_url


@dataclass(frozen=True)
class RagSearchHit:
    text: str
    source: str
    score: float
    metadata: dict[str, object]


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


class QdrantVectorStore:
    def __init__(
        self,
        url: str | None = None,
        collection: str | None = None,
        dimensions: int | None = None,
    ) -> None:
        self.url = url or qdrant_url()
        self.collection = collection or collection_name()
        self.dimensions = dimensions or embedding_dimensions()
        self.client = QdrantClient(url=self.url)

    def ensure_collection(self) -> None:
        existing = {collection.name for collection in self.client.get_collections().collections}
        if self.collection in existing:
            return
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=self.dimensions,
                distance=models.Distance.COSINE,
            ),
        )

    def upsert_chunks(self, chunks: list[DocumentChunk], vectors: list[list[float]]) -> int:
        self.ensure_collection()
        points = [
            models.PointStruct(
                id=point_id(chunk.id),
                vector=vector,
                payload={
                    "chunk_id": chunk.id,
                    "source": chunk.source,
                    "chunk_index": chunk.chunk_index,
                    "text": chunk.text,
                },
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        ]
        if not points:
            return 0
        self.client.upsert(collection_name=self.collection, points=points)
        return len(points)

    def search(self, vector: list[float], limit: int = 5) -> list[RagSearchHit]:
        self.ensure_collection()
        results = self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )
        hits: list[RagSearchHit] = []
        for result in results:
            payload = result.payload or {}
            hits.append(
                RagSearchHit(
                    text=str(payload.get("text", "")),
                    source=str(payload.get("source", "")),
                    score=float(result.score),
                    metadata={
                        "chunk_id": payload.get("chunk_id"),
                        "chunk_index": payload.get("chunk_index"),
                    },
                )
            )
        return hits
