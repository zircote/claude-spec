#!/bin/bash
# lib/config.sh - Configuration loader with user config + default fallback
#
# This library provides functions for loading claude-spec configuration
# with a fallback chain: user config -> default -> hardcoded defaults
#
# Supports auto-migration from legacy worktree-manager.config.json path.
#
# Usage:
#   source "$SCRIPT_DIR/lib/config.sh"
#   TERMINAL=$(get_config "terminal" "ghostty")
#   PORT_START=$(get_config_nested "portPool.start" "8100")

# Determine paths
_CONFIG_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_PLUGIN_ROOT="${_CONFIG_LIB_DIR}/../../../.."

# Config paths
USER_CONFIG="${HOME}/.claude/claude-spec.config.json"
OLD_USER_CONFIG="${HOME}/.claude/worktree-manager.config.json"
DEFAULT_CONFIG="${_PLUGIN_ROOT}/claude-spec.config.json"

# Auto-migrate old config if needed
if [ -f "$OLD_USER_CONFIG" ] && [ ! -f "$USER_CONFIG" ]; then
    mv "$OLD_USER_CONFIG" "$USER_CONFIG" 2>/dev/null && \
        echo "cs-config: Migrated $OLD_USER_CONFIG → $USER_CONFIG" >&2
fi

# Check if user config exists
# Returns: 0 if exists, 1 if not
has_user_config() {
    [ -f "$USER_CONFIG" ]
}

# Get the path to the active config file (user or default)
# Returns: path to config file, or empty if neither exists
get_config_path() {
    if [ -f "$USER_CONFIG" ]; then
        echo "$USER_CONFIG"
    elif [ -f "$DEFAULT_CONFIG" ]; then
        echo "$DEFAULT_CONFIG"
    else
        echo ""
    fi
}

# Get config value with fallback chain: user config -> default config -> hardcoded
# Arguments:
#   $1 - key name (e.g., "terminal", "shell")
#   $2 - default value if not found anywhere
# Returns: config value or default
get_config() {
    local key="$1"
    local default="$2"

    # If jq not available, return default
    if ! command -v jq &> /dev/null; then
        echo "$default"
        return
    fi

    local value=""

    # Try user config first
    if [ -f "$USER_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$USER_CONFIG" 2>/dev/null)
    fi

    # Fall back to default config if user config didn't have it
    if [ -z "$value" ] && [ -f "$DEFAULT_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$DEFAULT_CONFIG" 2>/dev/null)
    fi

    # Fall back to hardcoded default if still empty
    if [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# Get nested config value (e.g., portPool.start)
# Arguments:
#   $1 - dot-notation key (e.g., "portPool.start")
#   $2 - default value if not found anywhere
# Returns: config value or default
get_config_nested() {
    local key="$1"
    local default="$2"

    # If jq not available, return default
    if ! command -v jq &> /dev/null; then
        echo "$default"
        return
    fi

    local value=""

    # Try user config first
    if [ -f "$USER_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$USER_CONFIG" 2>/dev/null)
    fi

    # Fall back to default config
    if [ -z "$value" ] && [ -f "$DEFAULT_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$DEFAULT_CONFIG" 2>/dev/null)
    fi

    # Fall back to hardcoded default
    if [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}

# Check if config setup is needed (no user config exists)
# Returns: 0 if setup needed, 1 if user config exists
needs_setup() {
    ! has_user_config
}

# Get detected shell from environment
# Returns: shell name (bash, zsh, fish, or bash as default)
detect_shell() {
    case "$SHELL" in
        */bash) echo "bash" ;;
        */zsh)  echo "zsh" ;;
        */fish) echo "fish" ;;
        *)      echo "bash" ;;
    esac
}

# Display current config summary (for debugging/setup)
show_config_summary() {
    echo "Claude Spec Configuration"
    echo "========================="
    if has_user_config; then
        echo "Source: User config ($USER_CONFIG)"
    elif [ -f "$DEFAULT_CONFIG" ]; then
        echo "Source: Default config ($DEFAULT_CONFIG)"
    else
        echo "Source: Hardcoded defaults"
    fi
    echo ""
    echo "Current values:"
    echo "  terminal:      $(get_config "terminal" "ghostty")"
    echo "  shell:         $(get_config "shell" "bash")"
    echo "  claudeCommand: $(get_config "claudeCommand" "claude")"
    echo "  worktreeBase:  $(get_config "worktreeBase" "$HOME/Projects/worktrees")"
    echo "  portPool:      $(get_config_nested "portPool.start" "8100")-$(get_config_nested "portPool.end" "8199")"
}

# =============================================================================
# Lifecycle Configuration Functions
# =============================================================================

# Get lifecycle steps for a specific command and phase
# Arguments:
#   $1 - command name (e.g., "claude-spec:complete", "claude-spec:plan")
#   $2 - phase ("preSteps" or "postSteps")
# Returns: JSON array of steps, or "[]" if not found
get_lifecycle_steps() {
    local command="$1"
    local phase="$2"

    # If jq not available, return empty array
    if ! command -v jq &> /dev/null; then
        echo "[]"
        return
    fi

    # Build the jq path for lifecycle.commands.<command>.<phase>
    # Properly escape the command for use as a jq object key
    local escaped_command
    escaped_command=$(printf '%s' "$command" | jq -R .)
    local jq_path=".lifecycle.commands[${escaped_command}].${phase}"
    local value=""

    # Try user config first
    if [ -f "$USER_CONFIG" ]; then
        value=$(jq -r "${jq_path} // empty" "$USER_CONFIG" 2>/dev/null)
    fi

    # Fall back to default config
    if [ -z "$value" ] && [ -f "$DEFAULT_CONFIG" ]; then
        value=$(jq -r "${jq_path} // empty" "$DEFAULT_CONFIG" 2>/dev/null)
    fi

    # Return value or empty array
    if [ -z "$value" ] || [ "$value" = "null" ]; then
        echo "[]"
    else
        echo "$value"
    fi
}

# Check if session start context loading is enabled for a specific type
# Arguments:
#   $1 - context type ("claudeMd", "gitState", "projectStructure")
# Returns: 0 if enabled (true), 1 if disabled (false)
is_session_context_enabled() {
    local context_type="$1"
    local enabled

    enabled=$(get_config_nested "lifecycle.sessionStart.loadContext.${context_type}" "true")

    [ "$enabled" = "true" ]
}

# Check if session start is globally enabled
# Returns: 0 if enabled, 1 if disabled
is_session_start_enabled() {
    local enabled
    enabled=$(get_config_nested "lifecycle.sessionStart.enabled" "true")
    [ "$enabled" = "true" ]
}

# Get all enabled pre-steps for a command
# Arguments:
#   $1 - command name (e.g., "claude-spec:complete")
# Returns: JSON array of enabled steps only
get_enabled_pre_steps() {
    local command="$1"
    local steps

    steps=$(get_lifecycle_steps "$command" "preSteps")

    # If jq available, filter to enabled only
    if command -v jq &> /dev/null; then
        echo "$steps" | jq '[.[] | select(.enabled == true)]' 2>/dev/null || echo "[]"
    else
        echo "[]"
    fi
}

# Get all enabled post-steps for a command
# Arguments:
#   $1 - command name (e.g., "claude-spec:complete")
# Returns: JSON array of enabled steps only
get_enabled_post_steps() {
    local command="$1"
    local steps

    steps=$(get_lifecycle_steps "$command" "postSteps")

    # If jq available, filter to enabled only
    if command -v jq &> /dev/null; then
        echo "$steps" | jq '[.[] | select(.enabled == true)]' 2>/dev/null || echo "[]"
    else
        echo "[]"
    fi
}
