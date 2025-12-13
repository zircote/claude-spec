# /cs:wt:setup - Configure Worktree Manager

Run the interactive setup flow to configure your worktree-manager preferences.

This command creates or updates `~/.claude/worktree-manager.config.json` with your personal settings.

## When to Use

- **First time**: When you haven't configured worktree-manager yet
- **Reconfigure**: When you want to change your terminal, shell, or other settings
- **After switching terminals**: If you started using a different terminal app

## Execution Steps

### Step 1: Check Current Config

First, check if a config already exists and display current values:

```bash
CONFIG_FILE="${HOME}/.claude/worktree-manager.config.json"

if [ -f "$CONFIG_FILE" ]; then
    echo "Current configuration:"
    echo "======================"
    cat "$CONFIG_FILE" | jq '.'
    echo ""
    echo "This setup will overwrite the above configuration."
fi
```

### Step 2: Detect Shell

```bash
DETECTED_SHELL=$(basename "$SHELL")
echo "Detected shell: $DETECTED_SHELL"
```

### Step 3: Ask Configuration Questions

Use the `AskUserQuestion` tool with these 4 questions in a single call:

```json
{
  "questions": [
    {
      "header": "Terminal",
      "question": "Which terminal do you use for development?",
      "multiSelect": false,
      "options": [
        {
          "label": "iTerm2 (Recommended)",
          "description": "macOS terminal with excellent tab support"
        },
        {
          "label": "Ghostty",
          "description": "Fast, GPU-accelerated terminal"
        },
        {
          "label": "tmux",
          "description": "Terminal multiplexer (creates detached sessions)"
        }
      ]
    },
    {
      "header": "Shell",
      "question": "What shell do you use?",
      "multiSelect": false,
      "options": [
        {
          "label": "zsh (Recommended)",
          "description": "Z Shell - macOS default since Catalina"
        },
        {
          "label": "bash",
          "description": "Bourne Again Shell"
        },
        {
          "label": "fish",
          "description": "Friendly Interactive Shell"
        }
      ]
    },
    {
      "header": "Claude",
      "question": "How do you launch Claude Code?",
      "multiSelect": false,
      "options": [
        {
          "label": "claude --dangerously-skip-permissions (Recommended)",
          "description": "Auto-approves tool use for autonomous worktree agents"
        },
        {
          "label": "cc",
          "description": "Common alias for Claude Code"
        },
        {
          "label": "claude",
          "description": "Standard command - will prompt for tool approvals"
        }
      ]
    },
    {
      "header": "Location",
      "question": "Where should worktrees be created?",
      "multiSelect": false,
      "options": [
        {
          "label": "~/Projects/worktrees (Recommended)",
          "description": "Keeps worktrees organized and separate from source repos"
        },
        {
          "label": "~/worktrees",
          "description": "Shorter path directly in home directory"
        }
      ]
    }
  ]
}
```

### Step 4: Map Answers to Config Values

| Question | User Selection | Config Value |
|----------|---------------|--------------|
| Terminal | iTerm2 (Recommended) | `iterm2-tab` |
| Terminal | Ghostty | `ghostty` |
| Terminal | tmux | `tmux` |
| Terminal | Other (specify wezterm) | `wezterm` |
| Terminal | Other (specify kitty) | `kitty` |
| Terminal | Other (specify alacritty) | `alacritty` |
| Shell | zsh (Recommended) | `zsh` |
| Shell | bash | `bash` |
| Shell | fish | `fish` |
| Claude | claude --dangerously-skip-permissions | `claude --dangerously-skip-permissions` |
| Claude | cc | `cc` |
| Claude | claude | `claude` |
| Location | ~/Projects/worktrees | `~/Projects/worktrees` |
| Location | ~/worktrees | `~/worktrees` |

### Step 5: Write Config File

After mapping answers, write the configuration using jq for proper JSON escaping:

```bash
mkdir -p ~/.claude

jq -n \
  --arg terminal "${TERMINAL_VALUE}" \
  --arg shell "${SHELL_VALUE}" \
  --arg claudeCommand "${CLAUDE_CMD_VALUE}" \
  --arg worktreeBase "${WORKTREE_BASE_VALUE}" \
  '{
    terminal: $terminal,
    shell: $shell,
    claudeCommand: $claudeCommand,
    worktreeBase: $worktreeBase,
    portPool: { start: 8100, end: 8199 },
    portsPerWorktree: 2,
    registryPath: "~/.claude/worktree-registry.json",
    defaultCopyDirs: [".agents", ".env.example", ".env"],
    healthCheckTimeout: 30,
    healthCheckRetries: 6
  }' > ~/.claude/worktree-manager.config.json
```

### Step 6: Confirm Success

```bash
echo ""
echo "Configuration saved!"
echo "===================="
echo "Location: ~/.claude/worktree-manager.config.json"
echo ""
echo "Settings:"
echo "  Terminal:      ${TERMINAL_VALUE}"
echo "  Shell:         ${SHELL_VALUE}"
echo "  Claude cmd:    ${CLAUDE_CMD_VALUE}"
echo "  Worktree base: ${WORKTREE_BASE_VALUE}"
echo ""
echo "These settings will be used for all future worktree operations."
```

## Notes

- Port pool defaults to 8100-8199 (allows ~50 concurrent worktrees)
- Registry location is fixed at `~/.claude/worktree-registry.json`
- Default directories copied to worktrees: `.agents`, `.env.example`, `.env`
- Run this command again anytime to change your settings
