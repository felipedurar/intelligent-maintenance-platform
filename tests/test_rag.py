from rag.chunking import load_document_chunks
from rag.retriever import RagRetriever


class FakeEmbeddingService:
    def embed_query(self, query: str):
        assert query
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def search(self, vector, limit=5):
        assert vector == [0.1, 0.2, 0.3]
        assert limit == 2
        return [
            type(
                "Hit",
                (),
                {
                    "text": "Predictive maintenance model documentation",
                    "source": "docs/predictive-maintenance-model.md",
                    "score": 0.91,
                    "metadata": {"chunk_id": "x:0"},
                },
            )()
        ]


def test_load_document_chunks_reads_markdown_files(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "model.md").write_text("# Model\n\nThis is a predictive model.", encoding="utf-8")

    chunks = load_document_chunks(["docs"], base_dir=tmp_path, max_chars=80)

    assert len(chunks) == 1
    assert chunks[0].source == "docs/model.md"
    assert "predictive model" in chunks[0].text


def test_rag_retriever_returns_vector_store_hits() -> None:
    retriever = RagRetriever(
        embedding_service=FakeEmbeddingService(),
        vector_store=FakeVectorStore(),
    )

    result = retriever.search("What model is used?", limit=2)

    assert result["status"] == "ok"
    assert result["results"][0]["source"] == "docs/predictive-maintenance-model.md"
