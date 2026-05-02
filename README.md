# Datathon AI Platform

This is the cloud AI platform for the FIAP Phase 05 Datathon.

The project now targets **predictive maintenance for industrial machines** using the **AI4I 2020 Predictive Maintenance Dataset**. The platform predicts machine failure risk, explains predictions, monitors data/model drift, and provides an OpenAI-powered assistant with RAG over project and governance documentation.

## Target Capabilities

- Binary machine-failure prediction using AI4I process/sensor data.
- Optional failure-mode diagnostics using `TWF`, `HDF`, `PWF`, `OSF`, and `RNF`.
- MLflow experiment tracking and model registry.
- DVC dataset and golden-set versioning.
- Cloud object storage for artifacts and DVC remotes.
- FastAPI serving APIs.
- AI assistant with OpenAI-powered tool calling.
- Custom or managed RAG over project and governance documentation.
- Prometheus/Grafana or cloud-native observability.
- Evidently drift detection.
- OpenAI traces, Langfuse, or TruLens tracing.
- Cloud IAM/OIDC authentication and guardrails.
- Model Card, System Card, LGPD plan, OWASP mapping, and red-team report.

## Proposed Modules

```text
src/
├── platform_api/      # Public API and route composition
├── agent/             # OpenAI agent orchestration, tools, prompts
├── rag/               # Chunking, embeddings, retrieval, generation support
├── features/          # Predictive-maintenance feature engineering
├── model_serving/     # MLflow-backed prediction service
├── training/          # MLflow-backed training pipeline
├── ingestion/         # CSV ingestion and validation
├── monitoring/        # Metrics and drift hooks
└── security/          # Guardrails, PII checks, auth helpers
```

## Data Layout

```text
data/
├── raw/             # Original AI4I CSV snapshots, tracked by DVC
├── incoming/        # New CSV batches waiting for ingestion
├── processed/       # Cleaned and feature-engineered datasets
├── reference/       # Reference data for drift detection
└── golden_set/      # RAG/agent evaluation set
```

The initial dataset is a single CSV, but the ingestion design supports future CSV batches in `data/incoming/` or cloud object storage.

## Initial API

The first implementation should expose route groups for:

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `POST /api/v1/chat`
- `POST /api/v1/predictions`
- `GET /api/v1/models/{model_name}/active`
- `POST /api/v1/rag/search`
- `GET /api/v1/monitoring/status`

The routes should be wired to placeholder modules first, then connected to OpenAI, the vector database, MLflow, PostgreSQL feature tables, and the trained predictive-maintenance model.

## Run With Docker Compose

Start the platform API, PostgreSQL, Prefect server, and Prefect worker:

```bash
docker compose up --build
```

The API and worker are separate runtime images:

- `Dockerfile.api`: online FastAPI service for chat, predictions, RAG search, and metadata.
- `Dockerfile.worker`: offline Prefect worker for ingestion, feature builds, training, drift, and RAG indexing.

Open the FastAPI docs:

```text
http://localhost:8080/api/v1/docs
```

PostgreSQL is exposed locally on port `5433` and used by the API inside Compose as:

```text
postgresql://datathon:datathon@postgres:5432/datathon
```

The same PostgreSQL service also stores Prefect server metadata in a separate `prefect` database:

```text
postgresql+asyncpg://datathon:datathon@postgres:5432/prefect
```

The `postgres-init` service creates this database automatically if it is missing, including when a previous Docker volume already exists.

Prefect UI:

```text
http://localhost:4200
```

The `prefect-deployments` service registers deployments automatically during `docker compose up`.
The worker polls the `datathon-local` work pool and picks up runs after the deployments are registered.

After startup, the Prefect UI should show these deployments:

- `ingest-initial-ai4i-dataset/initial-ai4i-dataset`
- `ingest-incoming-ai4i-batches/incoming-ai4i-batches`

If you need to register them manually, run:

```bash
docker compose run --rm prefect-deployments
```

You can trigger deployments from the UI, or run the flow directly from the worker container during development.

Trigger the registered initial ingestion deployment:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion_deployment.sh
```

Trigger the registered incoming-batch ingestion deployment:

```bash
docker compose exec prefect-worker ./scripts/run_incoming_ingestion_deployment.sh
```

Run the initial AI4I CSV ingestion directly:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion.sh
```

Run future incoming-batch ingestion directly after placing CSV files in `data/incoming/`:

```bash
docker compose exec prefect-worker ./scripts/run_incoming_ingestion.sh
```

The initial flow reads:

```text
data/raw/ai4i2020.csv
```

The incoming flow scans:

```text
data/incoming/*.csv
```

and moves processed incoming files to:

```text
data/archive/
```

## Documentation

- [Architecture](docs/architecture.md)
- [Stack](docs/stack.md)
- [Predictive Maintenance Model](docs/predictive-maintenance-model.md)

## First Implementation Milestones

1. Add AI4I CSV ingestion and schema validation.
2. Add feature engineering for process/sensor features.
3. Build a baseline classifier with MLflow logging.
4. Add model serving for failure probability and risk class.
5. Add DVC dataset versioning and reference drift dataset.
6. Add RAG indexing/search over docs and governance files.
7. Add `/api/chat` with OpenAI tool calling for prediction, model metadata, drift status, and RAG.
8. Add monitoring, drift jobs, and governance docs.
