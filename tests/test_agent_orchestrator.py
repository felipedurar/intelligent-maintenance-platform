from agent.orchestrator import AgentOrchestrator


class FakeRagRetriever:
    def search(self, query, limit=3):
        return {
            "status": "ok",
            "results": [
                {
                    "text": "The platform uses a predictive-maintenance classifier.",
                    "source": "docs/predictive-maintenance-model.md",
                    "score": 0.9,
                }
            ],
            "message": "Found 1 chunk.",
        }


def test_agent_fallback_uses_rag_when_openai_key_is_missing(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("agent.orchestrator.get_rag_retriever", lambda: FakeRagRetriever())

    result = AgentOrchestrator().answer("What model is used?", session_id="test")

    assert result["metadata"]["status"] == "missing_openai_api_key"
    assert result["tool_calls"] == ["search_project_docs"]
    assert result["sources"] == ["docs/predictive-maintenance-model.md"]
