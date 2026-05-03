#!/usr/bin/env bash
# Configura GitHub Secrets e Variables necessários para o CI/CD da IM Platform.
# Requer: gh CLI autenticado (gh auth login) e jq instalado.
#
# Uso:
#   export GITHUB_REPO=org/repo          # ex: everton-vieira/intelligent-maintenance-platform
#   export AWS_ACCOUNT_ID=123456789012
#   export AWS_REGION=us-east-1
#   bash infra/scripts/github-secrets-setup.sh

set -euo pipefail

: "${GITHUB_REPO:?Defina GITHUB_REPO=org/repo}"
: "${AWS_ACCOUNT_ID:?Defina AWS_ACCOUNT_ID}"
: "${AWS_REGION:?Defina AWS_REGION}"

ECR_BASE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "=== IM Platform — GitHub Secrets/Variables Setup ==="
echo "Repositório: $GITHUB_REPO"
echo ""

# ── Secrets (valores sensíveis) ───────────────────────────────────────────────

echo "--- Configurando GitHub Secrets ---"

# AWS_ROLE_ARN — obtido do output do stack 03-ecr
ROLE_ARN=$(aws cloudformation describe-stacks \
    --region "$AWS_REGION" \
    --stack-name intelligent-maintenance-ecr \
    --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsDeployRoleArn'].OutputValue" \
    --output text 2>/dev/null || echo "")

if [ -z "$ROLE_ARN" ]; then
    read -rp "AWS_ROLE_ARN (ARN do GitHubActionsDeployRole): " ROLE_ARN
fi

gh secret set AWS_ROLE_ARN        --repo "$GITHUB_REPO" --body "$ROLE_ARN"
echo "✓ AWS_ROLE_ARN"

# ── Variables (valores não-sensíveis) ─────────────────────────────────────────

echo ""
echo "--- Configurando GitHub Variables ---"

gh variable set AWS_ACCOUNT_ID    --repo "$GITHUB_REPO" --body "$AWS_ACCOUNT_ID"
echo "✓ AWS_ACCOUNT_ID"

gh variable set AWS_REGION        --repo "$GITHUB_REPO" --body "$AWS_REGION"
echo "✓ AWS_REGION"

gh variable set ECR_API_REPO      --repo "$GITHUB_REPO" --body "${ECR_BASE}/im/platform-api"
echo "✓ ECR_API_REPO"

gh variable set ECR_WORKER_REPO   --repo "$GITHUB_REPO" --body "${ECR_BASE}/im/prefect-worker"
echo "✓ ECR_WORKER_REPO"

gh variable set ECR_MLFLOW_REPO   --repo "$GITHUB_REPO" --body "${ECR_BASE}/im/mlflow"
echo "✓ ECR_MLFLOW_REPO"

gh variable set ECR_PROMETHEUS_REPO --repo "$GITHUB_REPO" --body "${ECR_BASE}/im/prometheus"
echo "✓ ECR_PROMETHEUS_REPO"

gh variable set ECR_GRAFANA_REPO  --repo "$GITHUB_REPO" --body "${ECR_BASE}/im/grafana"
echo "✓ ECR_GRAFANA_REPO"

gh variable set ECS_CLUSTER       --repo "$GITHUB_REPO" --body "intelligent-maintenance-cluster"
echo "✓ ECS_CLUSTER"

gh variable set ECS_API_SERVICE   --repo "$GITHUB_REPO" --body "platform-api"
echo "✓ ECS_API_SERVICE"

gh variable set ECS_WORKER_SERVICE --repo "$GITHUB_REPO" --body "prefect-worker"
echo "✓ ECS_WORKER_SERVICE"

echo ""
echo "=== Configuração concluída! ==="
echo ""
echo "Verifique em: https://github.com/${GITHUB_REPO}/settings/secrets/actions"
