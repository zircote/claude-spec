---
document_type: research
project_id: SPEC-2025-12-13-001
last_updated: 2025-12-13T14:30:00Z
---

# Worktree Manager Configuration Installation - Research Notes

## Research Summary

Analyzed the existing worktree-manager skill structure, identified all config consumers, and mapped out the prompt log timing bug.

## Codebase Analysis

### Relevant Files Examined

| File | Purpose | Relevance |
|------|---------|-----------|
| `plugins/cs/skills/worktree-manager/config.json` | Current config location | Will be renamed to template |
| `plugins/cs/skills/worktree-manager/SKILL.md` | Skill documentation | Needs setup flow addition |
| `plugins/cs/skills/worktree-manager/scripts/launch-agent.sh` | Agent launcher | Uses terminal, shell, claudeCommand |
| `plugins/cs/skills/worktree-manager/scripts/allocate-ports.sh` | Port allocation | Uses portPool.start/end |
| `plugins/cs/skills/worktree-manager/scripts/cleanup.sh` | Worktree cleanup | Only uses registry, not config |
| `plugins/cs/skills/worktree-manager/scripts/register.sh` | Worktree registration | Only uses registry, not config |
| `plugins/cs/skills/worktree-manager/scripts/status.sh` | Status display | Only uses registry, not config |
| `plugins/cs/skills/worktree-manager/scripts/release-ports.sh` | Port release | Only uses registry, not config |
| `plugins/cs/commands/p.md` | /cs:p command | Needs prompt log timing fix |
| `plugins/cs/hooks/prompt_capture.py` | Prompt capture hook | Checks for .prompt-log-enabled |

### Config Usage Patterns

**Scripts that use config.json:**

1. **launch-agent.sh** (lines 64-72):
```bash
if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    TERMINAL=$(jq -r '.terminal // "ghostty"' "$CONFIG_FILE")
    SHELL_CMD=$(jq -r '.shell // "bash"' "$CONFIG_FILE")
    CLAUDE_CMD=$(jq -r '.claudeCommand // "claude --dangerously-skip-permissions"' "$CONFIG_FILE")
```

2. **allocate-ports.sh** (lines 27-33):
```bash
if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    PORT_START=$(jq -r '.portPool.start // 8100' "$CONFIG_FILE")
    PORT_END=$(jq -r '.portPool.end // 8199' "$CONFIG_FILE")
```

**Scripts that DON'T use config.json:**
- `cleanup.sh` - Uses registry at `~/.claude/worktree-registry.json`
- `register.sh` - Uses registry
- `status.sh` - Uses registry
- `release-ports.sh` - Uses registry

### Current Config Schema

```json
{
  "terminal": "iterm2-tab",           // Used by launch-agent.sh
  "shell": "bash",                     // Used by launch-agent.sh
  "claudeCommand": "cc",               // Used by launch-agent.sh
  "portPool": {
    "start": 8100,                     // Used by allocate-ports.sh
    "end": 8199                        // Used by allocate-ports.sh
  },
  "portsPerWorktree": 2,               // Not currently used by scripts
  "worktreeBase": "~/Projects/worktrees",  // Not currently used by scripts
  "registryPath": "~/.claude/worktree-registry.json",  // Hardcoded in scripts
  "defaultCopyDirs": [".agents", ".env.example", ".env"],  // Referenced in SKILL.md
  "healthCheckTimeout": 30,            // Not currently used
  "healthCheckRetries": 6              // Not currently used
}
```

### Existing User Files in ~/.claude/

```
~/.claude/
├── settings.json
├── settings.local.json
├── stats-cache.json
├── worktree-registry.json    # Already uses this location
└── security_warnings_state_*.json
```

Note: `worktree-registry.json` already lives at `~/.claude/`, so `worktree-manager.config.json` fits the pattern.

## Prompt Log Timing Analysis

### Hook Detection Logic

From `plugins/cs/hooks/prompt_capture.py`:
```python
def find_active_project(cwd: str) -> Optional[str]:
    """Find active project directory with logging enabled."""
    spec_paths = [
        os.path.join(cwd, "docs", "spec", "active"),
        os.path.join(cwd, "docs", "architecture", "active"),
    ]

    for spec_dir in spec_paths:
        if os.path.isdir(spec_dir):
            for project in os.listdir(spec_dir):
                project_path = os.path.join(spec_dir, project)
                if os.path.isdir(project_path):
                    marker_path = os.path.join(project_path, ".prompt-log-enabled")
                    if os.path.exists(marker_path):
                        return project_path
    return None
```

The hook looks for `.prompt-log-enabled` marker in `docs/spec/active/*/` or `docs/architecture/active/*/`.

### Current p.md Flow (Buggy)

```
mandatory_first_actions:
1. Check branch
2. If protected branch:
   a. Create worktree
   b. Launch agent with --prompt "/cs:p ..."
   c. STOP

--- NEW SESSION ---

Step 1: Initialize Project (runs in new session)
   - mkdir -p docs/spec/active/${DATE}-${SLUG}
   - touch .prompt-log-enabled           <- TOO LATE!
```

### Fixed Flow

```
mandatory_first_actions:
1. Check branch
2. If protected branch:
   a. Create worktree
   b. Compute slug from project seed
   c. mkdir -p ${WORKTREE_PATH}/docs/spec/active/${DATE}-${SLUG}
   d. touch ${WORKTREE_PATH}/docs/spec/active/${DATE}-${SLUG}/.prompt-log-enabled
   e. Launch agent with --prompt "/cs:p ..."
   f. STOP

--- NEW SESSION ---

Hook can now find .prompt-log-enabled -> first prompt captured!
```

## Terminal Support

From `launch-agent.sh`:
```bash
case "$TERMINAL" in
    ghostty)           # Uses open -na "Ghostty.app"
    iterm2|iterm)      # Uses osascript to create tab
    iterm2-tab|iterm-tab)  # Same as above
    tmux)              # Uses tmux new-session
    wezterm)           # Uses wezterm start
    kitty)             # Uses kitty --detach
    alacritty)         # Uses alacritty &
esac
```

## Open Questions from Research

- [x] Which config fields are actively used? → terminal, shell, claudeCommand, portPool.start/end
- [x] Where should user config live? → ~/.claude/worktree-manager.config.json
- [x] How to detect shell? → Parse $SHELL environment variable

## Sources

- `plugins/cs/skills/worktree-manager/` - All scripts analyzed
- `plugins/cs/commands/p.md` - Prompt flow analyzed
- `plugins/cs/hooks/prompt_capture.py` - Marker detection logic
