#!/bin/bash
# launch-agent.sh - Terminal-aware Claude Code launcher for worktrees
# Reads terminal preference from ~/.claude/worktree-manager.config.json
set -e

WORKTREE_PATH="${1:?Missing worktree path argument}"
INITIAL_PROMPT="${2:-}"
CONFIG_FILE="${HOME}/.claude/worktree-manager.config.json"

# Read preferences from config (with defaults)
if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    TERMINAL=$(jq -r '.terminal // "iterm2-tab"' "$CONFIG_FILE" 2>/dev/null || echo "iterm2-tab")
    CLAUDE_CMD=$(jq -r '.claudeCommand // "claude"' "$CONFIG_FILE" 2>/dev/null || echo "claude")
else
    TERMINAL="iterm2-tab"
    CLAUDE_CMD="claude"
fi

# Build the command to run in the new terminal
if [ -n "$INITIAL_PROMPT" ]; then
    FULL_CMD="cd '${WORKTREE_PATH}' && ${CLAUDE_CMD} '${INITIAL_PROMPT}'"
else
    FULL_CMD="cd '${WORKTREE_PATH}' && ${CLAUDE_CMD}"
fi

case "$TERMINAL" in
    iterm2-tab)
        osascript <<EOF
tell application "iTerm2"
    activate
    tell current window
        create tab with default profile
        tell current session
            write text "${FULL_CMD}"
        end tell
    end tell
end tell
EOF
        ;;

    iterm2-window)
        osascript <<EOF
tell application "iTerm2"
    activate
    set newWindow to (create window with default profile)
    tell current session of newWindow
        write text "${FULL_CMD}"
    end tell
end tell
EOF
        ;;

    ghostty)
        if command -v ghostty &> /dev/null; then
            # Ghostty uses different syntax for commands
            ghostty --working-directory="${WORKTREE_PATH}" -e ${CLAUDE_CMD} ${INITIAL_PROMPT:+"$INITIAL_PROMPT"} &
        else
            echo "ERROR: ghostty not found in PATH" >&2
            exit 1
        fi
        ;;

    tmux)
        if command -v tmux &> /dev/null; then
            # Check if tmux server is running
            if ! tmux list-sessions &>/dev/null; then
                echo "Starting new tmux session..." >&2
                tmux new-session -d -s worktrees -c "${WORKTREE_PATH}"
                tmux send-keys -t worktrees "${CLAUDE_CMD}${INITIAL_PROMPT:+ '$INITIAL_PROMPT'}" Enter
            else
                tmux new-window -c "${WORKTREE_PATH}" "${CLAUDE_CMD}${INITIAL_PROMPT:+ '$INITIAL_PROMPT'}"
            fi
        else
            echo "ERROR: tmux not found in PATH" >&2
            exit 1
        fi
        ;;

    terminal|Terminal.app)
        osascript <<EOF
tell application "Terminal"
    activate
    do script "${FULL_CMD}"
end tell
EOF
        ;;

    wezterm)
        if command -v wezterm &> /dev/null; then
            wezterm cli spawn --cwd "${WORKTREE_PATH}" -- ${CLAUDE_CMD} ${INITIAL_PROMPT:+"$INITIAL_PROMPT"} &
        else
            echo "ERROR: wezterm not found in PATH" >&2
            exit 1
        fi
        ;;

    alacritty)
        if command -v alacritty &> /dev/null; then
            alacritty --working-directory "${WORKTREE_PATH}" -e ${CLAUDE_CMD} ${INITIAL_PROMPT:+"$INITIAL_PROMPT"} &
        else
            echo "ERROR: alacritty not found in PATH" >&2
            exit 1
        fi
        ;;

    kitty)
        if command -v kitty &> /dev/null; then
            kitty --directory "${WORKTREE_PATH}" ${CLAUDE_CMD} ${INITIAL_PROMPT:+"$INITIAL_PROMPT"} &
        else
            echo "ERROR: kitty not found in PATH" >&2
            exit 1
        fi
        ;;

    *)
        echo "ERROR: Unknown terminal type: $TERMINAL" >&2
        echo "Supported terminals: iterm2-tab, iterm2-window, ghostty, tmux, terminal, wezterm, alacritty, kitty" >&2
        exit 1
        ;;
esac

echo "[OK] Claude agent launched in $TERMINAL"
