from __future__ import annotations

from rag.chunking import load_document_chunks
from rag.config import DEFAULT_RAG_PATHS
from rag.embeddings import EmbeddingService
from rag.vector_store import QdrantVectorStore


class RagIndexer:
    def __init__(
        self,
        embedding_service: EmbeddingService | None = None,
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.embedding_service = embedding_service or EmbeddingService()
        self.vector_store = vector_store or QdrantVectorStore()

    def index_paths(
        self,
        paths: list[str] | None = None,
        base_dir: str = ".",
        batch_size: int = 64,
    ) -> dict[str, object]:
        chunks = load_document_chunks(paths or DEFAULT_RAG_PATHS, base_dir=base_dir)
        indexed = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            vectors = self.embedding_service.embed_texts([chunk.text for chunk in batch])
            indexed += self.vector_store.upsert_chunks(batch, vectors)
        return {
            "status": "indexed",
            "chunk_count": indexed,
            "paths": paths or DEFAULT_RAG_PATHS,
            "collection": self.vector_store.collection,
        }
