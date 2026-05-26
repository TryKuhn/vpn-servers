#!/bin/sh
# ============================================================================
#  render-config.sh — render xray config from template
# ============================================================================
#
#  Runs in a one-shot init container with envsubst available. Reads the
#  template, substitutes env vars, writes the result to the shared volume.
# ============================================================================

set -e

TEMPLATE="/templates/config.template.json"
OUTPUT="/output/config.json"

# --- Sanity ------------------------------------------------------------------

if [ ! -f "$TEMPLATE" ]; then
    echo "FATAL: template not found at $TEMPLATE" >&2
    exit 1
fi

require_var() {
    eval "val=\$$1"
    if [ -z "$val" ]; then
        echo "FATAL: required env var $1 is empty." >&2
        echo "       Did you run 'make init' to generate keys?" >&2
        exit 1
    fi
}

require_var SNI
require_var DEST
require_var PRIVATE_KEY
require_var SHORT_ID

# --- Render ------------------------------------------------------------------

mkdir -p "$(dirname "$OUTPUT")"

# Pass an explicit list of vars to envsubst — only those will be substituted.
# This prevents accidental substitution of unrelated $-things in the template.
envsubst '${SNI} ${DEST} ${PRIVATE_KEY} ${SHORT_ID}' \
    < "$TEMPLATE" > "$OUTPUT"

echo "✓ Rendered config:"
echo "    template: $TEMPLATE"
echo "    output:   $OUTPUT"
