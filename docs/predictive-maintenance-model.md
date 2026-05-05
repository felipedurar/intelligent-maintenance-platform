# Modelo de Manutenção Preditiva

Este documento descreve o problema de modelagem, as features, os modelos treinados, os critérios de avaliação e a forma como o modelo entra em produção na plataforma.

## Problema

O objetivo do modelo é prever a variável:

```text
Machine failure
```

Em outras palavras, o modelo estima a probabilidade de falha da máquina a partir das variáveis de processo observadas em um determinado ponto.

Trata-se de um problema de classificação binária:

- `0`: sem falha;
- `1`: com falha.

## O que o modelo retorna

Na plataforma, a inferência não retorna apenas um rótulo seco. A API entrega:

- probabilidade de falha;
- classe de risco;
- versão do modelo;
- metadados úteis para auditoria.

Isso faz mais sentido do ponto de vista operacional, porque manutenção preditiva raramente depende só de um sim ou não. A probabilidade e a faixa de risco ajudam mais na priorização.

## Dataset Utilizado

O projeto usa o **AI4I 2020 Predictive Maintenance Dataset**.

Colunas principais:

- `UDI`
- `Product ID`
- `Type`
- `Air temperature [K]`
- `Process temperature [K]`
- `Rotational speed [rpm]`
- `Torque [Nm]`
- `Tool wear [min]`
- `Machine failure`
- `TWF`
- `HDF`
- `PWF`
- `OSF`
- `RNF`

O alvo principal do modelo é `Machine failure`.

As colunas `TWF`, `HDF`, `PWF`, `OSF` e `RNF` são úteis para análise de falhas, entendimento do dataset e possíveis estudos diagnósticos, mas não devem ser usadas como features do classificador principal, porque carregam informação muito próxima do desfecho.

## Entradas da API de Predição

Hoje a API de predição recebe uma observação estruturada com:

- `product_type`
- `air_temperature_k`
- `process_temperature_k`
- `rotational_speed_rpm`
- `torque_nm`
- `tool_wear_min`

Esses campos são suficientes para a plataforma reconstruir a engenharia de features usada no treinamento e servir a inferência com consistência.

## Engenharia de Features

O projeto não usa apenas os dados crus. Durante a ingestão e no serving, a plataforma deriva variáveis adicionais para representar melhor o comportamento físico do processo.

Exemplos importantes:

- delta de temperatura entre processo e ar;
- velocidade angular derivada da rotação;
- potência estimada a partir de torque e rotação;
- interações entre torque e velocidade;
- interações entre desgaste e torque;
- indicadores de risco ligados às condições descritas no próprio AI4I.

Essa decisão faz bastante sentido porque o dataset já sugere relações físicas claras entre falha, dissipação térmica, esforço e potência.

## Modelos da Plataforma

Atualmente, a plataforma trabalha com múltiplos candidatos.

### Baseline

- regressão logística balanceada.

Ela serve como referência simples, rápida e interpretável.

### Challengers

- random forest balanceado;
- extra trees no benchmark;
- MLP em PyTorch como challenger neural, quando disponível no runtime de treinamento.

Isso permite comparar:

- um modelo linear;
- modelos baseados em árvores;
- um modelo neural tabular.

## Critério de Seleção

Como a classe de falha é desbalanceada, o projeto prioriza métricas mais adequadas para esse tipo de cenário.

A ordenação principal dos candidatos é feita por:

1. `average_precision`
2. `recall`
3. `f1`

Essa escolha foi feita porque, em manutenção preditiva, deixar passar uma falha real costuma ser mais caro do que investigar alguns falsos positivos adicionais.

## Métricas Avaliadas

Entre as métricas usadas no treinamento e benchmark estão:

- ROC AUC;
- average precision;
- precisão;
- recall;
- F1;
- matriz de confusão.

Essas métricas são registradas no MLflow e reaproveitadas nos artefatos de benchmark e governança.

## Benchmark

O projeto gera um benchmark comparando os candidatos do pipeline.

Esse benchmark serve para:

- justificar a escolha do melhor modelo;
- comparar frameworks diferentes;
- documentar custo-benefício entre desempenho e complexidade;
- sustentar a promoção manual de modelos.

Relatórios esperados:

```text
evaluation/reports/model_benchmark_latest.json
evaluation/reports/model_benchmark_latest.md
```

## Explicabilidade e Fairness

O projeto também gera um relatório dedicado a explicabilidade e análise de grupo.

Hoje ele cobre:

- importância de features;
- avaliação por tipo de produto (`L`, `M`, `H`);
- comparação de precisão;
- comparação de recall;
- comparação de false positive rate;
- comparação de false negative rate.

Essa análise não é uma avaliação de fairness demográfica. Ela é uma análise de consistência operacional entre grupos do dataset.

Relatórios esperados:

```text
evaluation/reports/explainability_fairness_latest.json
evaluation/reports/explainability_fairness_latest.md
```

## Registro no MLflow

O treinamento registra:

- parâmetros;
- métricas;
- artefatos;
- tipo de modelo;
- versão de features;
- versão de dados;
- status de aprovação;
- nome do candidato.

Aliases usados:

- `candidate`
- `champion`
- `previous_champion`

Essa estrutura melhora bastante a governança da plataforma porque separa o melhor modelo treinado do modelo realmente aprovado para produção.

## Serving

O endpoint de predição consome apenas o modelo `champion`.

Fluxo simplificado:

1. recebe a observação;
2. aplica a engenharia de features;
3. carrega o modelo aprovado via MLflow;
4. retorna probabilidade, classe de risco e metadados.

O contrato de serving foi desenhado para funcionar tanto com modelos `scikit-learn` quanto com o challenger em PyTorch, via wrapper `pyfunc` do MLflow.

Isso significa que a API não precisa mudar quando o champion troca de framework.

## Promoção de Modelo

O ciclo de promoção foi desenhado para ter controle humano explícito.

Hoje ele funciona assim:

1. o pipeline treina candidatos;
2. escolhe o melhor;
3. registra esse modelo como `candidate`;
4. marca `approval_status=pending`;
5. exige benchmark e relatório de fairness/explicabilidade;
6. depende de aprovação manual para virar `champion`.

Esse processo reduz o risco de colocar em produção um modelo novo sem revisão suficiente.

## Limitações

Algumas limitações importantes do modelo atual:

- o AI4I é um dataset sintético;
- o comportamento observado pode não representar uma planta industrial real;
- limiares de risco podem precisar de calibração conforme o contexto do negócio;
- o modelo é um apoio à decisão, não um sistema de automação industrial.

## Resumo

O modelo da plataforma foi pensado para ser tecnicamente consistente e, ao mesmo tempo, fácil de defender:

- usa um problema bem definido;
- aplica engenharia de features coerente com o domínio;
- compara baseline e challengers;
- registra tudo no MLflow;
- separa candidato de champion;
- entra em produção apenas após aprovação humana.
