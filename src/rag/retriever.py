class RagRetriever:
    """Retrieves relevant documentation chunks from the vector database."""

    def search(self, query: str, limit: int = 5) -> dict[str, object]:
        return {
            "query": query,
            "status": "not_indexed",
            "results": [],
            "message": (
                "RAG retrieval is ready to be implemented. "
                "The next step is adding chunking, embeddings, and vector database integration."
            ),
        }


def get_rag_retriever() -> RagRetriever:
    return RagRetriever()
