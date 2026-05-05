# Stack

Este documento explica a stack escolhida para a plataforma e o papel de cada tecnologia no estado atual do projeto.

Mais do que listar ferramentas, a ideia aqui é deixar claro por que cada uma existe na solução.

## Visão Geral

A stack foi organizada para cobrir quatro necessidades do projeto:

- servir uma API de manutenção preditiva;
- operar um pipeline de dados e modelos com MLOps;
- suportar um agente com LLM e RAG;
- oferecer observabilidade, segurança e governança.

## Aplicação e API

### FastAPI

O FastAPI é a base da `platform_api`.

Ele foi escolhido porque:

- gera Swagger/OpenAPI automaticamente;
- funciona bem com tipagem e validação;
- é simples de organizar em módulos;
- atende bem tanto endpoints tradicionais quanto rotas de agente, RAG e monitoramento.

Hoje ele concentra as rotas de:

- health e readiness;
- predição;
- chat;
- RAG;
- datasets;
- modelos;
- monitoramento.

### Pydantic

O Pydantic é usado para contratos de entrada e saída da API. Isso ajuda bastante em um projeto como esse porque:

- garante schema consistente;
- melhora a documentação no Swagger;
- reduz erros de payload;
- deixa o código mais seguro para refatorar.

### pandas

O `pandas` é a principal ferramenta de manipulação tabular no pipeline.

Ele é usado para:

- leitura dos CSVs;
- validação de estrutura;
- engenharia de features;
- preparação de datasets processados;
- avaliações e relatórios.

## Dados e Persistência

### PostgreSQL

O PostgreSQL é o banco relacional da plataforma.

Ele faz sentido aqui porque:

- organiza bem dados curados e tabelas de features;
- funciona muito bem com APIs Python;
- também suporta o ecossistema ao redor, como MLflow e Prefect;
- é uma escolha madura, fácil de justificar e comum em cenários corporativos.

No projeto atual, ele guarda:

- registros de datasets enviados;
- batches de ingestão;
- dados curados;
- features utilizadas no treinamento;
- bancos auxiliares do Prefect e do MLflow no ambiente local.

### DVC

O DVC foi adotado para versionamento de dados.

Ele entra principalmente para:

- controlar o dataset bruto;
- manter reprodutibilidade;
- evitar subir CSVs pesados diretamente no Git;
- permitir evolução futura com remote storage.

### Estrutura de pastas de dados

A organização da pasta `data/` segue uma lógica operacional clara:

- `raw/`: dados originais;
- `incoming/`: novos CSVs aguardando ingestão;
- `processed/`: datasets tratados e com features;
- `reference/`: base de referência para drift;
- `archive/`: arquivos já processados;
- `golden_set/`: conjuntos de avaliação do agente e segurança.

## Treinamento e MLOps

### scikit-learn

O `scikit-learn` é a base dos modelos tabulares clássicos da plataforma.

Ele faz sentido porque:

- o AI4I é um dataset tabular relativamente pequeno;
- modelos clássicos são fortes nesse tipo de problema;
- a interpretação e o benchmark ficam mais fáceis;
- o custo computacional é baixo.

Hoje ele já cobre:

- regressão logística;
- random forest;
- extra trees.

### PyTorch

O PyTorch entra como challenger neural, com uma MLP.

Ele não é a escolha mais óbvia para vencer nesse dataset, mas é uma boa decisão para o projeto porque:

- cobre o requisito técnico de usar PyTorch;
- permite comparar um modelo neural com abordagens clássicas;
- enriquece a discussão de benchmark e arquitetura.

O PyTorch fica no runtime offline, no `prefect-worker`, e não na imagem da API.

### MLflow

O MLflow é a peça central do ciclo de vida dos modelos.

Ele é usado para:

- registrar experimentos;
- salvar métricas e parâmetros;
- guardar artefatos;
- manter o registry de modelos;
- separar `candidate` de `champion`;
- sustentar o processo de aprovação manual.

Isso melhora muito a maturidade do projeto em comparação com um versionamento manual de modelos dentro do código.

### Prefect

O Prefect orquestra os processos offline.

Ele faz sentido porque:

- é Python-native;
- conversa bem com o restante da stack;
- facilita agendamento e reexecução de jobs;
- ajuda a separar API de processamento pesado.

No projeto atual, o Prefect executa:

- ingestão inicial;
- ingestão de novos lotes;
- treinamento;
- indexação RAG;
- detecção de drift.

## Serving e Consumo

### MLflow PyFunc

O serving do modelo foi estruturado com contrato `pyfunc` do MLflow.

Isso é útil porque permite servir candidatos diferentes com a mesma interface, mesmo quando um é `scikit-learn` e outro é `PyTorch`.

Na prática, o endpoint de predição continua estável, independentemente do framework do modelo champion.

### Frontend

O projeto também possui um frontend no Docker Compose para demonstrar o consumo da API.

Ele não substitui a API, mas ajuda na experiência de apresentação e validação funcional da plataforma.

## LLM, Agente e RAG

### OpenAI

A OpenAI é usada em três frentes:

- geração de respostas no chat;
- tool calling do agente;
- geração de embeddings para o RAG.

Essa escolha foi feita porque o projeto não vai rodar um LLM local neste momento, e um serviço gerenciado reduz a complexidade operacional.

### Qdrant

O Qdrant é a base vetorial do projeto.

Ele foi escolhido porque:

- roda localmente com Docker;
- também pode ser usado em cloud;
- é simples de integrar com Python;
- atende bem ao RAG documental do projeto.

### RAG customizado

O projeto segue uma abordagem de RAG controlado, com chunking, embeddings e busca vetorial sobre documentação própria.

Isso faz sentido porque o escopo documental é conhecido e confiável:

- documentação do projeto;
- documentos de governança;
- README e AGENTS.

Não faria sentido, neste contexto, abrir ingestão livre de documentos arbitrários pelo usuário final.

## Observabilidade

### Prometheus

O Prometheus coleta métricas da API e de eventos importantes, como:

- latência de predição;
- volume de requests;
- eventos de guardrail;
- chamadas de chat;
- buscas RAG.

### Grafana

O Grafana é a camada visual da observabilidade.

Ele é útil tanto para operação quanto para demonstração, porque transforma métricas técnicas em uma narrativa mais fácil de apresentar.

### PSI para drift

O projeto usa PSI para detecção de drift.

Essa escolha é pragmática:

- é simples de explicar;
- funciona bem para variáveis tabulares;
- atende bem a necessidade do Datathon.

Os relatórios de drift são gerados a partir da comparação entre o dataset de referência e o dataset processado mais recente.

## Segurança e Governança

### Guardrails próprios

A camada de chat possui guardrails implementados no próprio projeto para:

- bloquear prompt injection;
- restringir assunto;
- sanitizar saídas sensíveis;
- reduzir risco de exposição de segredos e prompts internos.

### GitHub Actions

O CI/CD usa GitHub Actions para:

- lint;
- type checking;
- testes;
- cobertura;
- build das imagens;
- avaliações LLM específicas;
- workflow de deploy.

### CloudFormation

Para a parte de infraestrutura na AWS, o projeto usa CloudFormation.

Isso ajuda a deixar a infraestrutura documentada, repetível e defensável em um contexto de arquitetura.

## Imagens Docker

As imagens principais do projeto são:

- `Dockerfile.api`: API online;
- `Dockerfile.worker`: processamento offline;
- `Dockerfile.mlflow`: servidor do MLflow;
- `Dockerfile.prometheus`: observabilidade;
- `Dockerfile.grafana`: dashboards.

A separação entre API e worker é especialmente importante. Embora ambas compartilhem partes do repositório, elas têm funções diferentes e evoluem melhor quando os runtimes também são separados.

## Resumo da Stack

Em termos práticos, a stack atual pode ser resumida assim:

```text
FastAPI
Pydantic
pandas
PostgreSQL
DVC
Prefect
MLflow
scikit-learn
PyTorch
OpenAI
Qdrant
Prometheus
Grafana
GitHub Actions
CloudFormation
Docker Compose
```

É uma stack bem coerente para um projeto de Datathon com cara de plataforma real: moderna, explicável, relativamente portátil e com boa cobertura de MLOps e LLMOps.
