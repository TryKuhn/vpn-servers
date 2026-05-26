#!/bin/sh
# Process stream config templates into /etc/nginx/stream.d/ before nginx starts.
set -e
mkdir -p /etc/nginx/stream.d
for template in /etc/nginx/stream-templates/*.template; do
    [ -f "$template" ] || continue
    out="/etc/nginx/stream.d/$(basename "${template%.template}")"
    envsubst '${NGINX_DOMAIN}' < "$template" > "$out"
    echo "25-envsubst-stream.sh: $template → $out"
done
