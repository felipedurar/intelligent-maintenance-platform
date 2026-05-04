from fastapi.testclient import TestClient

from agent.orchestrator import get_agent_orchestrator
from dataset_management.management import DatasetUpload
from model_serving.service import get_model_serving_service
from platform_api.main import create_app
from platform_api.routes import datasets, models
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


class FakeDatasetManager:
    def __init__(self):
        self.status_updates = []

    def save_upload(self, filename, content):
        return DatasetUpload(
            dataset_id="dataset-123",
            original_filename=filename,
            stored_path="data/incoming/dataset-123_batch.csv",
            source_hash="abc123",
            row_count=2,
            status="uploaded",
            ingestion_recommended=True,
        )

    def mark_upload_status(self, dataset_id, status):
        self.status_updates.append((dataset_id, status))

    def list_uploads(self, limit=50):
        return [
            {
                "dataset_id": "dataset-123",
                "original_filename": "batch.csv",
                "stored_path": "data/incoming/dataset-123_batch.csv",
                "source_hash": "abc123",
                "row_count": 2,
                "status": "uploaded",
                "ingestion_recommended": True,
                "created_at": "2026-05-04T00:00:00Z",
                "updated_at": "2026-05-04T00:00:00Z",
            }
        ]

    def list_ingestion_batches(self, limit=50):
        return [
            {
                "batch_id": "incoming-abc123",
                "source_file": "data/incoming/dataset-123_batch.csv",
                "source_hash": "abc123",
                "row_count": 2,
                "status": "ingested",
                "ingested_at": "2026-05-04T00:00:00Z",
            }
        ]

    def get_ingestion_batch(self, batch_id):
        if batch_id != "incoming-abc123":
            return None
        return self.list_ingestion_batches()[0]


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


def test_dataset_upload_endpoint_stores_csv_and_triggers_ingestion(monkeypatch) -> None:
    async def fake_trigger(deployment_name):
        return {
            "status": "submitted",
            "deployment": deployment_name,
            "flow_run_id": "flow-run-123",
            "flow_run_name": "test-flow-run",
        }

    manager = FakeDatasetManager()
    monkeypatch.setattr(datasets, "trigger_prefect_deployment", fake_trigger)
    app = create_app()
    app.dependency_overrides[datasets.get_dataset_manager] = lambda: manager
    client = TestClient(app)

    csv_content = (
        "UDI,Product ID,Type,Air temperature [K],Process temperature [K],"
        "Rotational speed [rpm],Torque [Nm],Tool wear [min],Machine failure,TWF\n"
        "1,M14860,M,298.1,308.6,1551,42.8,0,0,0\n"
        "2,L47181,L,298.2,308.7,1408,46.3,3,0,0\n"
    )
    response = client.post(
        "/api/v1/datasets/upload",
        data={"trigger_ingestion": "true"},
        files={"file": ("batch.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["dataset_id"] == "dataset-123"
    assert payload["status"] == "ingestion_requested"
    assert payload["ingestion_trigger"]["flow_run_id"] == "flow-run-123"
    assert manager.status_updates == [("dataset-123", "ingestion_requested")]


def test_dataset_metadata_endpoints_use_manager_override() -> None:
    app = create_app()
    app.dependency_overrides[datasets.get_dataset_manager] = lambda: FakeDatasetManager()
    client = TestClient(app)

    uploads = client.get("/api/v1/datasets/uploads")
    batches = client.get("/api/v1/datasets/batches")
    batch = client.get("/api/v1/datasets/batches/incoming-abc123")

    assert uploads.status_code == 200
    assert uploads.json()["count"] == 1
    assert batches.status_code == 200
    assert batches.json()["results"][0]["batch_id"] == "incoming-abc123"
    assert batch.status_code == 200
    assert batch.json()["source_hash"] == "abc123"


def test_dataset_trigger_endpoints_submit_prefect_deployments(monkeypatch) -> None:
    triggered = []

    async def fake_trigger(deployment_name):
        triggered.append(deployment_name)
        return {
            "status": "submitted",
            "deployment": deployment_name,
            "flow_run_id": "flow-run-123",
            "flow_run_name": "test-flow-run",
        }

    monkeypatch.setattr(datasets, "trigger_prefect_deployment", fake_trigger)
    app = create_app()
    client = TestClient(app)

    ingest = client.post("/api/v1/datasets/ingest")
    retrain = client.post("/api/v1/datasets/retrain")

    assert ingest.status_code == 200
    assert retrain.status_code == 200
    assert triggered == [
        datasets.INCOMING_DEPLOYMENT,
        datasets.TRAINING_DEPLOYMENT,
    ]
