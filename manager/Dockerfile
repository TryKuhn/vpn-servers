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
#   PYTHONUNB
