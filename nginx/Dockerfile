# syntax=docker/dockerfile:1
FROM jonasal/nginx-certbot:5.4.1-alpine
COPY nginx.conf /etc/nginx/nginx.conf
COPY templates/ /etc/nginx/templates/
COPY stream/ /etc/nginx/stream-templates/
COPY 25-envsubst-stream.sh /docker-entrypoint.d/25-envsubst-stream.sh
RUN chmod +x /docker-entrypoint.d/25-envsubst-stream.sh
