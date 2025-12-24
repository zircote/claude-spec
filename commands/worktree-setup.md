---
argument-hint: (none)
description: Interactive configuration wizard for worktree-manager. Creates ~/.claude/claude-spec.config.json with terminal, shell, and path settings.
model: claude-sonnet-4-5-20250929
allowed-tools: Read, Write, Bash, AskUserQuestion
---

<help_check>
## Help Check

If `$ARGUMENTS` contains `--help` or `-h`:

**Output this help and HALT (do not proceed further):**

<help_output>
```
WORKTREE_SETUP(1)                                    User Commands                                    WORKTREE_SETUP(1)

NAME
    worktree-setup - Interactive configuration wizard for worktree-manager. ...

SYNOPSIS
    /claude-spec:worktree-setup (none)

DESCRIPTION
    Interactive configuration wizard for worktree-manager. Creates ~/.claude/claude-spec.config.json with terminal, shell, and path settings.

OPTIONS
    --help, -h                Show this help message

EXAMPLES
    /claude-spec:worktree-setup             
    /claude-spec:worktree-setup --help      

SEE ALSO
    /claude-spec:* for related commands

                                                                      WORKTREE_SETUP(1)
```
</help_output>

**After outputting help, HALT immediately. Do not proceed with command execution.**
</help_check>

---

# /claude-spec:worktree-setup - Configure Worktree Manager

Run the interactive setup flow to configure your worktree-manager preferences.

This command creates or updates `~/.claude/claude-spec.config.json` with your personal settings.

## When to Use

- **First time**: When you haven't configured worktree-manager yet
- **Reconfigure**: When you want to change your terminal, shell, or other settings
- **After switching terminals**: If you started using a different terminal app

## Execution Steps

### Step 1: Check Current Config and Detect Shell

Run these two commands in parallel:

**Check existing config:**
```bash
test -f ~/.claude/claude-spec.config.json && echo "Current configuration:" && jq '.' ~/.claude/claude-spec.config.json && echo "This setup will overwrite the above." || echo "No existing configuration found."
```

**Detect shell:**
```bash
echo "Detected shell: $(basename $SHELL)"
```

### Step 2: Ask Configuration Questions

Use the `AskUserQuestion` tool with these 4 questions in a single call.

**IMPORTANT**: Labels are the EXACT config values. Use the selected label directly in the config file without any transformation.

```json
{
  "questions": [
    {
      "header": "Terminal",
      "question": "Which terminal do you use for development?",
      "multiSelect": false,
      "options": [
        {
          "label": "iterm2-tab",
          "description": "(Recommended) macOS terminal with excellent tab support"
        },
        {
          "label": "ghostty",
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
          "label": "zsh",
          "description": "(Recommended) Z Shell - macOS default since Catalina"
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
          "label": "claude --dangerously-skip-permissions",
          "description": "(Recommended) Auto-approves tool use for autonomous worktree agents"
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
          "label": "~/Projects/worktrees",
          "description": "(Recommended) Keeps worktrees organized and separate from source repos"
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

### Step 3: Use Answers Directly

**No mapping required.** The selected labels ARE the config values. Use them directly:

- Terminal answer → `terminal` field
- Shell answer → `shell` field
- Claude answer → `claudeCommand` field
- Location answer → `worktreeBase` field

For "Other" responses, use the user's custom input as the config value.

### Step 4: Write Config File

Write the configuration using the selected labels directly. Run as a single chained command:

```bash
mkdir -p ~/.claude && jq -n --arg terminal "TERMINAL_ANSWER" --arg shell "SHELL_ANSWER" --arg claudeCommand "CLAUDE_ANSWER" --arg worktreeBase "LOCATION_ANSWER" '{terminal: $terminal, shell: $shell, claudeCommand: $claudeCommand, worktreeBase: $worktreeBase, portPool: {start: 8100, end: 8199}, portsPerWorktree: 2, registryPath: "~/.claude/worktree-registry.json", defaultCopyDirs: [".agents", ".env.example", ".env"], healthCheckTimeout: 30, healthCheckRetries: 6}' > ~/.claude/claude-spec.config.json
```

Replace the `*_ANSWER` placeholders with the actual user selections before running.

### Step 5: Confirm Success

Display the saved config:

```bash
cat ~/.claude/claude-spec.config.json
```

## Notes

- Port pool defaults to 8100-8199 (allows ~50 concurrent worktrees)
- Registry location is fixed at `~/.claude/worktree-registry.json`
- Default directories copied to worktrees: `.agents`, `.env.example`, `.env`
- Run this command again anytime to change your settings
