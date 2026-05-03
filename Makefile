SHELL := /bin/bash

PYTHON ?= python
PIP ?= $(PYTHON) -m pip
DOCKER_COMPOSE ?= docker compose
API_SERVICE ?= platform_api
WORKER_SERVICE ?= prefect-worker
API_BASE_URL ?= http://localhost:8080

.PHONY: help install-dev install-eval install-torch-cpu pre-commit-install pre-commit-run format lint type security test quality coverage docker-config build up down logs ps shell-api shell-worker ingest train rag-index drift agent-eval security-eval prediction-smoke clean

help: ## Show available commands
	@awk 'BEGIN {FS = ":.*##"; printf "\nDatathon AI Platform commands:\n\n"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-24s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install-dev: ## Install project with development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

install-eval: ## Install optional RAGAS/evaluation dependencies
	$(PIP) install -e ".[eval]"

install-torch-cpu: ## Install CPU-only PyTorch for local MLP training
	$(PIP) install "torch>=2.4.0,<3.0.0" --index-url https://download.pytorch.org/whl/cpu

pre-commit-install: ## Install Git pre-commit hooks
	pre-commit install
	pre-commit install --hook-type pre-push

pre-commit-run: ## Run all pre-commit hooks against the repository
	pre-commit run --all-files

format: ## Format code with Ruff
	ruff format src tests evaluation
	ruff check src tests evaluation --fix

lint: ## Run Ruff lint checks
	ruff check src tests evaluation

type: ## Run mypy type checks
	mypy src

security: ## Run Bandit security scan
	bandit -r src -c pyproject.toml

test: ## Run unit tests
	pytest tests

coverage: ## Run tests with coverage gate
	pytest tests --cov=src --cov-report=term-missing --cov-report=xml

quality: lint type security coverage ## Run the same core quality gates used by CI

docker-config: ## Validate Docker Compose configuration
	$(DOCKER_COMPOSE) config

build: ## Build local Docker images
	$(DOCKER_COMPOSE) build $(API_SERVICE) $(WORKER_SERVICE) mlflow

up: ## Start the full local stack
	$(DOCKER_COMPOSE) up -d --build

down: ## Stop the local stack
	$(DOCKER_COMPOSE) down

logs: ## Follow Docker Compose logs
	$(DOCKER_COMPOSE) logs -f

ps: ## Show Docker Compose service status
	$(DOCKER_COMPOSE) ps

shell-api: ## Open a shell in the API container
	$(DOCKER_COMPOSE) exec $(API_SERVICE) sh

shell-worker: ## Open a shell in the Prefect worker container
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) sh

ingest: ## Run initial AI4I ingestion directly
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) ./scripts/run_initial_ingestion.sh

train: ## Run model training directly
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) ./scripts/run_training.sh

rag-index: ## Run RAG indexing directly
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) ./scripts/run_rag_indexing.sh

drift: ## Run PSI drift detection directly
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) ./scripts/run_drift_detection.sh

agent-eval: ## Run golden-set agent evaluation
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) ./scripts/run_agent_evaluation.sh

security-eval: ## Run deterministic security guardrail evaluation
	$(DOCKER_COMPOSE) exec $(WORKER_SERVICE) ./scripts/run_security_evaluation.sh

prediction-smoke: ## Run live prediction smoke checks
	API_BASE_URL=$(API_BASE_URL) ./evaluation/run_prediction_smoke.sh

clean: ## Remove local Python caches
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -prune -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -prune -exec rm -rf {} +
