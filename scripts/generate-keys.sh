#!/usr/bin/env bash
# ============================================================================
#  generate-keys.sh — generate Reality keys and write to .env
# ============================================================================
#
#  Generates:
#    - x25519 keypair (PRIVATE_KEY + PUBLIC_KEY) for Reality
#    - random 8-byte SHORT_ID
#
#  Then patches .env in-place to fill in the generated values.
#
#  Idempotent: refuses to overwrite existing keys unless --force is passed.
# ============================================================================

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env}"
FORCE=0

for arg in "$@"; do
    case "$arg" in
        --force|-f) FORCE=1 ;;
        --help|-h)
            echo "Usage: $0 [--force]"
            echo "  --force    overwrite existing keys in $ENV_FILE"
            exit 0
            ;;
    esac
done

# --- Sanity checks ----------------------------------------------------------

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: $ENV_FILE not found. Run \`cp .env.example .env\` first." >&2
    exit 1
fi

# Check we have the tools we need
need_tool() {
    if ! command -v "$1" &>/dev/null; then
        echo "ERROR: '$1' is not installed." >&2
        echo "$2" >&2
        exit 1
    fi
}

need_tool docker "Install Docker first (run scripts/install.sh)."
need_tool openssl "Install with: apt install openssl"

# --- Detect existing keys ---------------------------------------------------

current_priv=$(grep -E '^PRIVATE_KEY=' "$ENV_FILE" | cut -d= -f2-)
if [[ -n "$current_priv" && "$FORCE" -eq 0 ]]; then
    echo "ERROR: PRIVATE_KEY is already set in $ENV_FILE." >&2
    echo "Use --force to overwrite (existing clients will be invalidated!)." >&2
    exit 1
fi

current_ws_path=$(grep -E '^WS_PATH=' "$ENV_FILE" | cut -d= -f2-)
if [[ -n "$current_ws_path" && "$FORCE" -eq 0 ]]; then
    echo "ERROR: WS_PATH is already set in $ENV_FILE." >&2
    echo "Use --force to overwrite (existing WS clients will be invalidated!)." >&2
    exit 1
fi

# --- Generate keys via xray container ---------------------------------------

echo "→ Generating x25519 keypair via xray..."

# Use the same image we'll use in production to ensure compatibility.
key_output=$(docker run --rm teddysun/xray xray x25519)

# xray output format has varied across versions:
#   Older:  "Private key: ..."        / "Public key: ..."
#   Newer:  "PrivateKey: ..."         / "Password (PublicKey): ..."
# Match either by accepting "Private" with optional space and the literal
# word "Key" (case-insensitive). Same for Public.
priv=$(echo "$key_output" | grep -oP '(?i)private\s*key:?\s*\K\S+' | head -1)
pub=$(echo "$key_output"  | grep -oP '(?i)public\s*key\)?:?\s*\K\S+' | head -1)

if [[ -z "$priv" || -z "$pub" ]]; then
    echo "ERROR: failed to parse xray x25519 output." >&2
    echo "       This usually means xray's output format changed." >&2
    echo "       Raw output was:" >&2
    echo "       ----------------------------------------" >&2
    echo "$key_output" | sed 's/^/       /' >&2
    echo "       ----------------------------------------" >&2
    echo "       Please open an issue with this output." >&2
    exit 1
fi

# --- Generate short ID ------------------------------------------------------

echo "→ Generating short ID..."
sid=$(openssl rand -hex 8)

# --- Generate WebSocket path ------------------------------------------------

echo "→ Generating WebSocket path..."
ws_path=$(openssl rand -hex 16)

# --- Patch .env -------------------------------------------------------------

echo "→ Writing keys to $ENV_FILE..."

# We use a temp file to avoid partial writes if something goes wrong.
tmp=$(mktemp)
trap "rm -f $tmp" EXIT

awk -v priv="$priv" -v pub="$pub" -v sid="$sid" -v ws_path="$ws_path" '
    /^PRIVATE_KEY=/ { print "PRIVATE_KEY=" priv; next }
    /^PUBLIC_KEY=/  { print "PUBLIC_KEY=" pub; next }
    /^SHORT_ID=/    { print "SHORT_ID=" sid; next }
    /^WS_PATH=/     { print "WS_PATH=" ws_path; next }
    { print }
' "$ENV_FILE" > "$tmp"

mv "$tmp" "$ENV_FILE"
chmod 600 "$ENV_FILE"

# --- Done -------------------------------------------------------------------

echo ""
echo "✓ Keys generated and saved to $ENV_FILE"
echo ""
echo "  PRIVATE_KEY: <hidden>"
echo "  PUBLIC_KEY:  $pub"
echo "  SHORT_ID:    $sid"
echo "  WS_PATH:     $ws_path"
echo ""
echo "Next steps:"
echo "  1. Verify other vars in $ENV_FILE (SERVER_IP, SNI, etc.)"
echo "  2. Run: make up"
