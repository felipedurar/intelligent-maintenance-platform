# Datathon AI Platform

This is the cloud AI platform for the FIAP Phase 05 Datathon.

The project now targets **predictive maintenance for industrial machines** using the **AI4I 2020 Predictive Maintenance Dataset**. The platform predicts machine failure risk, explains predictions, monitors data/model drift, and provides an OpenAI-powered assistant with RAG over project and governance documentation.

## Target Capabilities

- Binary machine-failure prediction using AI4I process/sensor data.
- Optional failure-mode diagnostics using `TWF`, `HDF`, `PWF`, `OSF`, and `RNF`.
- MLflow experiment tracking and model registry.
- Qdrant-backed RAG over project and governance documentation.
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

Start the platform API, PostgreSQL, MLflow, Prefect server, and Prefect worker:

```bash
docker compose up --build
```

Common development shortcuts are available through `make`:

```bash
make help
make install-dev
make pre-commit-install
make quality
make up
make train
make agent-eval
make security-eval
```

The repository also includes `.pre-commit-config.yaml` with file hygiene checks, Ruff
format/lint, mypy, Bandit, and a pre-push pytest hook.

PyTorch is used by the offline training worker for the MLP challenger. It is intentionally not
installed in the online API image. For local MLP training outside Docker, install the CPU build:

```bash
make install-torch-cpu
```

The API and worker are separate runtime images:

- `Dockerfile.api`: online FastAPI service for chat, predictions, RAG search, and metadata.
- `Dockerfile.worker`: offline Prefect worker for ingestion, feature builds, training, drift, and RAG indexing.
- `Dockerfile.mlflow`: MLflow tracking server and model registry runtime.

Qdrant UI/API:

```text
http://localhost:6333
```

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

The same PostgreSQL service also stores MLflow metadata in a separate `mlflow` database:

```text
postgresql+psycopg2://datathon:datathon@postgres:5432/mlflow
```

The `postgres-init` service creates these databases automatically if they are missing, including when a previous Docker volume already exists.

MLflow UI:

```text
http://localhost:5000
```

Prefect UI:

```text
http://localhost:4200
```

Prometheus UI:

```text
http://localhost:9090
```

Grafana UI:

```text
http://localhost:3000
```

Grafana is provisioned with the Prometheus datasource and a `Datathon Platform Observability`
dashboard. The platform API exposes Prometheus metrics at:

```text
http://localhost:8080/metrics
```

The `prefect-deployments` service registers deployments automatically during `docker compose up`.
The worker polls the `datathon-local` work pool and picks up runs after the deployments are registered.

After startup, the Prefect UI should show these deployments:

- `ingest-initial-ai4i-dataset/initial-ai4i-dataset`
- `ingest-incoming-ai4i-batches/incoming-ai4i-batches`
- `train-ai4i-failure-classifier/train-ai4i-failure-classifier`
- `index-rag-documentation/index-rag-documentation`
- `detect-ai4i-drift/detect-ai4i-drift`

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

Trigger the registered training deployment:

```bash
docker compose exec prefect-worker ./scripts/run_training_deployment.sh
```

Trigger the registered RAG indexing deployment:

```bash
docker compose exec prefect-worker ./scripts/run_rag_indexing_deployment.sh
```

Trigger the registered PSI drift detection deployment:

```bash
docker compose exec prefect-worker ./scripts/run_drift_detection_deployment.sh
```

Run the initial AI4I CSV ingestion directly:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion.sh
```

Run future incoming-batch ingestion directly after placing CSV files in `data/incoming/`:

```bash
docker compose exec prefect-worker ./scripts/run_incoming_ingestion.sh
```

Run the training pipeline directly after ingestion:

```bash
docker compose exec prefect-worker ./scripts/run_training.sh
```

Run RAG indexing directly after setting `OPENAI_API_KEY`:

```bash
docker compose exec prefect-worker ./scripts/run_rag_indexing.sh
```

Run the golden-set agent evaluation with deterministic checks:

```bash
docker compose exec prefect-worker ./scripts/run_agent_evaluation.sh
```

Run the deterministic security guardrail evaluation:

```bash
docker compose exec prefect-worker ./scripts/run_security_evaluation.sh
```

Enable OpenAI LLM-as-judge when `OPENAI_API_KEY` is configured:

```bash
docker compose exec prefect-worker ./scripts/run_agent_evaluation.sh --judge --mlflow
```

Enable RAGAS after installing optional evaluation dependencies:

```bash
pip install -e ".[eval]"
python -m evaluation.agent_eval --judge --ragas --mlflow
```

Run PSI drift detection directly after a processed dataset exists:

```bash
docker compose exec prefect-worker ./scripts/run_drift_detection.sh
```

The RAG pipeline chunks `README.md`, `AGENTS.md`, `docs/`, and `docs_governance/`, embeds
the chunks with OpenAI embeddings, and upserts them into Qdrant. The `/api/v1/rag/search`
endpoint queries that index. The `/api/v1/chat` endpoint uses OpenAI tool calling with these
platform tools:

- `search_project_docs`
- `get_active_model`
- `predict_machine_failure`

The chat route is protected by deterministic security guardrails before and after the agent:

- prompt-injection blocking for attempts to override instructions or reveal hidden prompts/secrets;
- topic restriction to predictive maintenance, AI4I, model operations, RAG, monitoring, deployment, and governance;
- output sanitization for API keys, JWT-like tokens, database URLs, password/token fields, internal prompt leakage, and unsafe automation claims;
- Prometheus counter `security_guardrail_events_total` for blocked and sanitized events.

The agent evaluation golden set lives at:

```text
data/golden_set/agent_eval.jsonl
```

Security adversarial examples live at:

```text
data/golden_set/security_eval.jsonl
```

It evaluates the chat agent with:

- deterministic checks for expected tool usage, retrieved source recall, and non-empty answers;
- optional OpenAI LLM-as-judge scoring for answer quality, groundedness, safety, and tool/context use;
- optional RAGAS metrics for faithfulness, answer relevancy, context precision, and context recall.

Reports are written to:

```text
evaluation/reports/agent_eval_latest.json
evaluation/reports/agent_eval_latest.md
```

Run the automated tests locally after installing dev dependencies:

```bash
pytest
```

Run live prediction smoke checks after the stack is up and the champion model exists:

```bash
./evaluation/run_prediction_smoke.sh
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

Both ingestion flows also export engineered snapshots to:

```text
data/processed/ai4i_features_<batch_id>.csv
data/processed/ai4i_features_latest.csv
```

The training pipeline reads `ai4i_machine_features` from PostgreSQL, trains a baseline logistic-regression model and a challenger random-forest model, logs metrics/artifacts to MLflow, registers the best model as `ai4i-machine-failure-classifier`, and assigns the `champion` alias. The prediction endpoint loads that MLflow champion model.

The training pipeline also trains a PyTorch MLP deep challenger when PyTorch is installed in
the training runtime. All candidates are logged through a common MLflow pyfunc serving contract
that returns `failure_probability`, so the champion model can be sklearn or PyTorch without
changing the prediction API.

The monitoring flow compares `data/reference/ai4i_reference.csv` against
`data/processed/ai4i_features_latest.csv` using PSI thresholds:

- `< 0.10`: stable
- `0.10 - 0.20`: warning
- `>= 0.20`: drift detected

If the reference file does not exist yet, the flow initializes it from the latest processed
dataset. Drift reports are written to `reports/drift/` as JSON and HTML, and summary metrics
plus artifacts are logged to MLflow.

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
