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

# --- Generate keys via xray container ---------------------------------------

echo "→ Generating x25519 keypair via xray..."

# Use the same image we'll use in production to ensure compatibility.
key_output=$(docker run --rm teddysun/xray xray x25519)

priv=$(echo "$key_output" | grep -oP 'Private key:\s*\K\S+')
pub=$(echo "$key_output" | grep -oP 'Public key:\s*\K\S+')

if [[ -z "$priv" || -z "$pub" ]]; then
    echo "ERROR: failed to parse xray x25519 output:" >&2
    echo "$key_output" >&2
    exit 1
fi

# --- Generate short ID ------------------------------------------------------

echo "→ Generating short ID..."
sid=$(openssl rand -hex 8)

# --- Patch .env -------------------------------------------------------------

echo "→ Writing keys to $ENV_FILE..."

# We use a temp file to avoid partial writes if something goes wrong.
tmp=$(mktemp)
trap "rm -f $tmp" EXIT

awk -v priv="$priv" -v pub="$pub" -v sid="$sid" '
    /^PRIVATE_KEY=/ { print "PRIVATE_KEY=" priv; next }
    /^PUBLIC_KEY=/  { print "PUBLIC_KEY=" pub; next }
    /^SHORT_ID=/    { print "SHORT_ID=" sid; next }
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
echo ""
echo "Next steps:"
echo "  1. Verify other vars in $ENV_FILE (SERVER_IP, SNI, etc.)"
echo "  2. Run: make up"
