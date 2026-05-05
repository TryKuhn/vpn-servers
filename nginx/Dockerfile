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

# Conf templates are rendered with envsubst at startup. The template name
# must end in .conf.template - the entrypoint will produce conf.d/X.conf.
COPY templates/ /etc/nginx/templates/
