#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "Missing .env"
  exit 1
fi

set -a
source .env
set +a

DOMAINS=(-d "$PUBLIC_DOMAIN")

if [ -n "${NAIVE_DOMAIN:-}" ] && [ "$NAIVE_DOMAIN" != "$PUBLIC_DOMAIN" ]; then
  DOMAINS+=(-d "$NAIVE_DOMAIN")
fi

if [ -n "${HYSTERIA_DOMAIN:-}" ] && [ "$HYSTERIA_DOMAIN" != "$PUBLIC_DOMAIN" ] && [ "$HYSTERIA_DOMAIN" != "${NAIVE_DOMAIN:-}" ]; then
  DOMAINS+=(-d "$HYSTERIA_DOMAIN")
fi

if [ -n "${SUB_DOMAIN:-}" ] \
  && [ "$SUB_DOMAIN" != "$PUBLIC_DOMAIN" ] \
  && [ "$SUB_DOMAIN" != "${NAIVE_DOMAIN:-}" ] \
  && [ "$SUB_DOMAIN" != "${HYSTERIA_DOMAIN:-}" ]; then
  DOMAINS+=(-d "$SUB_DOMAIN")
fi

mkdir -p certs

echo "→ Stopping stack to free port 80 for standalone certbot"
docker compose down || true

echo "→ Requesting certificate for: ${DOMAINS[*]}"
docker run --rm \
  -p 80:80 \
  -v "$PWD/certs/letsencrypt:/etc/letsencrypt" \
  certbot/certbot \
  certonly \
  --standalone \
  --non-interactive \
  --agree-tos \
  --register-unsafely-without-email \
  "${DOMAINS[@]}"

PRIMARY="$PUBLIC_DOMAIN"
LIVE_DIR="certs/letsencrypt/live/$PRIMARY"

echo "→ Copying certs from $LIVE_DIR"

sudo cp -L "$LIVE_DIR/fullchain.pem" certs/fullchain.pem
sudo cp -L "$LIVE_DIR/privkey.pem" certs/privkey.pem

sudo cp -L "$LIVE_DIR/fullchain.pem" certs/nv.fullchain.pem
sudo cp -L "$LIVE_DIR/privkey.pem" certs/nv.privkey.pem

sudo cp -L "$LIVE_DIR/fullchain.pem" certs/hy.fullchain.pem
sudo cp -L "$LIVE_DIR/privkey.pem" certs/hy.privkey.pem

OWNER="${DEPLOY_OWNER:-deploy:deploy}"
sudo chown -R "$OWNER" certs

chmod 600 certs/*.pem

echo "✓ certs written to:"
echo "  certs/fullchain.pem"
echo "  certs/privkey.pem"
echo "  certs/nv.fullchain.pem"
echo "  certs/nv.privkey.pem"
echo "  certs/hy.fullchain.pem"
echo "  certs/hy.privkey.pem"