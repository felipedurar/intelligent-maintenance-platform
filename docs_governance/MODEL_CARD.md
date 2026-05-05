# Ficha do Modelo

Este documento resume o modelo de manutenção preditiva utilizado pela plataforma e o contexto em que ele deve ser interpretado.

## Visão Geral

O modelo estima a probabilidade de `machine_failure` a partir de observações de processo e operação de máquinas industriais.

Ele foi construído para apoiar decisões de priorização de manutenção. Não foi desenhado para executar ações automáticas sobre equipamentos e não deve ser tratado como mecanismo de controle autônomo.

## Caso de Uso

O uso pretendido do modelo é:

- estimar risco de falha;
- apoiar triagem de manutenção;
- enriquecer o chat da plataforma com respostas baseadas em predição real;
- servir como componente de demonstração de MLOps e governança.

O uso não pretendido inclui:

- parada automática de máquinas;
- aprovação automática de ordens de manutenção;
- substituição de especialistas de operação ou manutenção;
- extrapolação direta para ambientes industriais reais sem validação local.

## Dados de Treinamento

Fonte dos dados:

- AI4I 2020 Predictive Maintenance Dataset.

Fontes internas do projeto:

- bruto: `data/raw/ai4i2020.csv`
- processado: `data/processed/ai4i_features_latest.csv`

Variável alvo:

- `machine_failure`

Grupo usado nas análises comparativas:

- `product_type` com categorias `L`, `M` e `H`

## Famílias de Modelo Consideradas

O pipeline da plataforma já trabalha com mais de um candidato:

- regressão logística balanceada;
- random forest balanceado;
- extra trees no benchmark;
- MLP em PyTorch, quando disponível no runtime offline.

O melhor candidato é registrado no MLflow como `candidate`. O modelo usado em produção pela API é o `champion`.

## Saída do Modelo

Na plataforma, o contrato de inferência entrega:

- probabilidade de falha;
- classe de risco;
- versão do modelo;
- metadados de execução.

Isso torna o uso mais útil do ponto de vista operacional do que apenas retornar uma classe binária.

## Métricas e Evidências

O projeto gera evidências reproduzíveis de qualidade do modelo.

Artefatos principais:

- `evaluation/reports/model_benchmark_latest.json`
- `evaluation/reports/model_benchmark_latest.md`
- `evaluation/reports/explainability_fairness_latest.json`
- `evaluation/reports/explainability_fairness_latest.md`

O benchmark prioriza `average_precision`, seguido por recall e F1. Essa decisão foi tomada porque falhas são eventos raros no dataset.

## Explicabilidade e Fairness

O relatório de explicabilidade e fairness inclui:

- importância de features;
- comparação entre grupos `L`, `M` e `H`;
- precisão por grupo;
- recall por grupo;
- taxa de falso positivo;
- taxa de falso negativo.

Essa análise deve ser lida como avaliação de consistência operacional entre grupos do dataset, e não como fairness demográfica.

## Monitoramento

O modelo é acompanhado por mecanismos da própria plataforma:

- métricas operacionais expostas pela API;
- relatórios de drift baseados em PSI;
- rastreabilidade de versão via MLflow.

Isso permite relacionar predição, versão do modelo e estado mais recente do pipeline.

## Governança de Promoção

O projeto adota uma separação explícita entre treinamento e produção.

Fluxo atual:

1. o pipeline treina candidatos;
2. escolhe o melhor;
3. registra esse modelo como `candidate`;
4. marca `approval_status=pending`;
5. exige evidências de benchmark e fairness;
6. depende de aprovação humana para virar `champion`.

Esse desenho reduz o risco de substituir o modelo de produção automaticamente com base apenas em uma métrica de treino.

## Limitações

As principais limitações do modelo atual são:

- o dataset é sintético;
- os dados podem não representar uma planta industrial específica;
- o custo relativo entre falso positivo e falso negativo depende do negócio real;
- thresholds operacionais podem precisar de calibração;
- a análise de fairness é limitada aos grupos disponíveis no dataset.

## Status Atual

No estado atual do projeto, o modelo é adequado como:

- componente de suporte à decisão;
- evidência técnica de MLOps;
- base de experimentação e comparação de candidatos.

Ele não deve ser tratado como sistema pronto para automação industrial real sem validação adicional em dados reais, revisão de especialistas do domínio e definição formal de thresholds operacionais.
