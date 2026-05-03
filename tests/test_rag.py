from rag.chunking import load_document_chunks
from rag.indexer import RagIndexer
from rag.retriever import RagRetriever


class FakeEmbeddingService:
    def embed_query(self, query: str):
        assert query
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    collection = "unit-test-docs"

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


class FakeBatchEmbeddingService:
    def embed_texts(self, texts: list[str]):
        assert texts
        return [[0.1, 0.2, 0.3] for _ in texts]


class FakeIndexVectorStore:
    collection = "unit-test-docs"

    def __init__(self) -> None:
        self.upserted = 0

    def upsert_chunks(self, chunks, vectors):
        assert len(chunks) == len(vectors)
        self.upserted += len(chunks)
        return len(chunks)


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


def test_rag_indexer_chunks_embeds_and_upserts_markdown(tmp_path) -> None:
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "architecture.md").write_text(
        "# Architecture\n\nThe platform uses FastAPI, MLflow, Qdrant, and OpenAI.",
        encoding="utf-8",
    )
    vector_store = FakeIndexVectorStore()
    indexer = RagIndexer(
        embedding_service=FakeBatchEmbeddingService(),
        vector_store=vector_store,
    )

    result = indexer.index_paths(paths=["docs"], base_dir=tmp_path, batch_size=1)

    assert result["status"] == "indexed"
    assert result["chunk_count"] == 1
    assert result["collection"] == "unit-test-docs"
    assert vector_store.upserted == 1
