# Deploy

Este documento descreve como o projeto pode ser executado localmente e como a infraestrutura em nuvem foi organizada para deploy na AWS.

Ele foi atualizado para refletir o estado atual do projeto, que hoje já possui:

- API FastAPI;
- worker separado para jobs offline;
- MLflow;
- PostgreSQL;
- Qdrant;
- Prefect;
- Prometheus e Grafana;
- workflows de CI/CD;
- templates CloudFormation.

## Execução Local

### Pré-requisitos

Para rodar o projeto localmente, você precisa de:

- Docker e Docker Compose;
- Python 3.12, caso queira rodar ferramentas locais fora dos containers;
- arquivo `.env` configurado a partir do `.env.example`.

Se quiser usar chat, embeddings, RAGAS ou LLM-as-judge, também será necessário configurar:

```text
OPENAI_API_KEY
```

### Subindo o ambiente

O jeito mais simples de iniciar tudo é:

```bash
docker compose up --build
```

Serviços expostos localmente:

```text
Frontend:         http://localhost:5173
API:              http://localhost:8080
Swagger:          http://localhost:8080/api/v1/docs
Prefect:          http://localhost:4200
MLflow:           http://localhost:5000
Qdrant:           http://localhost:6333
Prometheus:       http://localhost:9090
Grafana:          http://localhost:3000
PostgreSQL:       localhost:5433
```

### Bancos auxiliares

No ambiente local, o mesmo container do PostgreSQL hospeda três bancos:

- `datathon`
- `prefect`
- `mlflow`

O serviço `postgres-init` cria os bancos auxiliares quando necessário.

### Serviços do Docker Compose

O `docker-compose.yml` atual já contempla:

- `frontend`
- `platform_api`
- `postgres`
- `postgres-init`
- `prefect-server`
- `prefect-worker`
- `prefect-deployments`
- `mlflow`
- `qdrant`
- `prometheus`
- `grafana`

Isso permite demonstrar a plataforma de ponta a ponta em ambiente local, com pouca fricção.

## Inicialização da Plataforma

### Deployments do Prefect

Após subir o ambiente, os deployments do Prefect devem ser registrados automaticamente pelo serviço `prefect-deployments`.

Deployments esperados:

```text
ingest-initial-ai4i-dataset/initial-ai4i-dataset
ingest-incoming-ai4i-batches/incoming-ai4i-batches
train-ai4i-failure-classifier/train-ai4i-failure-classifier
index-rag-documentation/index-rag-documentation
detect-ai4i-drift/detect-ai4i-drift
```

Se precisar registrar manualmente:

```bash
docker compose run --rm prefect-deployments
```

### Ingestão inicial

Para carregar o dataset base:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion_deployment.sh
```

Ou diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion.sh
```

### Treinamento

Para disparar o treinamento:

```bash
docker compose exec prefect-worker ./scripts/run_training_deployment.sh
```

Ou diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_training.sh
```

### Indexação RAG

Para indexar a documentação:

```bash
docker compose exec prefect-worker ./scripts/run_rag_indexing_deployment.sh
```

Ou diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_rag_indexing.sh
```

### Drift

Para rodar a detecção de drift:

```bash
docker compose exec prefect-worker ./scripts/run_drift_detection_deployment.sh
```

Ou diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_drift_detection.sh
```

## Fluxo de Deploy Local

O fluxo esperado para preparar a plataforma em ambiente local é:

1. subir os serviços com `docker compose up --build`;
2. verificar se os deployments do Prefect apareceram;
3. rodar a ingestão inicial;
4. rodar o treinamento;
5. promover manualmente um candidato para `champion`, se necessário;
6. rodar a indexação RAG;
7. validar API, chat, métricas e dashboards.

## Promoção Manual do Modelo

O projeto não promove modelos automaticamente após o treinamento.

Depois de gerar benchmark, fairness e demais evidências, a promoção pode ser feita assim:

```bash
docker compose exec prefect-worker ./scripts/promote_model.sh \
  --approved-by "felipe" \
  --reason "Modelo aprovado após revisão de benchmark e fairness"
```

Isso garante um passo explícito de governança antes de servir o novo modelo em produção.

## Upload de Novos Datasets

O jeito mais adequado de inserir novos dados no fluxo da plataforma é via API:

```bash
curl -X POST "http://localhost:8080/api/v1/datasets/upload" \
  -F "file=@data/incoming/example_batch.csv" \
  -F "trigger_ingestion=true"
```

Esse endpoint:

- valida o CSV;
- salva o arquivo em `data/incoming/`;
- registra metadados do upload;
- pode disparar o deployment de ingestão.

Importante: upload de dataset não implica retreinamento ou promoção automática.

## Qualidade e CI/CD

### CI

O projeto possui workflow de CI com GitHub Actions para:

- `ruff`;
- `mypy`;
- `bandit`;
- `pytest` com cobertura;
- validação de build das imagens Docker.

### Avaliações LLM

Há um workflow separado para avaliação LLM, voltado para os casos em que o projeto precisa rodar:

- agent evaluation;
- RAGAS;
- LLM-as-judge.

Como essas avaliações dependem de chave da OpenAI e de custo externo, elas ficam separadas do pipeline básico de CI.

### Deploy

O workflow de deploy está preparado para ambiente AWS usando:

- GitHub Actions;
- OIDC;
- ECR;
- ECS/Fargate;
- CloudFormation.

Isso evita o uso de chaves AWS permanentes no repositório.

## Infraestrutura AWS

### Organização dos stacks

Os templates de infraestrutura estão em:

- [01-network.yml](/home/felipe_malaquias/Repositories/FIAP-5/datathon-ai-platform/infra/cloudformation/01-network.yml)
- [02-storage.yml](/home/felipe_malaquias/Repositories/FIAP-5/datathon-ai-platform/infra/cloudformation/02-storage.yml)
- [03-ecr.yml](/home/felipe_malaquias/Repositories/FIAP-5/datathon-ai-platform/infra/cloudformation/03-ecr.yml)
- [04-ecs.yml](/home/felipe_malaquias/Repositories/FIAP-5/datathon-ai-platform/infra/cloudformation/04-ecs.yml)

A ordem de deploy dos stacks é:

```text
rede -> storage -> ECR/OIDC -> ECS
```

### O que a infraestrutura cobre

A infraestrutura foi preparada para hospedar:

- API pública;
- worker do Prefect;
- PostgreSQL;
- MLflow;
- Prefect server;
- Qdrant;
- Prometheus;
- Grafana;
- buckets S3;
- ECR;
- secrets;
- roles de deploy.

### Ponto importante sobre a nuvem

Apesar de a OpenAI ser um serviço gerenciado, o restante da plataforma foi pensado para ser relativamente portátil. Ou seja: a base operacional principal continua rodando em componentes padrão de mercado, sem depender de um stack excessivamente fechado.

## Estratégia de Imagens

As imagens foram separadas por responsabilidade:

- `Dockerfile.api`: runtime online;
- `Dockerfile.worker`: jobs offline;
- `Dockerfile.mlflow`: registry e tracking;
- `Dockerfile.prometheus`: monitoramento;
- `Dockerfile.grafana`: visualização.

Essa separação é importante porque:

- reduz acoplamento entre serving e processamento;
- deixa a arquitetura mais defensável;
- evita inflar a imagem da API com dependências de treinamento;
- melhora a clareza operacional.

## Observações Operacionais

### Segredos

Segredos como `OPENAI_API_KEY`, senhas de banco e credenciais de nuvem não devem ficar em arquivos versionados. Localmente eles ficam no `.env`; em cloud, devem ficar em secret managers ou secrets do pipeline.

### Estado da plataforma

Para uma demonstração completa, o ideal é garantir estes pontos antes da apresentação:

1. dataset inicial ingerido;
2. modelo `champion` disponível no MLflow;
3. Qdrant indexado;
4. relatório de drift disponível;
5. Prometheus e Grafana funcionando;
6. chat com chave da OpenAI configurada.

## Resumo

Hoje a plataforma já possui um caminho de deploy bem definido:

- localmente com Docker Compose, pronto para demonstração;
- em nuvem com AWS, usando infraestrutura declarativa e pipeline de deploy.

Essa combinação ajuda bastante porque dá velocidade para desenvolvimento local e, ao mesmo tempo, mostra uma arquitetura séria o bastante para um cenário mais próximo de produção.
