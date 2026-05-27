# syntax=docker/dockerfile:1.7

FROM python:3.12-slim AS manager

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY manager/requirements.txt /app/manager/requirements.txt
RUN pip install --no-cache-dir -r /app/manager/requirements.txt

COPY manager /app/manager
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations

EXPOSE 8080

CMD ["uvicorn", "manager.app:app", "--host", "0.0.0.0", "--port", "8080"]

FROM caddy:2-builder AS naive-builder

RUN xcaddy build --with github.com/klzgrad/forwardproxy@naive

FROM caddy:2 AS naive
COPY --from=naive-builder /usr/bin/caddy /usr/bin/caddy
EXPOSE 2443
CMD ["caddy", "run", "--config", "/etc/caddy/Caddyfile", "--adapter", "caddyfile"]
