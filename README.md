# Datathon AI Platform

Plataforma de IA desenvolvida para o Datathon da Fase 05 da FIAP.

O projeto resolve um problema de manutenção preditiva em máquinas industriais usando o dataset **AI4I 2020 Predictive Maintenance Dataset**. A solução combina ingestão de dados, engenharia de features, treinamento de modelos, registro no MLflow, API de predição, monitoramento de drift e um assistente com LLM e RAG para apoiar a interpretação técnica da plataforma.

## Integrantes

- Felipe Malaquias Durar
- Everton Vieira Rodrigues

## Objetivo

O objetivo da plataforma é estimar o risco de falha de uma máquina industrial a partir de variáveis de processo, como temperatura, rotação, torque e desgaste da ferramenta.

Além da predição em si, a solução foi desenhada para cobrir o ciclo completo de MLOps:

- receber novos datasets em CSV;
- validar e ingerir os dados;
- gerar features para treinamento e inferência;
- treinar modelos baseline e challengers;
- registrar experimentos e modelos no MLflow;
- servir o modelo aprovado pela API;
- monitorar métricas operacionais e drift;
- avaliar o agente/RAG com golden set, RAGAS e LLM-as-judge;
- documentar governança, segurança, LGPD e promoção de modelos.

## Visão Geral da Arquitetura

A solução é organizada em serviços separados por responsabilidade:

- **Platform API**: aplicação FastAPI responsável por expor endpoints de predição, chat, RAG, datasets, modelos, health checks e monitoramento.
- **PostgreSQL**: banco relacional usado para armazenar dados ingeridos, features, metadados de datasets e dados de suporte da plataforma.
- **Prefect Server e Worker**: orquestração de pipelines offline, como ingestão, treinamento, indexação RAG e detecção de drift.
- **MLflow**: tracking de experimentos, versionamento e registry de modelos.
- **Qdrant**: banco vetorial usado pelo RAG.
- **Prometheus e Grafana**: coleta e visualização de métricas operacionais.
- **OpenAI**: LLM para o agente conversacional, embeddings para RAG e avaliações opcionais com LLM-as-judge/RAGAS.

O desenho evita que o upload de dados treine ou promova modelos automaticamente. Novos dados entram na plataforma, são validados e ingeridos, mas a criação de um novo modelo gera apenas um candidato. A promoção para produção exige aprovação humana.

## Estrutura Principal

```text
src/
├── platform_api/          # API pública com FastAPI
├── dataset_management/    # Upload, validação e metadados de datasets
├── ingestion/             # Ingestão de CSVs AI4I e persistência no PostgreSQL
├── features/              # Engenharia de features para manutenção preditiva
├── training/              # Treinamento, avaliação, MLflow e promoção de modelos
├── model_serving/         # Carregamento do modelo champion e predição
├── rag/                   # Chunking, embeddings, Qdrant e busca semântica
├── agent/                 # Orquestração do agente com ferramentas
├── monitoring/            # Métricas, PSI e drift
└── security/              # Guardrails de prompt, saída e restrição de tópico
```

```text
data/
├── raw/             # Dataset original versionado com DVC
├── incoming/        # Novos CSVs recebidos para ingestão
├── processed/       # Datasets processados e com features
├── reference/       # Dataset de referência para drift
├── archive/         # CSVs incoming já processados
└── golden_set/      # Casos de avaliação do agente, RAG e segurança
```

## Dataset

O projeto usa o **AI4I 2020 Predictive Maintenance Dataset**, um dataset sintético inspirado em um processo de usinagem. As principais colunas são:

- `UDI`
- `Product ID`
- `Type`
- `Air temperature [K]`
- `Process temperature [K]`
- `Rotational speed [rpm]`
- `Torque [Nm]`
- `Tool wear [min]`
- `Machine failure`
- `TWF`, `HDF`, `PWF`, `OSF`, `RNF`

A variável principal de predição é `Machine failure`. As colunas de modo de falha podem ser usadas para análise, diagnóstico e explicabilidade, mas o modelo principal prevê se haverá falha ou não.

## Engenharia de Features

A plataforma não usa apenas as colunas brutas. Durante a ingestão, são criadas features derivadas para representar melhor o comportamento físico do processo, por exemplo:

- diferença entre temperatura de processo e temperatura do ar;
- potência aproximada a partir de torque e rotação;
- indicadores de risco por desgaste de ferramenta;
- variáveis categóricas do tipo de produto;
- combinações úteis para capturar cenários de sobrecarga, dissipação térmica e esforço mecânico.

Essas features são persistidas no PostgreSQL e também exportadas para `data/processed/`, permitindo auditoria, reprodutibilidade e uso em relatórios de drift.

## Como Executar Localmente

Crie um arquivo `.env` a partir do exemplo:

```bash
cp .env.example .env
```

Se for usar chat, RAG, RAGAS ou LLM-as-judge, configure `OPENAI_API_KEY` no `.env`. Nunca commite esse arquivo.

Suba a plataforma:

```bash
docker compose up --build
```

Serviços principais:

```text
API FastAPI:      http://localhost:8080
Swagger:          http://localhost:8080/api/v1/docs
MLflow:           http://localhost:5000
Prefect:          http://localhost:4200
Qdrant:           http://localhost:6333
Prometheus:       http://localhost:9090
Grafana:          http://localhost:3000
PostgreSQL local: localhost:5433
```

Credenciais locais padrão do PostgreSQL:

```text
usuário: datathon
senha:   datathon
banco:   datathon
```

## Comandos Úteis

O projeto inclui um `Makefile` para facilitar o desenvolvimento:

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

Para treinamento local do modelo PyTorch MLP fora do Docker:

```bash
make install-torch-cpu
```

## Ingestão de Dados

O dataset inicial fica em:

```text
data/raw/ai4i2020.csv
```

A ingestão inicial pode ser executada pelo deployment do Prefect:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion_deployment.sh
```

Ou diretamente no worker:

```bash
docker compose exec prefect-worker ./scripts/run_initial_ingestion.sh
```

Para novos dados, a forma recomendada é usar a API de upload:

```bash
curl -X POST "http://localhost:8080/api/v1/datasets/upload" \
  -F "file=@data/incoming/example_batch.csv" \
  -F "trigger_ingestion=true"
```

Esse endpoint valida o schema do CSV, salva o arquivo em `data/incoming/`, registra metadados no PostgreSQL e, se solicitado, dispara o deployment de ingestão de novos lotes no Prefect.

Endpoints de gestão de datasets:

```text
POST /api/v1/datasets/upload
GET  /api/v1/datasets/uploads
GET  /api/v1/datasets/batches
GET  /api/v1/datasets/batches/{batch_id}
POST /api/v1/datasets/ingest
POST /api/v1/datasets/retrain
```

O fluxo operacional recomendado para novos dados é:

```text
upload do CSV
-> validação e armazenamento em incoming
-> ingestão pelo Prefect
-> exportação do dataset processado
-> verificação de drift
-> treinamento, se fizer sentido
-> registro de modelo candidato
-> análise de benchmark/fairness
-> aprovação humana
-> promoção para champion
```

## Treinamento e MLflow

O pipeline de treinamento lê as features do PostgreSQL, treina modelos candidatos e registra tudo no MLflow.

Modelos implementados:

- regressão logística como baseline;
- random forest e extra trees como challengers clássicos;
- MLP em PyTorch como challenger neural, quando PyTorch está disponível no worker.

O ranking prioriza **average precision**, porque falhas são eventos raros no AI4I. Também são avaliadas métricas como recall, F1, precisão, ROC AUC e matriz de confusão.

Executar treinamento pelo deployment:

```bash
docker compose exec prefect-worker ./scripts/run_training_deployment.sh
```

Executar diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_training.sh
```

O melhor modelo é registrado no MLflow como `candidate`, com `approval_status=pending`. Ele não substitui o modelo em produção automaticamente.

## Promoção de Modelo

A API de predição usa o modelo com alias `champion` no MLflow. Para promover um candidato, é necessário passar por uma etapa explícita de aprovação humana.

Exemplo:

```bash
docker compose exec prefect-worker ./scripts/promote_model.sh \
  --approved-by "felipe" \
  --reason "Benchmark e fairness revisados para a entrega do Datathon"
```

Também é possível promover uma versão específica com `--version`.

Esse processo registra informações como aprovador, data e justificativa da promoção.

## API de Predição

Endpoint principal:

```text
POST /api/v1/predictions
```

A API recebe uma observação de máquina, aplica a mesma engenharia de features usada no treinamento e retorna:

- probabilidade de falha;
- classe de risco;
- versão do modelo usado;
- metadados úteis para auditoria.

## RAG e Agente

O RAG indexa a documentação do projeto e arquivos de governança:

```text
README.md
AGENTS.md
docs/
docs_governance/
```

Rodar indexação RAG:

```bash
docker compose exec prefect-worker ./scripts/run_rag_indexing_deployment.sh
```

Ou diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_rag_indexing.sh
```

Endpoints relacionados:

```text
POST /api/v1/rag/search
POST /api/v1/chat
```

O agente usa OpenAI com tool calling. As ferramentas disponíveis permitem:

- buscar documentação do projeto;
- consultar o modelo ativo;
- executar predições de falha de máquina.

Assim, o usuário pode fazer perguntas em linguagem natural, e o agente pode combinar contexto documental com chamadas reais à API/modelo.

## Avaliação do Agente e RAGAS

O golden set do agente fica em:

```text
data/golden_set/agent_eval.jsonl
```

Rodar avaliação determinística:

```bash
docker compose exec prefect-worker ./scripts/run_agent_evaluation.sh
```

Rodar avaliação com LLM-as-judge:

```bash
docker compose exec prefect-worker ./scripts/run_agent_evaluation.sh --judge --mlflow
```

Rodar RAGAS obrigatório:

```bash
docker compose exec prefect-worker ./scripts/run_ragas_evaluation.sh --mlflow
```

A avaliação RAGAS calcula e reporta quatro métricas:

- `faithfulness`
- `answer_relevancy`
- `context_precision`
- `context_recall`

O workflow `LLM Evaluation` no GitHub Actions também pode executar essa avaliação quando o secret `OPENAI_API_KEY` estiver configurado.

## Monitoramento e Drift

A API expõe métricas Prometheus em:

```text
http://localhost:8080/metrics
```

O Grafana já é provisionado com datasource do Prometheus e dashboard da plataforma.

Rodar detecção de drift:

```bash
docker compose exec prefect-worker ./scripts/run_drift_detection_deployment.sh
```

Ou diretamente:

```bash
docker compose exec prefect-worker ./scripts/run_drift_detection.sh
```

O drift é calculado com PSI comparando:

```text
data/reference/ai4i_reference.csv
data/processed/ai4i_features_latest.csv
```

Critérios usados:

```text
PSI < 0.10       estável
0.10 a 0.20     atenção
PSI >= 0.20     drift detectado
```

Relatórios são gravados em:

```text
reports/drift/
```

## Segurança e Guardrails

O chat possui guardrails antes e depois da chamada ao agente:

- bloqueio de prompt injection;
- restrição de assunto ao domínio da plataforma;
- sanitização de chaves, tokens, URLs de banco e possíveis segredos;
- bloqueio de respostas que tentem expor prompts internos;
- métrica Prometheus `security_guardrail_events_total`.

Os exemplos adversariais ficam em:

```text
data/golden_set/security_eval.jsonl
```

Rodar avaliação de segurança:

```bash
docker compose exec prefect-worker ./scripts/run_security_evaluation.sh
```

## Benchmark, Explicabilidade e Fairness

Gerar benchmark dos modelos:

```bash
docker compose exec prefect-worker ./scripts/run_model_benchmark.sh
```

Gerar artefatos de explicabilidade e fairness:

```bash
docker compose exec prefect-worker ./scripts/run_explainability_fairness.sh
```

Esses relatórios comparam modelos, mostram importância de features e analisam métricas por grupo de produto (`L`, `M` e `H`).

Relatórios principais:

```text
evaluation/reports/agent_eval_latest.json
evaluation/reports/agent_eval_latest.md
evaluation/reports/model_benchmark_latest.json
evaluation/reports/model_benchmark_latest.md
evaluation/reports/explainability_fairness_latest.json
evaluation/reports/explainability_fairness_latest.md
```

## DVC

Arquivos de dados não devem ser versionados diretamente no Git. O dataset original deve ser controlado com DVC:

```bash
dvc add data/raw/ai4i2020.csv
git add data/raw/ai4i2020.csv.dvc data/raw/.gitignore
```

Depois, configure um remote DVC adequado para a entrega, como S3, Azure Blob, Google Cloud Storage ou outro storage compatível.

## Qualidade e CI/CD

O projeto possui:

- GitHub Actions para lint, type check, testes, cobertura, Bandit e build das imagens Docker;
- pre-commit com Ruff, mypy, Bandit e verificações de higiene de arquivos;
- workflow separado para avaliação LLM/RAGAS;
- workflow de deploy com infraestrutura em CloudFormation.

Rodar a qualidade localmente:

```bash
make quality
```

Ou manualmente:

```bash
ruff check src tests evaluation
mypy src evaluation
bandit -r src -c pyproject.toml
pytest tests --cov=src --cov-report=term-missing --cov-report=xml
```

## Documentação

- [Arquitetura](docs/architecture.md)
- [Stack](docs/stack.md)
- [Modelo de Manutenção Preditiva](docs/predictive-maintenance-model.md)
- [Deploy](docs/deployment.md)
- [Governança e LGPD](docs_governance/LGPD_PLAN.md)

## Observação Sobre Chaves de API

Chaves como `OPENAI_API_KEY` devem ficar apenas no `.env` local ou em secrets do GitHub/AWS. Se uma chave for exposta por engano, ela deve ser revogada e recriada imediatamente.
