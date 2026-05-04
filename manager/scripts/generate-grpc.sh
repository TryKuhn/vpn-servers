#!/usr/bin/env bash
# ============================================================================
#  generate-grpc.sh — pull xray .proto files and generate Python bindings
# ============================================================================
#
#  Clones xray-core at the pinned version, extracts .proto files into a
#  flat directory (preserving import paths), and runs protoc to generate
#  Python bindings into src/vpn_manager/xray/_generated/.
#
#  Run from the manager/ directory.
#
#  Required env: XRAY_VERSION (e.g. v25.1.30)
# ============================================================================

set -euo pipefail

# --- Config -----------------------------------------------------------------

XRAY_VERSION="${XRAY_VERSION:-v25.1.30}"
XRAY_REPO="https://github.com/XTLS/Xray-core.git"

# Where to put generated Python files.
OUT_DIR="src/vpn_manager/xray/_generated"

# Tmp dir for the xray clone. We use a deterministic path so subsequent
# runs can detect existing clones (saves time during local dev).
TMP_DIR="${XRAY_PROTO_TMP:-/tmp/xray-protos-${XRAY_VERSION}}"

# --- Sanity -----------------------------------------------------------------

if ! command -v python3 &>/dev/null; then
    echo "FATAL: python3 not found." >&2
    exit 1
fi

if ! python3 -c "import grpc_tools" &>/dev/null; then
    echo "FATAL: grpcio-tools not installed." >&2
    echo "       Install with: pip install grpcio-tools" >&2
    exit 1
fi

# --- Clone xray-core --------------------------------------------------------

if [[ ! -d "$TMP_DIR" ]]; then
    echo "→ Cloning xray-core $XRAY_VERSION..."
    git clone --depth 1 --branch "$XRAY_VERSION" "$XRAY_REPO" "$TMP_DIR" \
        > /dev/null 2>&1
else
    echo "→ Using cached xray-core at $TMP_DIR"
fi

# --- Find all .proto files we need ------------------------------------------

# We start with command.proto (the API entrypoint) and let protoc figure out
# transitive imports based on the proto_path.
echo "→ Finding .proto files..."

# Collect ALL proto files from the xray repo. The `proxyman/command` proto
# imports from many other directories (common, transport, proxy/*, etc.),
# and rather than tracking them by hand we just include everything.
mapfile -t PROTO_FILES < <(find "$TMP_DIR" -name '*.proto' -type f | sort)

if [[ ${#PROTO_FILES[@]} -eq 0 ]]; then
    echo "FATAL: no .proto files found in $TMP_DIR" >&2
    exit 1
fi

echo "  found ${#PROTO_FILES[@]} proto files"

# --- Generate bindings ------------------------------------------------------

echo "→ Generating Python bindings into $OUT_DIR..."

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# protoc settings:
#   --proto_path=$TMP_DIR  — root for resolving import paths in .proto files
#   --python_out           — output dir for messages
#   --grpc_python_out      — output dir for gRPC service stubs
#
# We use `python -m grpc_tools.protoc` (not the system protoc) because
# grpcio-tools ships its own bundled protoc that's guaranteed to be
# compatible with the grpcio runtime.
python3 -m grpc_tools.protoc \
    --proto_path="$TMP_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "${PROTO_FILES[@]}"

# --- Make it a Python package ----------------------------------------------

# protoc creates directory structure mirroring the proto package paths.
# Add empty __init__.py everywhere so Python sees them as packages.
find "$OUT_DIR" -type d -exec touch {}/__init__.py \;

# Top-level __init__.py for vpn_manager.xray._generated
touch "$OUT_DIR/__init__.py"

echo "✓ Generated bindings:"
find "$OUT_DIR" -name "*_pb2.py" -o -name "*_pb2_grpc.py" | sort | head -20
echo "  ..."
echo "  total: $(find "$OUT_DIR" -name "*.py" | wc -l) files"
