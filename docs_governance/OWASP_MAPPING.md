# Mapeamento OWASP para LLMs

Este documento relaciona riscos relevantes do OWASP Top 10 para aplicações com LLM ao estado atual da plataforma.

O foco aqui não é dizer que todos os riscos estão “resolvidos”. A ideia é mostrar, com honestidade, o que já foi implementado, o que já possui evidência e o que ainda depende de evolução para um cenário real de produção.

## Resumo Executivo

Os riscos mais relevantes para o projeto hoje são:

- prompt injection;
- exposição de informação sensível;
- uso indevido de ferramentas do agente;
- envenenamento de contexto no RAG;
- promoção inadequada de modelos;
- abuso de consumo da camada de LLM.

## Mapeamento

### Prompt Injection

**Como aparece no projeto**

O usuário pode tentar convencer o agente a ignorar instruções, revelar prompt interno ou contornar regras de uso.

**Impacto**

- respostas não confiáveis;
- vazamento de contexto interno;
- chamadas indevidas de ferramentas.

**Mitigações atuais**

- detecção de padrões de prompt injection na entrada;
- bloqueio antes da chamada ao LLM;
- conjunto de avaliação adversarial.

**Evidências**

- `src/security/guardrails.py`
- `data/golden_set/security_eval.jsonl`
- `evaluation/reports/security_eval_latest.json`

### Exposição de informação sensível

**Como aparece no projeto**

Tentativas de solicitar chave da OpenAI, senhas de banco, prompts internos ou credenciais.

**Impacto**

- comprometimento de segredos;
- vazamento de detalhes internos da plataforma.

**Mitigações atuais**

- bloqueio de pedidos explícitos de segredos;
- sanitização de tokens e credenciais na saída;
- recomendação de uso de secrets fora do código.

**Evidências**

- `src/security/guardrails.py`
- cenários de segurança já implementados

### Insecure Output Handling

**Como aparece no projeto**

O agente pode produzir uma resposta que sugira automação indevida, excesso de confiança ou instruções inadequadas.

**Impacto**

- usuário interpretar a resposta como comando operacional;
- uso indevido do sistema em contexto industrial.

**Mitigações atuais**

- sanitização de saída;
- framing do sistema como apoio à decisão;
- documentação explícita em model card e system card.

### Excessive Agency

**Como aparece no projeto**

Um agente com ferramentas pode ser confundido com um sistema de execução operacional.

**Impacto**

- sobrecarga de confiança;
- interpretação errada do escopo do assistente.

**Mitigações atuais**

- conjunto de ferramentas limitado;
- ausência de ferramentas destrutivas ou operacionais;
- promoção de modelo fora do escopo do agente.

### Insecure Tool Use

**Como aparece no projeto**

Chamadas com payload inválido ou inadequado para as ferramentas do agente.

**Impacto**

- resultados incorretos;
- comportamento fora do esperado;
- uso frágil da API.

**Mitigações atuais**

- schemas explícitos para requests;
- validação com Pydantic na API;
- ferramentas do agente com escopo conhecido.

### Data and Vector Store Poisoning

**Como aparece no projeto**

O RAG pode ser afetado se documentos maliciosos ou incorretos forem indexados.

**Impacto**

- respostas documentais enviesadas;
- grounding ruim;
- confiança excessiva em contexto contaminado.

**Mitigações atuais**

- indexação restrita a documentos do próprio projeto;
- indexação via worker e scripts controlados;
- ausência de upload aberto de documentação arbitrária para o RAG.

### Supply Chain e Integridade do Modelo

**Como aparece no projeto**

Um modelo pode ser colocado em produção sem revisão suficiente.

**Impacto**

- champion ruim em produção;
- perda de rastreabilidade;
- fragilidade de governança.

**Mitigações atuais**

- MLflow como registry;
- alias `candidate` e `champion`;
- aprovação manual;
- necessidade de benchmark e fairness antes da promoção.

### Model Denial of Service

**Como aparece no projeto**

Prompts grandes, off-topic ou abusivos podem consumir recursos desnecessários do LLM e das ferramentas.

**Impacto**

- custo;
- latência;
- degradação de serviço.

**Mitigações atuais**

- restrição de tópico;
- guardrails de entrada;
- separação entre API online e worker offline.

**Controles ainda recomendados**

- autenticação;
- rate limiting;
- quotas por usuário ou chave.

## Evidências Atuais

O projeto já possui evidências concretas, e não apenas intenção documental:

- testes de segurança;
- relatório de avaliação determinística;
- guardrails implementados;
- governança de promoção;
- documentação de limites do sistema.

## Riscos Residuais

Mesmo com os controles atuais, ainda existem riscos residuais relevantes:

- ataques mais sofisticados de prompt injection podem escapar de regras determinísticas;
- o RAG depende de disciplina sobre quais documentos entram no índice;
- o ambiente local ainda não representa um hardening completo de produção;
- o uso de um LLM gerenciado traz dependências externas de fornecedor.

## Recomendações para Produção

Antes de tratar a solução como ambiente real de produção, o ideal é acrescentar:

1. autenticação forte na API;
2. RBAC por função;
3. rate limiting;
4. logs centralizados de segurança;
5. revisão obrigatória de mudanças em documentos indexados no RAG;
6. varredura de dependências e imagens;
7. avaliações recorrentes após mudanças em prompts, ferramentas ou contexto documental.

## Conclusão

O projeto já trata com seriedade os riscos mais comuns de aplicações com LLM, especialmente no que diz respeito a prompt injection, segredos, escopo do agente e governança de modelos.

Ainda assim, os controles atuais devem ser vistos como uma base sólida para o Datathon, não como ponto final de segurança para produção corporativa.
