#!/bin/bash
# lib/config.sh - Configuration loader with user config + template fallback
#
# This library provides functions for loading worktree-manager configuration
# with a fallback chain: user config -> template -> hardcoded defaults
#
# Usage:
#   source "$SCRIPT_DIR/lib/config.sh"
#   TERMINAL=$(get_config "terminal" "ghostty")
#   PORT_START=$(get_config_nested "portPool.start" "8100")

# Determine paths
_CONFIG_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_CONFIG="${HOME}/.claude/worktree-manager.config.json"
TEMPLATE_CONFIG="${_CONFIG_LIB_DIR}/../../config.template.json"

# Check if user config exists
# Returns: 0 if exists, 1 if not
has_user_config() {
    [ -f "$USER_CONFIG" ]
}

# Get the path to the active config file (user or template)
# Returns: path to config file, or empty if neither exists
get_config_path() {
    if [ -f "$USER_CONFIG" ]; then
        echo "$USER_CONFIG"
    elif [ -f "$TEMPLATE_CONFIG" ]; then
        echo "$TEMPLATE_CONFIG"
    else
        echo ""
    fi
}

# Get config value with fallback chain: user config -> template -> default
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

    # Fall back to template if user config didn't have it
    if [ -z "$value" ] && [ -f "$TEMPLATE_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$TEMPLATE_CONFIG" 2>/dev/null)
    fi

    # Fall back to default if still empty
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

    # Fall back to template
    if [ -z "$value" ] && [ -f "$TEMPLATE_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$TEMPLATE_CONFIG" 2>/dev/null)
    fi

    # Fall back to default
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
    echo "Worktree Manager Configuration"
    echo "=============================="
    if has_user_config; then
        echo "Source: User config ($USER_CONFIG)"
    elif [ -f "$TEMPLATE_CONFIG" ]; then
        echo "Source: Template ($TEMPLATE_CONFIG)"
    else
        echo "Source: Hardcoded defaults"
    fi
    echo ""
    echo "Current values:"
    echo "  terminal:      $(get_config "terminal" "ghostty")"
    echo "  shell:         $(get_config "shell" "bash")"
    echo "  claudeCommand: $(get_config "claudeCommand" "claude --dangerously-skip-permissions")"
    echo "  worktreeBase:  $(get_config "worktreeBase" "$HOME/Projects/worktrees")"
    echo "  portPool:      $(get_config_nested "portPool.start" "8100")-$(get_config_nested "portPool.end" "8199")"
}
