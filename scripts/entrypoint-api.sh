#!/bin/sh
set -e

# Update No-IP DDNS with the current public IP of this ECS task
PUBLIC_IP=$(curl -sf --max-time 10 https://api.ipify.org)

if [ -n "$PUBLIC_IP" ] && [ -n "$NOIP_USERNAME" ] && [ -n "$NOIP_PASSWORD" ] && [ -n "$NOIP_HOST" ]; then
    RESPONSE=$(curl -sf --max-time 10 \
        "https://${NOIP_USERNAME}:${NOIP_PASSWORD}@dynupdate.no-ip.com/nic/update?hostname=${NOIP_HOST}&myip=${PUBLIC_IP}")
    echo "No-IP update: ip=${PUBLIC_IP} response=${RESPONSE}"
else
    echo "No-IP: skipping update (missing env vars or could not resolve public IP)"
fi

exec uvicorn platform_api.main:app --host 0.0.0.0 --port 8000
