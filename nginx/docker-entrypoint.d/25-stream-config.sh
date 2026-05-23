#!/bin/sh
# Process the SNI-routing stream config template and write it to stream.d/
# so the stream {} block in nginx.conf can include it.
set -e

mkdir -p /etc/nginx/stream.d

envsubst '${NGINX_DOMAIN}' \
    < /etc/nginx/stream-templates/sni-routing.conf.template \
    > /etc/nginx/stream.d/sni-routing.conf

echo "25-stream-config.sh: SNI routing configured (${NGINX_DOMAIN} -> :4430, default -> :8443)"
