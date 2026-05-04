# ============================================================================
#  vpn-manager Dockerfile (multi-stage)
# ============================================================================
#
#  Stage 1 (builder):
#    - Generates Python gRPC bindings from xray-core .proto files.
#    - Builds the manager wheel including those bindings.
#
#  Stage 2 (runtime):
#    - Minimal image with only the wheel and runtime deps.
# ============================================================================

ARG XRAY_VERSION=v25.1.30

# ----------------------------------------------------------------------------
# Stage 1: builder
# ----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ARG XRAY_VERSION

# We need git (to clone xray-core for proto files) and the build chain.
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        git \
        && rm -rf /var/lib/apt/lists/*

# Install build tools and grpcio-tools (for proto -> python codegen).
RUN pip install --no-cache-dir \
        build==1.2.1 \
        hatchling==1.25.0 \
        grpcio-tools==1.66.2

WORKDIR /src

# Copy source.
COPY pyproject.toml README.md ./
COPY src/ src/
COPY scripts/ scripts/

# Generate gRPC bindings. The script clones xray-core at $XRAY_VERSION
# and writes Python bindings into src/vpn_manager/xray/_generated/.
RUN XRAY_VERSION="${XRAY_VERSION}" bash scripts/generate-grpc.sh

# Build the wheel. The wheel will include the just-generated bindings
# because they live under src/vpn_manager/xray/_generated/ which is part
# of the package.
RUN python -m build --wheel --no-isolation

# ----------------------------------------------------------------------------
# Stage 2: runtime
# ----------------------------------------------------------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Minimal runtime tooling. Note: no `xray` binary anymore — we talk gRPC
# directly. We keep qrencode for any future shell-based tooling, and jq
# for ad-hoc debugging.
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        jq \
        qrencode \
        && rm -rf /var/lib/apt/lists/*

# Install the wheel built in stage 1.
COPY --from=builder /src/dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm /tmp/*.whl

# Non-root user.
RUN useradd --create-home --shell /bin/bash --uid 1000 manager
USER manager
WORKDIR /home/manager

CMD ["tail", "-f", "/dev/null"]
