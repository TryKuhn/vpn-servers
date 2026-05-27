#!/usr/bin/env bash
set -euo pipefail
[ -f rendered/haproxy/haproxy.cfg ] || { echo "Missing rendered/haproxy/haproxy.cfg"; exit 1; }
[ -f rendered/xray/config.json ] || { echo "Missing rendered/xray/config.json"; exit 1; }
[ -f rendered/hysteria/config.yaml ] || { echo "Missing rendered/hysteria/config.yaml"; exit 1; }
[ -f rendered/naive/Caddyfile ] || { echo "Missing rendered/naive/Caddyfile"; exit 1; }
echo "→ checking unresolved placeholders"
if grep -RInE '\$\{[A-Za-z_][A-Za-z0-9_]*\}|__(XRAY_CLIENTS|HYSTERIA_USERPASS|NAIVE_BASIC_AUTH)__' rendered; then
  echo "✗ rendered configs contain unreplaced placeholders"
  exit 1
fi
echo "→ docker compose config"
docker compose config -q
echo "→ validate HAProxy"
TMP_HAPROXY_CFG="$(mktemp)"
sed \
  -e 's/server xray xray:1443 check/server xray 127.0.0.1:1443 check/' \
  -e 's/server naive naive:2443 check/server naive 127.0.0.1:2443 check/' \
  rendered/haproxy/haproxy.cfg > "$TMP_HAPROXY_CFG"

docker run --rm \
  -v "$TMP_HAPROXY_CFG:/usr/local/etc/haproxy/haproxy.cfg:ro" \
  "haproxy:${HAPROXY_VERSION:-3.0-alpine}" \
  haproxy -c -f /usr/local/etc/haproxy/haproxy.cfg

rm -f "$TMP_HAPROXY_CFG"
echo "→ validate Xray"
docker run --rm -v "$PWD/rendered/xray/config.json:/etc/xray/config.json:ro" "ghcr.io/xtls/xray-core:${XRAY_VERSION:-latest}" run -test -c /etc/xray/config.json
echo "→ validate Caddy/Naive"
docker compose build naive >/dev/null
docker compose run --rm --no-deps naive caddy validate --config /etc/caddy/Caddyfile
echo "✓ rendered configs valid"
