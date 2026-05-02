OPENAPI_TAGS = [
    {
        "name": "Health",
        "description": "Liveness and readiness checks for the platform API.",
    },
    {
        "name": "Chat",
        "description": "OpenAI-powered assistant endpoint for predictive-maintenance questions.",
    },
    {
        "name": "Predictions",
        "description": "Machine-failure risk prediction from process and sensor observations.",
    },
    {
        "name": "Machines",
        "description": "Dataset and machine/process data endpoints.",
    },
    {
        "name": "Models",
        "description": "Model registry and active/champion model metadata.",
    },
    {
        "name": "RAG",
        "description": "Documentation retrieval endpoints used by the assistant and evaluations.",
    },
    {
        "name": "Monitoring",
        "description": "Operational, model, and drift monitoring endpoints.",
    },
]

API_DESCRIPTION = """
Cloud AI platform for predictive maintenance using the AI4I 2020 dataset.

The API is organized around:

- machine-failure predictions;
- an OpenAI-powered assistant with controlled tools;
- RAG over project and governance documentation;
- MLflow model metadata;
- data, drift, and operational monitoring.

The current implementation is a scaffold: endpoints are available in Swagger UI and return
placeholder responses until ingestion, feature engineering, MLflow, RAG, and OpenAI integrations
are implemented.
"""
