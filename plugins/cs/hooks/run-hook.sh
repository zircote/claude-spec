#!/bin/bash
# Wrapper script to run Python hooks with uv
# Usage: run-hook.sh <hook_script.py>

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
HOOK_SCRIPT="$1"

if [ -z "$HOOK_SCRIPT" ]; then
    echo "[cs-plugin] ERROR: No hook script specified" >&2
    exit 1
fi

# Check if uv is installed
if ! command -v uv >/dev/null 2>&1; then
    echo "[cs-plugin] ERROR: uv not installed." >&2
    echo "[cs-plugin] Install: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
    echo "[cs-plugin] Or: brew install uv" >&2
    exit 0  # Exit 0 to not block Claude
fi

# Run the hook with uv
exec uv run --directory "$PLUGIN_ROOT" python "$SCRIPT_DIR/$HOOK_SCRIPT"
