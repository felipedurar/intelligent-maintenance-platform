# System Card

## System Overview

The Datathon AI Platform is a predictive-maintenance decision-support system for industrial
machines. It uses the AI4I 2020 Predictive Maintenance Dataset to estimate machine-failure
risk, explain relevant model signals, monitor drift, and answer project questions through an
OpenAI-powered assistant with RAG over project documentation.

This system is a Datathon prototype. It is designed to demonstrate MLOps, LLMOps, governance,
monitoring, and security controls. It is not approved for autonomous industrial control.

## Intended Users

- Maintenance analysts reviewing machine-failure risk.
- Data scientists comparing model candidates and evaluation reports.
- MLOps engineers operating ingestion, training, promotion, monitoring, and deployment flows.
- Datathon evaluators reviewing architecture, safety, and governance evidence.

## Intended Use

- Predict failure probability for one machine observation.
- Explain model and feature behavior in operational language.
- Retrieve architecture, model, security, LGPD, and deployment documentation through RAG.
- Monitor operational metrics and PSI-based feature drift.
- Govern model promotion through MLflow candidate/champion aliases and human approval.

## Non-Use

- Do not use the system to automatically stop or restart industrial equipment.
- Do not use the system as the only source of maintenance decisions.
- Do not use the assistant for medical, legal, financial, phishing, malware, or unrelated tasks.
- Do not treat AI4I results as validated performance for a real factory without local data
  validation, calibration, and safety review.

## Components

| Component | Purpose | Runtime |
|---|---|---|
| FastAPI Platform API | Chat, prediction, RAG search, model metadata, monitoring routes | `Dockerfile.api` |
| Prefect Worker | Ingestion, feature build, training, RAG indexing, drift, evaluation jobs | `Dockerfile.worker` |
| PostgreSQL | Curated raw records, feature tables, Prefect metadata, MLflow metadata | Docker Compose / AWS |
| MLflow | Experiment tracking, model artifacts, registry aliases | `Dockerfile.mlflow` |
| Qdrant | Vector database for documentation retrieval | Docker Compose / cloud service |
| OpenAI API | LLM chat, tool calling, embeddings | Managed API |
| Prometheus | API and custom metric scraping | Docker Compose / cloud |
| Grafana | Observability dashboard | Docker Compose / cloud |

## API Surface

Primary routes:

- `GET /api/v1/health`
- `GET /api/v1/ready`
- `POST /api/v1/chat`
- `POST /api/v1/predictions`
- `GET /api/v1/models/{model_name}/active`
- `POST /api/v1/rag/search`
- `GET /api/v1/monitoring/status`
- `GET /metrics`

OpenAPI documentation is exposed at `/api/v1/docs`.

## Agent Tools

The assistant uses OpenAI tool calling with a constrained tool set:

- `search_project_docs`: retrieves relevant chunks from project and governance docs.
- `get_active_model`: checks MLflow champion metadata.
- `predict_machine_failure`: calls the model-serving path for a machine observation.

The agent is scoped to predictive maintenance, the AI4I dataset, model operations, RAG,
monitoring, deployment, and governance.

## Model Lifecycle

The lifecycle is:

```text
CSV/DVC data -> ingestion -> feature engineering -> training -> MLflow candidate
-> benchmark/fairness evidence -> human approval -> champion alias -> serving
```

Training registers the best model as `candidate` with `approval_status=pending`. Production
serving only loads the MLflow `champion` alias. Promotion requires an explicit reviewer and
reason through `scripts/promote_model.sh`.

Rollback is supported by preserving the previous production version as the
`previous_champion` alias.

## Monitoring

Operational monitoring:

- Prometheus metrics exposed by FastAPI at `/metrics`.
- Grafana dashboard for API latency, prediction volume, chat latency, error counters, and
  guardrail events.

Model and data monitoring:

- PSI-based drift reports in `reports/drift/`.
- Drift summaries exposed through `/api/v1/monitoring/status`.
- Benchmark report in `evaluation/reports/model_benchmark_latest.md`.
- Explainability/fairness report in `evaluation/reports/explainability_fairness_latest.md`.

LLM and agent evaluation:

- Golden set: `data/golden_set/agent_eval.jsonl`.
- Agent evaluation script: `evaluation/agent_eval.py`.
- Optional RAGAS and LLM-as-judge paths are implemented, but must be run with the required
  optional dependencies and OpenAI key to produce final scored evidence.

## Security Controls

- Input guardrails block prompt injection, secret extraction, unsafe topics, and off-topic
  requests.
- Output guardrails redact token-like secrets, database URLs, internal prompt leakage, and
  unsafe automation claims.
- Tool schemas constrain model-tool inputs.
- Security tests are stored in `data/golden_set/security_eval.jsonl`.
- Latest security report: `evaluation/reports/security_eval_latest.json`.
- Latest security result: 5/5 scenarios passed on 2026-05-03.

## Human Oversight

Human review is required for:

- Champion model promotion.
- Interpreting failure-risk predictions.
- Any maintenance action or operational intervention.
- Production readiness decisions for real industrial deployment.

The platform explicitly positions model output as decision support, not an automated
maintenance command.

## Known Limitations

- AI4I is synthetic and may not represent a real plant, machine fleet, or sensor profile.
- RAG quality depends on indexed project documentation and golden-set coverage.
- OpenAI is a managed service dependency. The application does not control model quantization.
- Authentication and RBAC are documented for cloud deployment but are not fully enforced in the
  local Docker Compose prototype.
- Real production use would require industrial validation, threshold calibration, SRE runbooks,
  incident response ownership, and environment-specific access policies.

## Evidence

- Architecture: `docs/architecture.md`
- Stack: `docs/stack.md`
- Model card: `docs_governance/MODEL_CARD.md`
- LGPD plan: `docs_governance/LGPD_PLAN.md`
- OWASP mapping: `docs_governance/OWASP_MAPPING.md`
- Red-team report: `docs_governance/RED_TEAM_REPORT.md`
- Benchmark: `evaluation/reports/model_benchmark_latest.md`
- Explainability/fairness: `evaluation/reports/explainability_fairness_latest.md`
- Security evaluation: `evaluation/reports/security_eval_latest.json`
