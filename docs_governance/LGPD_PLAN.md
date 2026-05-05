# Plano de LGPD

Este documento resume como a plataforma trata questões de privacidade e proteção de dados no contexto atual do projeto.

O ponto principal é o seguinte: o dataset usado para modelagem é sintético e não foi construído para conter dados pessoais. Mesmo assim, a plataforma inclui chat, logs, traces e integrações externas, então ainda existe responsabilidade de governança.

## Escopo

O plano cobre a plataforma de manutenção preditiva baseada no dataset AI4I 2020.

Hoje, os maiores pontos de atenção do ponto de vista de LGPD não estão no modelo tabular em si, mas em elementos como:

- prompts enviados ao chat;
- logs de aplicação;
- traces de avaliações com LLM;
- segredos e credenciais;
- futura adaptação do projeto para contexto real de empresa.

## Inventário de Dados

### Dados do dataset

- dataset bruto AI4I em `data/raw/`;
- datasets processados em `data/processed/`;
- features persistidas no PostgreSQL.

Esses dados são sintéticos e representam variáveis de máquina e processo. No estado atual do projeto, eles não são tratados como dados pessoais.

### Dados de interação

- mensagens enviadas ao endpoint `/api/v1/chat`;
- metadados de uso da API;
- possíveis traces de avaliação do agente.

Aqui existe risco de entrada acidental de dados pessoais pelo usuário, mesmo que isso não faça parte do objetivo da plataforma.

### Dados técnicos e operacionais

- métricas;
- logs;
- artefatos de MLflow;
- relatórios;
- segredos de ambiente.

Esses dados não são necessariamente pessoais, mas podem conter informação sensível.

## Finalidade

No estado atual, a finalidade legítima do tratamento é:

- demonstrar uma solução técnica de manutenção preditiva;
- avaliar modelos e pipelines de MLOps;
- auditar treinamento, avaliação e promoção;
- monitorar a operação da plataforma;
- responder perguntas técnicas sobre o projeto via agente com LLM.

Não faz parte da finalidade:

- monitoramento de pessoas;
- perfilamento de funcionários;
- coleta de CPF, e-mail, telefone ou dados biométricos;
- uso da plataforma para decisões automatizadas sobre indivíduos.

## Minimização de Dados

A plataforma foi desenhada para funcionar com o mínimo necessário.

No endpoint de predição, a entrada é limitada a variáveis de máquina:

- tipo de produto;
- temperatura do ar;
- temperatura de processo;
- rotação;
- torque;
- desgaste da ferramenta.

Nenhum identificador pessoal é necessário para que a plataforma cumpra sua função principal.

No chat, a política é restringir o assunto para reduzir a chance de a aplicação receber conteúdo irrelevante ou sensível.

## Riscos Principais

No cenário atual, os principais riscos de LGPD são:

- usuário enviar dados pessoais em prompts do chat;
- logs conterem texto sensível por acidente;
- traces ou avaliações com LLM armazenarem conteúdo que não deveria ser persistido;
- exposição de segredos como chaves de API e senhas.

O dataset principal, por ser sintético, tem risco baixo sob a ótica de dados pessoais.

## Controles Já Implementados

### Guardrails de entrada

O chat possui verificações para:

- bloquear prompt injection;
- bloquear tentativas de extração de segredos;
- restringir o assunto ao domínio da plataforma.

Esses controles ajudam não só em segurança, mas também em privacidade, porque reduzem o volume de entradas inadequadas.

### Sanitização de saída

A resposta do agente passa por sanitização para reduzir risco de exposição de:

- chaves de API;
- tokens;
- URLs de banco com credenciais;
- campos de senha;
- trechos de prompt interno.

### Estrutura de segredos

Localmente, o projeto usa `.env`. Em nuvem, a recomendação é usar:

- secret manager;
- secrets do pipeline;
- rotação de credenciais.

### Governança operacional

O projeto já evita alguns comportamentos de risco:

- promoção manual de modelos;
- separação entre treino e produção;
- documentação explícita do uso pretendido;
- relatórios de avaliação e segurança.

## Retenção

Como este ainda é um projeto de Datathon, a retenção está voltada mais para reprodutibilidade e evidência técnica do que para operação contínua de produção.

Na prática:

- dados brutos e processados são mantidos para reprodutibilidade;
- artefatos de MLflow são mantidos como trilha de auditoria;
- relatórios de benchmark, fairness e segurança são mantidos como evidência;
- logs e traces devem ser minimizados quando houver conteúdo de usuário.

Em um ambiente real, a retenção deveria ser formalizada por ambiente e por categoria de dado.

## Direitos do Titular

Hoje o dataset principal não representa pessoas identificadas. Ainda assim, se o projeto evoluir para armazenar interações de usuários reais, a organização responsável precisará prever:

- acesso aos dados;
- correção;
- exclusão;
- informação sobre finalidade;
- política de retenção;
- registro de consentimento ou outra base legal aplicável, quando necessário.

## Incidentes

Se houver exposição de segredo ou dado pessoal:

1. revogar a credencial ou acesso comprometido;
2. remover o dado de logs, arquivos e artefatos quando possível;
3. revisar onde o conteúdo foi persistido;
4. reavaliar artefatos impactados;
5. documentar causa, impacto e remediação;
6. seguir o processo institucional aplicável.

## Limitações Atuais

O projeto ainda tem limitações típicas de um protótipo:

- não possui autenticação forte em todo o ambiente local;
- pode depender de serviços externos para LLM;
- não possui política completa de retenção por ambiente;
- não implementa um fluxo formal de requisição de titular porque não opera, hoje, sobre dados pessoais estruturados.

## Conclusão

Do ponto de vista de LGPD, o risco principal da plataforma atual não está no modelo de manutenção preditiva em si, mas no uso do chat e na gestão de logs, traces e segredos.

O projeto já possui medidas úteis de redução de risco, especialmente guardrails, sanitização e separação de responsabilidades. Para um uso corporativo real, ainda seriam necessários controles adicionais de acesso, retenção, auditoria e gestão de fornecedores.
