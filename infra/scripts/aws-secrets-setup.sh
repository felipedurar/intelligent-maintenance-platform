#!/usr/bin/env bash
# Preenche os valores reais nos secrets do AWS Secrets Manager criados pelo CloudFormation.
# Execute após o deploy do stack 02-storage e antes do stack 04-ecs.
#
# Uso:
#   export AWS_REGION=us-east-1
#   bash infra/scripts/aws-secrets-setup.sh
#
# O script pede cada valor interativamente para não expô-los no histórico do shell.

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"

read_secret() {
    local prompt="$1"
    local value
    read -rsp "$prompt: " value
    echo
    echo "$value"
}

echo "=== IM Platform — AWS Secrets Manager Setup ==="
echo "Region: $REGION"
echo ""

# ── im/db-password ────────────────────────────────────────────────────────────
echo "--- PostgreSQL password ---"
DB_PASS=$(read_secret "POSTGRES_PASSWORD")

# Build DATABASE_URL values (usados pelas aplicações)
DB_URL="postgresql://datathon:${DB_PASS}@postgres.im.local:5432/datathon"
PREFECT_DB_URL="postgresql+asyncpg://datathon:${DB_PASS}@postgres.im.local:5432/prefect"
MLFLOW_DB_URL="postgresql+psycopg2://datathon:${DB_PASS}@postgres.im.local:5432/mlflow"

aws secretsmanager put-secret-value \
    --region "$REGION" \
    --secret-id im/db-password \
    --secret-string "{
        \"POSTGRES_PASSWORD\":\"${DB_PASS}\",
        \"DATABASE_URL\":\"${DB_URL}\",
        \"PREFECT_API_DATABASE_CONNECTION_URL\":\"${PREFECT_DB_URL}\",
        \"MLFLOW_BACKEND_STORE_URI\":\"${MLFLOW_DB_URL}\"
    }"
echo "✓ im/db-password atualizado"

# ── im/openai ─────────────────────────────────────────────────────────────────
echo ""
echo "--- OpenAI API Key ---"
OPENAI_KEY=$(read_secret "OPENAI_API_KEY")

aws secretsmanager put-secret-value \
    --region "$REGION" \
    --secret-id im/openai \
    --secret-string "{\"OPENAI_API_KEY\":\"${OPENAI_KEY}\"}"
echo "✓ im/openai atualizado"

# ── im/noip ───────────────────────────────────────────────────────────────────
echo ""
echo "--- No-IP DDNS credentials ---"
NOIP_USER=$(read_secret "NOIP_USERNAME (e-mail ou usuário no-ip)")
NOIP_PASS=$(read_secret "NOIP_PASSWORD")
NOIP_HOST=$(read_secret "NOIP_HOST (ex: meuhost.ddns.net)")

aws secretsmanager put-secret-value \
    --region "$REGION" \
    --secret-id im/noip \
    --secret-string "{
        \"NOIP_USERNAME\":\"${NOIP_USER}\",
        \"NOIP_PASSWORD\":\"${NOIP_PASS}\",
        \"NOIP_HOST\":\"${NOIP_HOST}\"
    }"
echo "✓ im/noip atualizado"

# ── im/tailscale ──────────────────────────────────────────────────────────────
echo ""
echo "--- Tailscale Auth Key ---"
echo "  Gere em: https://login.tailscale.com/admin/settings/keys"
echo "  Tipo: Reusable, expiration longa, tag: tag:ecs-private"
TS_KEY=$(read_secret "TS_AUTHKEY")

aws secretsmanager put-secret-value \
    --region "$REGION" \
    --secret-id im/tailscale \
    --secret-string "{\"TS_AUTHKEY\":\"${TS_KEY}\"}"
echo "✓ im/tailscale atualizado"

# ── im/grafana ────────────────────────────────────────────────────────────────
echo ""
echo "--- Grafana Admin Password ---"
GRAFANA_PASS=$(read_secret "GF_SECURITY_ADMIN_PASSWORD")

aws secretsmanager put-secret-value \
    --region "$REGION" \
    --secret-id im/grafana \
    --secret-string "{\"GF_SECURITY_ADMIN_PASSWORD\":\"${GRAFANA_PASS}\"}"
echo "✓ im/grafana atualizado"

echo ""
echo "=== Todos os secrets atualizados com sucesso! ==="
echo ""
echo "Próximos passos:"
echo "  1. Deploy do stack 04-ecs: aws cloudformation deploy ..."
echo "  2. Execute postgres-init RunTask"
echo "  3. Execute prefect-deployments RunTask"
