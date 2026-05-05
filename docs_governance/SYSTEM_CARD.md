# Ficha do Sistema

Este documento descreve a plataforma como sistema completo, não apenas como modelo isolado.

O objetivo é deixar claro o que o sistema faz, para quem ele serve, quais controles já existem e quais limitações ainda permanecem.

## Visão Geral

A plataforma é um sistema de apoio à decisão para manutenção preditiva em máquinas industriais.

Ela combina:

- um modelo de predição de falha;
- uma API para serving;
- pipelines de ingestão e treinamento;
- governança de modelos no MLflow;
- monitoramento;
- um assistente com LLM e RAG sobre a própria documentação.

O projeto foi estruturado para demonstrar capacidades de MLOps, LLMOps, segurança e governança em um contexto de Datathon.

## Usuários Esperados

Os principais perfis de uso são:

- analistas de manutenção interessados no risco de falha;
- cientistas de dados comparando modelos e relatórios;
- engenheiros de MLOps operando ingestão, treinamento e promoção;
- avaliadores do Datathon analisando arquitetura, segurança e governança.

## Uso Pretendido

O sistema foi desenhado para:

- estimar risco de falha para uma observação de máquina;
- documentar e explicar a solução;
- apoiar perguntas em linguagem natural sobre o projeto;
- monitorar métricas e drift;
- manter um fluxo auditável de promoção de modelos.

## Uso Não Pretendido

O sistema não foi desenhado para:

- controlar máquinas diretamente;
- disparar ações automáticas de manutenção;
- operar fora do domínio de manutenção preditiva;
- servir como única fonte de decisão operacional;
- substituir validação humana em ambiente industrial real.

## Componentes do Sistema

### Camada online

- `platform_api`: predição, chat, busca RAG, datasets, monitoramento e metadados;
- frontend: camada de consumo para demonstração e interação.

### Camada offline

- `prefect-worker`: ingestão, treinamento, drift, indexação RAG, avaliações.

### Serviços de suporte

- PostgreSQL;
- MLflow;
- Qdrant;
- Prometheus;
- Grafana;
- OpenAI.

## Superfície de API

Rotas principais expostas hoje:

```text
GET  /api/v1/health
GET  /api/v1/ready
POST /api/v1/chat
POST /api/v1/predictions
GET  /api/v1/machines/dataset/status
POST /api/v1/datasets/upload
GET  /api/v1/datasets/uploads
GET  /api/v1/datasets/batches
GET  /api/v1/datasets/batches/{batch_id}
POST /api/v1/datasets/ingest
POST /api/v1/datasets/retrain
GET  /api/v1/models/{model_name}/active
POST /api/v1/rag/search
GET  /api/v1/monitoring/status
GET  /metrics
```

Documentação interativa:

```text
/api/v1/docs
```

## Ferramentas do Agente

O agente usa tool calling com escopo limitado. As ferramentas principais são:

- busca de documentação do projeto;
- consulta ao modelo ativo no MLflow;
- predição de risco de falha.

Esse recorte é intencional. O agente não possui ferramentas para alterar infraestrutura, promover modelos, gravar dados arbitrários ou executar automações perigosas.

## Ciclo de Vida do Modelo

O fluxo atual do sistema é:

```text
dataset bruto -> ingestão -> features -> treinamento -> candidate
-> benchmark e fairness -> aprovação humana -> champion -> serving
```

Isso significa que o modelo em produção depende de um gate explícito de governança. O pipeline pode sugerir o melhor candidato, mas não faz a promoção sozinho.

## Monitoramento

O sistema possui duas camadas principais de monitoramento.

### Monitoramento operacional

- métricas Prometheus em `/metrics`;
- dashboards no Grafana;
- contadores de chat, predição, latência, RAG e guardrails.

### Monitoramento de dados e modelo

- drift baseado em PSI;
- relatórios em `reports/drift/`;
- benchmark e fairness como evidência de qualidade;
- rastreabilidade de versão no MLflow.

## Segurança

O sistema já possui controles concretos para o chat e para a superfície LLM.

### Guardrails de entrada

- bloqueio de prompt injection;
- bloqueio de tentativas de extração de segredos;
- restrição de tópico.

### Guardrails de saída

- sanitização de chaves e tokens;
- remoção de credenciais em URLs;
- bloqueio de vazamento de prompt interno;
- mitigação de afirmações indevidas de automação.

### Evidências

- conjunto de testes adversariais;
- avaliação de segurança reproduzível;
- mapeamento OWASP;
- relatório de red team.

## Supervisão Humana

O sistema depende de supervisão humana em pontos críticos:

- interpretação de risco de falha;
- decisão final de manutenção;
- promoção de modelo;
- aceitação de artefatos de benchmark e fairness;
- validação de uso em contexto real.

Isso não é uma limitação acidental. É uma decisão de desenho.

## Limitações Atuais

As principais limitações do sistema hoje são:

- base de modelagem sintética;
- dependência de um LLM gerenciado externo;
- autenticação e RBAC ainda mais fortes na arquitetura de cloud do que no ambiente local;
- qualidade do RAG dependente da qualidade da documentação indexada;
- ausência de validação industrial em dados reais.

## Conclusão

Como sistema, a plataforma já é mais do que uma API de predição isolada. Ela combina modelo, operação, documentação, observabilidade, avaliação e governança.

Ao mesmo tempo, o projeto deixa claro seu posicionamento: trata-se de um sistema de apoio à decisão e de demonstração técnica madura, não de automação industrial autônoma.
