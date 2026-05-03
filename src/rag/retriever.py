from __future__ import annotations

from rag.embeddings import EmbeddingService
from rag.vector_store import QdrantVectorStore


class RagRetriever:
    """Retrieves relevant documentation chunks from the vector database."""

    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or QdrantVectorStore()

    def search(self, query: str, limit: int = 5) -> dict[str, object]:
        try:
            vector = self.embedding_service.embed_query(query)
            hits = self.vector_store.search(vector, limit=limit)
            return {
                "query": query,
                "status": "ok",
                "results": [
                    {
                        "text": hit.text,
                        "source": hit.source,
                        "score": hit.score,
                        "metadata": hit.metadata,
                    }
                    for hit in hits
                ],
                "message": f"Found {len(hits)} documentation chunks.",
            }
        except Exception as exc:
            return {
                "query": query,
                "status": "not_ready",
                "results": [],
                "message": f"RAG search is not ready: {exc}",
            }


def get_rag_retriever() -> RagRetriever:
    return RagRetriever()
