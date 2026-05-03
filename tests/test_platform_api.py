from fastapi.testclient import TestClient

from agent.orchestrator import get_agent_orchestrator
from model_serving.service import get_model_serving_service
from platform_api.main import create_app
from platform_api.routes import models
from rag.retriever import get_rag_retriever


class FakePredictionService:
    def predict_failure(self, observation, request_id=None):
        return {
            "status": "ok",
            "failure_probability": 0.42,
            "risk_class": "medium",
            "model_version": "unit-test",
            "message": "fake prediction",
            "metadata": {"request_id": request_id, "received_observation": observation},
        }


class FakeMlflowClient:
    def __init__(self, tracking_uri=None):
        self.tracking_uri = tracking_uri

    def get_model_version_by_alias(self, model_name, alias):
        return type("ModelVersion", (), {"version": "7"})()


class FakeRagRetriever:
    def search(self, query, limit=5):
        return {
            "query": query,
            "status": "ok",
            "results": [
                {
                    "text": "The model uses engineered AI4I process features.",
                    "source": "docs/predictive-maintenance-model.md",
                    "score": 0.9,
                    "metadata": {"chunk_id": "docs/predictive-maintenance-model.md:0"},
                }
            ],
            "message": "Found 1 documentation chunk.",
        }


class FakeAgentOrchestrator:
    def answer(self, message, session_id=None):
        return {
            "answer": f"answered: {message}",
            "tool_calls": ["search_project_docs"],
            "sources": ["docs/predictive-maintenance-model.md"],
            "metadata": {"session_id": session_id},
        }


def test_health_endpoint() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predictions_endpoint_uses_serving_dependency_override() -> None:
    app = create_app()
    app.dependency_overrides[get_model_serving_service] = lambda: FakePredictionService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/predictions",
        json={
            "request_id": "api-unit-test",
            "observation": {
                "product_type": "L",
                "air_temperature_k": 298.1,
                "process_temperature_k": 308.6,
                "rotational_speed_rpm": 1551,
                "torque_nm": 42.8,
                "tool_wear_min": 108,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["failure_probability"] == 0.42
    assert response.json()["model_version"] == "unit-test"


def test_predictions_endpoint_rejects_invalid_product_type() -> None:
    app = create_app()
    app.dependency_overrides[get_model_serving_service] = lambda: FakePredictionService()
    client = TestClient(app)

    response = client.post(
        "/api/v1/predictions",
        json={
            "request_id": "api-invalid-test",
            "observation": {
                "product_type": "X",
                "air_temperature_k": 298.1,
                "process_temperature_k": 308.6,
                "rotational_speed_rpm": 1551,
                "torque_nm": 42.8,
                "tool_wear_min": 108,
            },
        },
    )

    assert response.status_code == 422


def test_active_model_endpoint_reads_mlflow_alias(monkeypatch) -> None:
    monkeypatch.setattr(models, "MlflowClient", FakeMlflowClient)
    app = create_app()
    client = TestClient(app)

    response = client.get("/api/v1/models/ai4i-machine-failure-classifier/active")

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    assert response.json()["model_version"] == "7"


def test_rag_search_endpoint_uses_retriever_override() -> None:
    app = create_app()
    app.dependency_overrides[get_rag_retriever] = lambda: FakeRagRetriever()
    client = TestClient(app)

    response = client.post("/api/v1/rag/search", json={"query": "features", "limit": 3})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["results"][0]["source"] == "docs/predictive-maintenance-model.md"


def test_chat_endpoint_uses_agent_override() -> None:
    app = create_app()
    app.dependency_overrides[get_agent_orchestrator] = lambda: FakeAgentOrchestrator()
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={"message": "What features are used?", "session_id": "unit-chat"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "answered: What features are used?"
    assert response.json()["tool_calls"] == ["search_project_docs"]
