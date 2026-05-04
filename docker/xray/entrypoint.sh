#!/bin/sh
# ============================================================================
#  entrypoint.sh — render config and exec xray
# ============================================================================
#
#  Runs inside the xray container. Substitutes environment variables in
#  the config template and writes the result to /etc/xray/config.json,
#  then execs the real xray binary.
# ============================================================================

set -e

TEMPLATE="/templates/config.template.json"
OUTPUT="/etc/xray/config.json"

# --- Sanity checks ----------------------------------------------------------

if [ ! -f "$TEMPLATE" ]; then
    echo "FATAL: template not found at $TEMPLATE" >&2
    exit 1
fi

# Make sure required vars are set. Fail fast with a clear message.
require_var() {
    eval "val=\$$1"
    if [ -z "$val" ]; then
        echo "FATAL: required env var $1 is empty." >&2
        echo "       Did you run 'make init' to generate keys?" >&2
        exit 1
    fi
}

require_var SERVER_PORT
require_var SNI
require_var DEST
require_var PRIVATE_KEY
require_var SHORT_ID

# --- Render -----------------------------------------------------------------

mkdir -p "$(dirname "$OUTPUT")"

# envsubst is lightweight and exactly what we need — no full shell expansion,
# only variable substitution. Avoids accidental escaping issues.
#
# We pass an explicit list of vars so envsubst doesn't touch other $-things
# in the template (in case xray ever uses them, which it currently doesn't).
envsubst '${SERVER_PORT} ${SNI} ${DEST} ${PRIVATE_KEY} ${SHORT_ID}' \
    < "$TEMPLATE" > "$OUTPUT"

echo "→ Rendered config:"
echo "    template: $TEMPLATE"
echo "    output:   $OUTPUT"

# --- Validate JSON ----------------------------------------------------------

# Quick sanity: make sure the output is valid JSON.
# xray would also catch this, but failing early gives a cleaner error.
if ! xray -test -config "$OUTPUT" >/dev/null 2>&1; then
    echo "FATAL: rendered config failed xray validation. Dumping for debug:" >&2
    cat "$OUTPUT" >&2
    exit 1
fi

echo "✓ Config validated. Starting xray..."
echo ""

# --- Exec xray --------------------------------------------------------------

# `exec` replaces the shell process with xray, so PID 1 in the container
# is xray itself. This means signals (SIGTERM on `docker stop`) reach it
# directly, allowing for clean shutdown.
exec xray run -config "$OUTPUT"
