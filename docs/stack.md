# Stack

This stack is chosen to meet the Datathon requirements for a cloud predictive-maintenance platform.

## Application

| Technology | Role | Reason |
| --- | --- | --- |
| FastAPI | API services | Typed, simple, OpenAPI support, good for chat/prediction endpoints. |
| Pydantic | Schemas | Strong request/response and dataset validation contracts. |
| pandas/numpy | Data processing | CSV ingestion, feature engineering, and dataset preparation. |
| pandera or Great Expectations | Data validation | Schema and quality checks for AI4I CSV batches. |
| scikit-learn | Baseline/challenger models | Strong tabular ML toolkit for predictive maintenance. |
| PyTorch | Optional neural baseline | Useful if a PyTorch component is needed for Datathon coverage. |

## MLOps

| Technology | Role | Reason |
| --- | --- | --- |
| MLflow | Experiments and model registry | Required maturity: params, metrics, artifacts, registry, lineage. |
| DVC | Data versioning | Reproducible raw, processed, golden, and reference datasets. |
| Cloud object storage | Artifacts and DVC remote | Use S3, GCS, Azure Blob, or equivalent for MLflow artifacts, reports, and data versions. |
| PostgreSQL | Curated records and features | Stores AI4I rows, engineered features, prediction logs, and metadata. |
| Prefect | Orchestration | Python-native jobs for ingestion, feature builds, training, drift, RAG indexing, and evaluation. |
| Separate API/worker images | Runtime isolation | Keeps online serving and offline workflows separated while sharing one repository. |

## AI Assistant

| Technology | Role | Reason |
| --- | --- | --- |
| OpenAI Responses API | LLM and agent loop | Supports model responses, tool calling, and agent-like workflows through API. |
| OpenAI Agents SDK | Optional agent framework | Useful if the project wants structured tools, handoffs, and traces. |
| OpenAI embeddings | Embeddings | Converts docs and queries into vectors for custom RAG. |
| Qdrant or managed vector DB | Retrieval | Stores documentation chunks and metadata for RAG search. |
| LangChain or LlamaIndex | Optional RAG helper | Useful for document loading, chunking, and retrieval abstractions. |
| Langfuse or TruLens | LLM observability | Traces prompts, retrieval, tool calls, and generated answers. |

## Observability and Security

| Technology | Role | Reason |
| --- | --- | --- |
| Prometheus or cloud metrics | Metrics | Operational metrics collection. |
| Grafana or cloud dashboards | Dashboards | Clear Datathon demo surface. |
| Evidently | Drift detection | Feature, target, prediction, and performance drift reports. |
| Cloud IAM/OIDC | Authentication | Managed identity, roles, and access control. |
| API Gateway | Routing/security | TLS, routing, rate limits, request logging. |
| Presidio | PII detection | LGPD support if user-entered data is introduced. |
| Cloud secret manager | Secrets | Keeps API keys and credentials out of code. |

## Recommended MVP Stack

For the first runnable version:

```text
FastAPI
OpenAI Responses API
OpenAI embeddings
scikit-learn
MLflow
PostgreSQL
Cloud object storage
DVC
Prefect
Qdrant
Prometheus/Grafana or cloud metrics
Evidently
pandera
```

Recommended first model path:

```text
Logistic Regression baseline: implemented
Random Forest challenger: implemented
Optional PyTorch MLP
```
