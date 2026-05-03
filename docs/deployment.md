# Deployment Guide — AWS Infrastructure

Este guia cobre todo o processo de deploy da plataforma na AWS, desde a criação da infraestrutura até o primeiro deploy via GitHub Actions.

---

## Pré-requisitos

Ferramentas necessárias na máquina local:

| Ferramenta | Versão mínima | Instalação |
|------------|--------------|------------|
| AWS CLI | v2 | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| GitHub CLI (`gh`) | v2 | https://cli.github.com |
| Docker | v24 | https://docs.docker.com/get-docker |
| Python | 3.12 | https://python.org |

Contas e acessos necessários:

- **AWS**: conta com permissões de administrador (para criar IAM, VPC, ECS, EFS, S3, ECR, Secrets Manager)
- **GitHub**: repositório criado, `gh auth login` executado
- **Tailscale**: conta free em https://tailscale.com — gere uma auth key em Settings → Keys
- **No-IP**: conta com um hostname DDNS criado em https://www.noip.com

Configure o AWS CLI antes de começar:

```bash
aws configure
# AWS Access Key ID: ...
# AWS Secret Access Key: ...
# Default region name: us-east-1
# Default output format: json
```

---

## Visão Geral dos Stacks

```
01-network  ──►  02-storage  ──►  03-ecr  ──►  04-ecs
   VPC               EFS             ECR          ECS
   Subnets           S3              OIDC         Tasks
   SGs               Secrets         Deploy Role  Services
   Cloud Map
```

Cada stack exporta outputs consumidos pelo próximo via `!ImportValue`.  
**A ordem de deploy é obrigatória.**

---

## 1. Deploy dos CloudFormation Stacks

Defina as variáveis de ambiente antes de começar:

```bash
export AWS_REGION=us-east-1
export PROJECT=intelligent-maintenance

# Seu usuário ou org no GitHub (ex: everton-vieira)
export GITHUB_ORG=SEU_USUARIO_GITHUB

# Nome do repositório (ex: intelligent-maintenance-platform)
export GITHUB_REPO_NAME=intelligent-maintenance-platform
```

### Stack 1 — Rede

Cria VPC, subnets, Internet Gateway, Security Groups e Cloud Map namespace `im.local`.

```bash
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-network" \
  --template-file infra/cloudformation/01-network.yml \
  --parameter-overrides \
      ProjectName="$PROJECT" \
      Environment=prod \
  --capabilities CAPABILITY_NAMED_IAM
```

Verifique os outputs:

```bash
aws cloudformation describe-stacks \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-network" \
  --query "Stacks[0].Outputs" \
  --output table
```

---

### Stack 2 — Storage

Cria EFS (5 access points), S3 (3 buckets) e Secrets Manager (5 secrets com valores placeholder).

```bash
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-storage" \
  --template-file infra/cloudformation/02-storage.yml \
  --parameter-overrides \
      ProjectName="$PROJECT" \
      Environment=prod \
  --capabilities CAPABILITY_NAMED_IAM
```

> ⚠️ Após este stack, os secrets existem mas com valor `CHANGE_ME`. Você os preencherá na [Seção 2](#2-preencher-os-secrets-na-aws).

---

### Stack 3 — ECR + OIDC

Cria os 5 repositórios ECR, o OIDC Provider do GitHub e a IAM Role para o deploy.

```bash
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-ecr" \
  --template-file infra/cloudformation/03-ecr.yml \
  --parameter-overrides \
      ProjectName="$PROJECT" \
      GitHubOrg="$GITHUB_ORG" \
      GitHubRepo="$GITHUB_REPO_NAME" \
  --capabilities CAPABILITY_NAMED_IAM
```

Anote o ARN do role de deploy (será usado no GitHub):

```bash
aws cloudformation describe-stacks \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-ecr" \
  --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsDeployRoleArn'].OutputValue" \
  --output text
```

---

### Stack 4 — ECS

Cria o cluster ECS, todas as task definitions, os 8 services, IAM roles e CloudWatch log groups.

> ⚠️ Execute este stack **somente após** preencher os secrets (Seção 2).  
> As tasks falharão ao iniciar se os secrets ainda tiverem valor `CHANGE_ME`.

```bash
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-ecs" \
  --template-file infra/cloudformation/04-ecs.yml \
  --parameter-overrides \
      ProjectName="$PROJECT" \
      Environment=prod \
      ImageTag=latest \
  --capabilities CAPABILITY_NAMED_IAM
```

> Na primeira execução, o `ImageTag=latest` ainda não existe nos repositórios ECR.  
> Os serviços com imagens customizadas ficarão em `PENDING` até o primeiro push.  
> Os serviços com imagens oficiais (postgres, prefect-server, qdrant) sobem normalmente.

---

## 2. Preencher os Secrets na AWS

Execute o script interativo que pede cada valor e atualiza o Secrets Manager:

```bash
export AWS_REGION=us-east-1
bash infra/scripts/aws-secrets-setup.sh
```

O script pedirá:

| Secret | O que informar |
|--------|---------------|
| `POSTGRES_PASSWORD` | Senha forte para o PostgreSQL (mínimo 16 chars) |
| `OPENAI_API_KEY` | Sua API key da OpenAI (`sk-...`) |
| `NOIP_USERNAME` | Usuário/e-mail do No-IP |
| `NOIP_PASSWORD` | Senha do No-IP |
| `NOIP_HOST` | Hostname DDNS (ex: `minha-api.ddns.net`) |
| `TS_AUTHKEY` | Auth key do Tailscale (reusável, tag `tag:ecs-private`) |
| `GF_SECURITY_ADMIN_PASSWORD` | Senha do admin do Grafana |

### Gerar a Tailscale Auth Key

1. Acesse https://login.tailscale.com/admin/settings/keys
2. Clique em **Generate auth key**
3. Marque **Reusable** e **No expiry** (ou uma data longa)
4. Em **Tags**, adicione `tag:ecs-private`
5. Copie a key gerada

### Configurar ACL no Tailscale

Acesse https://login.tailscale.com/admin/acls e garanta que a tag existe:

```json
"tagOwners": {
  "tag:ecs-private": ["autogroup:admin"]
}
```

---

## 3. Configurar o GitHub

### Configurar Secrets e Variables

```bash
export GITHUB_REPO=${GITHUB_ORG}/${GITHUB_REPO_NAME}
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=us-east-1

bash infra/scripts/github-secrets-setup.sh
```

O script configura automaticamente via `gh` CLI:

**Secrets** (valores sensíveis — ficam ocultos nos logs):

| Nome | Valor configurado |
|------|-----------------|
| `AWS_ROLE_ARN` | ARN do `GitHubActionsDeployRole` (lido do stack 03-ecr) |

**Variables** (valores não-sensíveis — visíveis nos logs):

| Nome | Exemplo de valor |
|------|----------------|
| `AWS_ACCOUNT_ID` | `123456789012` |
| `AWS_REGION` | `us-east-1` |
| `ECR_API_REPO` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/im/platform-api` |
| `ECR_WORKER_REPO` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/im/prefect-worker` |
| `ECR_MLFLOW_REPO` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/im/mlflow` |
| `ECR_PROMETHEUS_REPO` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/im/prometheus` |
| `ECR_GRAFANA_REPO` | `123456789012.dkr.ecr.us-east-1.amazonaws.com/im/grafana` |
| `ECS_CLUSTER` | `intelligent-maintenance-cluster` |
| `ECS_API_SERVICE` | `platform-api` |
| `ECS_WORKER_SERVICE` | `prefect-worker` |

Verifique em: `https://github.com/SEU_ORG/SEU_REPO/settings/secrets/actions`

---

## 4. Primeiro Deploy (Push de Imagens)

O stack 04-ecs foi criado mas as imagens customizadas ainda não existem no ECR.  
Crie a primeira tag `prod-` para disparar o workflow de deploy:

```bash
git tag prod-1.0.0
git push origin prod-1.0.0
```

O workflow `.github/workflows/deploy.yml` irá:
1. Autenticar na AWS via OIDC (sem credenciais permanentes)
2. Fazer login no ECR
3. Build e push das 5 imagens (`platform-api`, `prefect-worker`, `mlflow`, `prometheus`, `grafana`)
4. Atualizar as task definitions com a nova tag
5. Forçar redeploy de todos os services com imagens customizadas
6. Aguardar `platform-api` e `prefect-worker` estabilizarem

Acompanhe em: `https://github.com/SEU_ORG/SEU_REPO/actions`

---

## 5. Tarefas de Inicialização Únicas (Pós-Primeiro Deploy)

Após o primeiro deploy, execute duas tarefas únicas via `aws ecs run-task`.

### 5.1 Criar os bancos de dados no PostgreSQL

```bash
CLUSTER="intelligent-maintenance-cluster"
REGION="us-east-1"

# Obter subnet e SG privado dos outputs do stack network
SUBNET=$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name intelligent-maintenance-network \
  --query "Stacks[0].Outputs[?OutputKey=='PublicSubnet1Id'].OutputValue" \
  --output text)

SG=$(aws cloudformation describe-stacks \
  --region "$REGION" \
  --stack-name intelligent-maintenance-network \
  --query "Stacks[0].Outputs[?OutputKey=='SGPrivateId'].OutputValue" \
  --output text)

# Executar task de init
aws ecs run-task \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --task-definition intelligent-maintenance-postgres-init \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNET}],securityGroups=[${SG}],assignPublicIp=ENABLED}" \
  --count 1
```

Acompanhe os logs em CloudWatch: `/ecs/im/postgres` (stream prefix: `init`)

### 5.2 Registrar os Prefect Deployments

```bash
aws ecs run-task \
  --region "$REGION" \
  --cluster "$CLUSTER" \
  --task-definition intelligent-maintenance-prefect-deployments \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[${SUBNET}],securityGroups=[${SG}],assignPublicIp=ENABLED}" \
  --count 1
```

Acompanhe os logs em CloudWatch: `/ecs/im/prefect-worker` (stream prefix: `deployments`)

---

## 6. Upload do Dataset Inicial para S3

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws s3 cp data/raw/ai4i2020.csv \
  s3://im-data-${ACCOUNT_ID}/raw/ai4i2020.csv
```

---

## 7. Acessar os Serviços via Tailscale

Após o deploy, instale o Tailscale no seu computador:  
https://tailscale.com/download

Faça login na mesma conta usada para gerar a auth key. Os containers privados aparecerão automaticamente como dispositivos na sua rede Tailscale.

| Serviço | Endereço Tailscale | Porta |
|---------|-------------------|-------|
| PostgreSQL | `im-postgres` | 5432 |
| MLflow UI | `im-mlflow` | 5000 |
| Prefect UI | `im-prefect` | 4200 |
| Qdrant UI | `im-qdrant` | 6333 |
| Prometheus | `im-prometheus` | 9090 |
| Grafana | `im-grafana` | 3000 |

Exemplos de acesso:

```bash
# Abrir MLflow UI no browser
open http://im-mlflow:5000

# Conectar ao PostgreSQL com psql
psql -h im-postgres -U datathon -d datathon

# Criar banco prefect (se não rodou o RunTask)
psql -h im-postgres -U datathon -c "CREATE DATABASE prefect;" || true
psql -h im-postgres -U datathon -c "CREATE DATABASE mlflow;"  || true
```

A API pública é acessada pelo hostname No-IP configurado:

```bash
curl http://SEU_HOST.ddns.net:8000/api/v1/health
```

---

## 8. Ciclo de Deploy (Deploys Subsequentes)

A cada novo deploy, crie uma tag com prefixo `prod-`:

```bash
# Exemplos válidos:
git tag prod-1.1.0 && git push origin prod-1.1.0
git tag prod-2025-05-10 && git push origin prod-2025-05-10
```

O workflow de deploy **não dispara** em commits diretos — apenas em tags `prod-*`.  
O CI (lint + testes + build validation) roda em todo push e pull request.

---

## 9. Atualizar a Infraestrutura

Para alterar qualquer stack CloudFormation:

```bash
# Edite o template desejado e re-execute o deploy
aws cloudformation deploy \
  --region "$AWS_REGION" \
  --stack-name "${PROJECT}-ecs" \
  --template-file infra/cloudformation/04-ecs.yml \
  --parameter-overrides ProjectName="$PROJECT" Environment=prod ImageTag=latest \
  --capabilities CAPABILITY_NAMED_IAM
```

O CloudFormation calcula automaticamente o diff e aplica apenas as mudanças necessárias.

---

## 10. Referência — Recursos Criados por Stack

### Stack 01-network
- VPC `10.0.0.0/16` com 2 subnets públicas (AZ-a e AZ-b)
- Internet Gateway + Route Table
- `SG-1` (public): inbound TCP 8000 de `0.0.0.0/0` — usado por `platform-api`
- `SG-2` (private): sem inbound da internet — usado por todos os serviços internos
- `SG-EFS`: inbound NFS 2049 de SG-1 e SG-2 — usado pelos mount targets do EFS
- Cloud Map namespace `im.local` (DNS privado interno)

### Stack 02-storage
- EFS com 5 access points: `postgres`, `qdrant`, `prometheus`, `grafana`, `reports`
- S3: `im-data-ACCOUNT`, `im-artifacts-ACCOUNT`, `im-cfn-ACCOUNT`
- Secrets Manager: `im/db-password`, `im/openai`, `im/noip`, `im/tailscale`, `im/grafana`

### Stack 03-ecr
- ECR: `im/platform-api`, `im/prefect-worker`, `im/mlflow`, `im/prometheus`, `im/grafana`
- IAM OIDC Provider para `token.actions.githubusercontent.com`
- IAM Role `intelligent-maintenance-github-deploy-role` (assume via OIDC em tags `prod-*`)

### Stack 04-ecs
- ECS Cluster `intelligent-maintenance-cluster`
- 8 ECS Services: `platform-api`, `postgres`, `mlflow`, `prefect-server`, `prefect-worker`, `qdrant`, `prometheus`, `grafana`
- 2 task definitions de inicialização: `postgres-init`, `prefect-deployments`
- IAM Roles: `ECSTaskExecutionRole`, `PlatformAPITaskRole`, `PrivateServicesTaskRole`
- CloudWatch Log Groups: `/ecs/im/*` (retenção 14 dias)
- Cloud Map services: `postgres`, `mlflow`, `prefect-server`, `qdrant`, `platform-api`
