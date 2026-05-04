#!/bin/sh
# ============================================================================
#  entrypoint.sh — validate and run xray
# ============================================================================
#
#  By the time this runs, the config-init container has already rendered
#  the config from the template. We just validate it and exec xray.
# ============================================================================

set -e

CONFIG="/etc/xray/config.json"

if [ ! -f "$CONFIG" ]; then
    echo "FATAL: $CONFIG not found." >&2
    echo "       config-init service should have rendered it. Check:" >&2
    echo "         docker compose logs config-init" >&2
    exit 1
fi

# Validate JSON & xray semantics. Fails fast with a useful message.
if ! xray -test -config "$CONFIG" >/dev/null 2>&1; then
    echo "FATAL: $CONFIG failed xray validation. Dumping for debug:" >&2
    cat "$CONFIG" >&2
    exit 1
fi

echo "✓ Config validated. Starting xray..."
exec xray run -config "$CONFIG"
