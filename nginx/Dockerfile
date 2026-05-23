# syntax=docker/dockerfile:1
#
# Nginx + Certbot for HTTPS subscription endpoint with auto-renewing
# Let's Encrypt certificates, plus SNI-based stream routing on port 443.
#
# Image: jonasal/nginx-certbot
#   - Bundles nginx + certbot in one container
#   - Reads conf.d/*.conf for site config (via 20-envsubst-on-templates.sh)
#   - Runs certbot on first start, then on a timer for renewal
#
# SNI routing (stream block):
#   Port 443 is shared between two backends via TLS SNI inspection:
#     NGINX_DOMAIN (trykuhn.xyz) → Nginx HTTPS on :4430 (subscription + WS)
#     any other SNI              → Xray Reality on :8443
#   This allows VLESS+Reality clients to use port 443, bypassing ISP blocks.

FROM jonasal/nginx-certbot:5.4.1-alpine

# HTTP conf templates — rendered by the upstream 20-envsubst script into conf.d/.
COPY templates/ /etc/nginx/templates/

# Override nginx.conf to add stream {} block, and bake in all helper files.
# Everything is embedded here so no external files need to be tracked in git.
RUN <<'EOF' sh
# --- nginx.conf: add stream {} block alongside the http {} block ---
cat > /etc/nginx/nginx.conf << 'NGINX_CONF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log notice;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
}

http {
    include      /etc/nginx/mime.types;
    default_type application/octet-stream;
    access_log   /var/log/nginx/access.log;
    sendfile     on;
    keepalive_timeout 65;
    server_tokens off;
    include /etc/nginx/conf.d/*.conf;
}

# SNI-based routing: port 443 is shared between Nginx HTTPS and Xray Reality.
stream {
    include /etc/nginx/stream.d/*.conf;
}
NGINX_CONF

# --- stream template: SNI map processed by 25-stream-config.sh at startup ---
mkdir -p /etc/nginx/stream-templates
cat > /etc/nginx/stream-templates/sni-routing.conf.template << 'STREAM_CONF'
map $ssl_preread_server_name $backend_443 {
    ${NGINX_DOMAIN}  127.0.0.1:4430;
    default          127.0.0.1:8443;
}

server {
    listen 443;
    ssl_preread on;
    proxy_pass $backend_443;
    proxy_connect_timeout 10s;
    proxy_timeout 86400s;
}
STREAM_CONF

# --- entrypoint hook: runs before nginx, processes the stream template ---
cat > /docker-entrypoint.d/25-stream-config.sh << 'HOOK_SCRIPT'
#!/bin/sh
set -e
mkdir -p /etc/nginx/stream.d
envsubst '${NGINX_DOMAIN}' \
    < /etc/nginx/stream-templates/sni-routing.conf.template \
    > /etc/nginx/stream.d/sni-routing.conf
echo "25-stream-config.sh: SNI routing configured (${NGINX_DOMAIN}->:4430, default->:8443)"
HOOK_SCRIPT
chmod +x /docker-entrypoint.d/25-stream-config.sh
EOF
