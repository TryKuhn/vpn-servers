# ============================================================================
#  vpn-manager Dockerfile (multi-stage)
# ============================================================================
#
#  Stage 1 (builder): produces a wheel artifact from source.
#  Stage 2 (runtime): minimal image with only the wheel installed.
#
#  Final image is ~120 MB (vs ~250 MB if we shipped the build toolchain).
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: builder
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# `build` is the PEP 517 build frontend. It calls hatchling under the hood
# (per pyproject.toml's [build-system]) and produces a wheel into dist/.
RUN pip install --no-cache-dir build==1.2.1

WORKDIR /src

# Copy source. We copy pyproject.toml first to give Docker a stable layer
# even if only source code changes (in our case minor optimization since
# we copy everything anyway, but a habit worth having).
COPY pyproject.toml README.md ./
COPY src/ src/

# Build the wheel. After this, /src/dist/ contains exactly one .whl file.
RUN python -m build --wheel --no-isolation

# ----------------------------------------------------------------------------
# Stage 2: runtime
# ----------------------------------------------------------------------------
FROM python:3.12-slim

# Set sensible Python defaults for containers:
#   PYTHONDONTWRITEBYTECODE=1  — no .pyc files (saves writes, harmless in container)
#   PYTHONUNBUFFERED=1         — flush stdout immediately (critical for `docker logs`)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install runtime tools:
#   - xray:    we use its `xray api` subcommand to talk to the xray container
#              over gRPC. This is the simplest path; native gRPC in Python
#              would require .proto files and generated bindings.
#   - jq:      JSON manipulation in shell scripts (if any).
#   - libqrencode-tools (qrencode): for terminal QR rendering.
#
# We also install xray itself by downloading the binary directly to avoid
# pulling a whole separate image.
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        unzip \
        jq \
        qrencode \
        && rm -rf /var/lib/apt/lists/*

# Install xray CLI binary. We pin a recent stable version to ensure
# reproducible builds. Update XRAY_VERSION when there's a new release.
ARG XRAY_VERSION=v25.1.30
RUN curl -fsSL -o /tmp/xray.zip \
        "https://github.com/XTLS/Xray-core/releases/download/${XRAY_VERSION}/Xray-linux-64.zip" && \
    unzip -q /tmp/xray.zip xray -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/xray && \
    rm /tmp/xray.zip

# Copy the wheel from the builder stage and install it.
COPY --from=builder /src/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Create a non-root user. We don't need root inside this container —
# manager talks to xray via network (gRPC) and writes only to mounted volumes.
RUN useradd --create-home --shell /bin/bash --uid 1000 manager
USER manager
WORKDIR /home/manager

# Default command: just sit there. Real work is invoked via `docker compose exec`.
# We use `tail -f /dev/null` rather than `sleep infinity` because tail responds
# to SIGTERM faster (clean shutdown).
CMD ["tail", "-f", "/dev/null"]