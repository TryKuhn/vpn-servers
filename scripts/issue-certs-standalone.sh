#!/usr/bin/env bash
set -euo pipefail
if [ ! -f .env ]; then echo "Missing .env"; exit 1; fi
set -a; source .env; set +a
DOMAINS=(-d "$PUBLIC_DOMAIN" -d "$NAIVE_DOMAIN" -d "$HYSTERIA_DOMAIN")
if [ "${SUB_DOMAIN:-$PUBLIC_DOMAIN}" != "$PUBLIC_DOMAIN" ] && [ "${SUB_DOMAIN:-}" != "$NAIVE_DOMAIN" ] && [ "${SUB_DOMAIN:-}" != "$HYSTERIA_DOMAIN" ]; then DOMAINS+=(-d "$SUB_DOMAIN"); fi
mkdir -p certs
echo "→ Stopping stack to free port 80 for standalone certbot"
docker compose down || true
docker run --rm -p 80:80 -v "$PWD/certs/letsencrypt:/etc/letsencrypt" certbot/certbot certonly --standalone --non-interactive --agree-tos --register-unsafely-without-email "${DOMAINS[@]}"
PRIMARY="$PUBLIC_DOMAIN"
cp "certs/letsencrypt/live/$PRIMARY/fullchain.pem" certs/fullchain.pem
cp "certs/letsencrypt/live/$PRIMARY/privkey.pem" certs/privkey.pem
chmod 600 certs/privkey.pem
echo "✓ certs written to certs/fullchain.pem and certs/privkey.pem"
