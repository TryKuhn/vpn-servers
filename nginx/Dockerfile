# Nginx + Certbot for HTTPS subscription endpoint with auto-renewing
# Let's Encrypt certificates.
#
# Image: jonasal/nginx-certbot
#   - Bundles nginx + certbot in one container
#   - Reads conf.d/*.conf for site config
#   - Templates with $variables get rendered from env vars at startup
#   - Runs certbot on first start to get certs, then on a 12h timer for renewal
#
# Pinned to a specific tag - never use :latest in production.

FROM jonasal/nginx-certbot:5.4.1-alpine

# Override the default nginx.conf to add the stream {} block for SNI routing.
COPY nginx.conf /etc/nginx/nginx.conf

# HTTP templates: rendered by the upstream 20-envsubst script into conf.d/.
COPY templates/ /etc/nginx/templates/

# Stream template: rendered by 25-stream-config.sh into stream.d/ at startup.
COPY stream/ /etc/nginx/stream-templates/

# Custom entrypoint hook: runs before nginx starts, processes the stream template.
# Numbered 25- so it runs after the HTTP template envsubst (20-) but before nginx start.
COPY 25-stream-config.sh /docker-entrypoint.d/25-stream-config.sh
RUN chmod +x /docker-entrypoint.d/25-stream-config.sh
