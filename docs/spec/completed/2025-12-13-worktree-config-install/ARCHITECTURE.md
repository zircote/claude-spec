---
document_type: architecture
project_id: SPEC-2025-12-13-001
version: 1.0.0
last_updated: 2025-12-13T14:30:00Z
status: draft
---

# Worktree Manager Configuration Installation - Technical Architecture

## System Overview

This project refactors the worktree-manager configuration system to separate plugin-bundled defaults from user preferences, introducing an interactive setup flow and fixing prompt log timing.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CONFIGURATION SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────┐     ┌──────────────────────────────────────┐  │
│  │ Plugin Directory        │     │ User Directory (~/.claude/)          │  │
│  │                         │     │                                      │  │
│  │  config.template.json   │────▶│  worktree-manager.config.json       │  │
│  │  (defaults, read-only)  │     │  (user preferences, persists)       │  │
│  │                         │ copy │                                      │  │
│  └─────────────────────────┘     └──────────────────────────────────────┘  │
│            ▲                                    │                           │
│            │ fallback                           │ primary                   │
│            │                                    ▼                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      CONFIG LOADER (in scripts)                      │   │
│  │                                                                      │   │
│  │  1. Check ~/.claude/worktree-manager.config.json                    │   │
│  │  2. If missing → trigger interactive setup OR use template          │   │
│  │  3. Load and merge with template defaults for missing fields        │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         CONSUMER SCRIPTS                             │   │
│  │                                                                      │   │
│  │  launch-agent.sh    │  allocate-ports.sh    │  SKILL.md (guidance)  │   │
│  │  - terminal         │  - portPool.start     │                        │   │
│  │  - shell            │  - portPool.end       │                        │   │
│  │  - claudeCommand    │                       │                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **User config at `~/.claude/worktree-manager.config.json`**: Follows Claude's config pattern, survives plugin updates
2. **Template fallback**: Scripts always work even without user config
3. **Interactive setup via AskUserQuestion**: Leverages Claude's native UI for clean UX
4. **Bash config loader function**: Reusable across all scripts

## Component Design

### Component 1: Config Template File

- **Purpose**: Provide sensible defaults for all config fields
- **Location**: `plugins/cs/skills/worktree-manager/config.template.json`
- **Responsibilities**:
  - Source of truth for default values
  - Reference for config schema
  - Fallback when user config missing or incomplete
- **Technology**: JSON file

```json
{
  "terminal": "ghostty",
  "shell": "bash",
  "claudeCommand": "claude --dangerously-skip-permissions",
  "portPool": {
    "start": 8100,
    "end": 8199
  },
  "portsPerWorktree": 2,
  "worktreeBase": "~/Projects/worktrees",
  "registryPath": "~/.claude/worktree-registry.json",
  "defaultCopyDirs": [".agents", ".env.example", ".env"],
  "healthCheckTimeout": 30,
  "healthCheckRetries": 6
}
```

### Component 2: Config Loader Function

- **Purpose**: Unified config loading with fallback logic
- **Location**: New file `plugins/cs/skills/worktree-manager/scripts/lib/config.sh`
- **Responsibilities**:
  - Check for user config at `~/.claude/worktree-manager.config.json`
  - Fall back to template if user config missing
  - Provide individual field getters with defaults
- **Interfaces**: Sourced by other scripts

```bash
# Usage in scripts:
source "$SCRIPT_DIR/lib/config.sh"

TERMINAL=$(get_config "terminal" "ghostty")
CLAUDE_CMD=$(get_config "claudeCommand" "claude --dangerously-skip-permissions")
```

### Component 3: Interactive Setup Flow

- **Purpose**: Guide users through first-time configuration
- **Location**: `plugins/cs/skills/worktree-manager/SKILL.md` (instructions)
- **Responsibilities**:
  - Detect missing user config
  - Use `AskUserQuestion` tool for interactive questions
  - Write user config file with answers
- **Technology**: Claude's AskUserQuestion tool + bash file write
- **Dependencies**: Called by Claude when SKILL.md triggers

### Component 4: Setup Command

- **Purpose**: Allow explicit reconfiguration
- **Location**: `plugins/cs/commands/wt/setup.md`
- **Responsibilities**:
  - Run interactive setup regardless of existing config
  - Optionally show current values before asking
- **Interfaces**: Slash command `/cs:wt:setup`

### Component 5: Prompt Log Timing Fix

- **Purpose**: Ensure first prompt is captured in worktree sessions
- **Location**: `plugins/cs/commands/p.md` (modification)
- **Responsibilities**:
  - Create spec directory in worktree BEFORE launching agent
  - Create `.prompt-log-enabled` marker BEFORE launching agent
- **Dependencies**: Coordinates with `launch-agent.sh`

## Data Design

### Config File Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "terminal": {
      "type": "string",
      "enum": ["ghostty", "iterm2", "iterm2-tab", "iterm-tab", "tmux", "wezterm", "kitty", "alacritty"],
      "default": "ghostty"
    },
    "shell": {
      "type": "string",
      "enum": ["bash", "zsh", "fish"],
      "default": "bash"
    },
    "claudeCommand": {
      "type": "string",
      "default": "claude --dangerously-skip-permissions"
    },
    "portPool": {
      "type": "object",
      "properties": {
        "start": { "type": "integer", "default": 8100 },
        "end": { "type": "integer", "default": 8199 }
      }
    },
    "portsPerWorktree": { "type": "integer", "default": 2 },
    "worktreeBase": { "type": "string", "default": "~/Projects/worktrees" },
    "registryPath": { "type": "string", "default": "~/.claude/worktree-registry.json" },
    "defaultCopyDirs": {
      "type": "array",
      "items": { "type": "string" },
      "default": [".agents", ".env.example", ".env"]
    },
    "healthCheckTimeout": { "type": "integer", "default": 30 },
    "healthCheckRetries": { "type": "integer", "default": 6 }
  }
}
```

### Data Flow

```
┌─────────────────┐
│ User runs       │
│ worktree cmd    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Script sources lib/config.sh       │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Check: ~/.claude/worktree-manager   │
│        .config.json exists?         │
└────────┬───────────────┬────────────┘
         │ yes           │ no
         ▼               ▼
┌─────────────┐   ┌──────────────────┐
│ Load user   │   │ If interactive:  │
│ config      │   │ Run setup flow   │
└─────────────┘   │ Else: use        │
         │        │ template         │
         │        └────────┬─────────┘
         │                 │
         ▼                 ▼
┌─────────────────────────────────────┐
│ Merge with template defaults        │
│ (fill missing fields)              │
└────────┬────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Return config values to script      │
└─────────────────────────────────────┘
```

### Storage Strategy

- **User Config**: `~/.claude/worktree-manager.config.json`
- **Template**: `plugins/cs/skills/worktree-manager/config.template.json`
- **Atomic Writes**: Write to temp file, then `mv` to target

## Interactive Setup Design

### AskUserQuestion Flow

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  WORKTREE MANAGER SETUP                                                   ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║  Question 1: Terminal                                                     ║
║  "Which terminal do you use for development?"                             ║
║  Options:                                                                 ║
║    - iTerm2 (Recommended for macOS)                                       ║
║    - Ghostty                                                              ║
║    - tmux                                                                 ║
║    - Other (WezTerm, Kitty, Alacritty)                                    ║
║                                                                           ║
║  Question 2: Shell                                                        ║
║  "What shell do you use?" [Pre-filled from $SHELL detection]              ║
║  Options:                                                                 ║
║    - bash                                                                 ║
║    - zsh                                                                  ║
║    - fish                                                                 ║
║                                                                           ║
║  Question 3: Claude Command                                               ║
║  "What command/alias launches Claude Code?"                               ║
║  Options:                                                                 ║
║    - claude --dangerously-skip-permissions (Recommended)                  ║
║    - cc (common alias)                                                    ║
║    - Other (specify)                                                      ║
║                                                                           ║
║  Question 4: Worktree Base                                                ║
║  "Where should worktrees be created?"                                     ║
║  Options:                                                                 ║
║    - ~/Projects/worktrees (Recommended)                                   ║
║    - ~/worktrees                                                          ║
║    - Other (specify)                                                      ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

### Shell Detection

```bash
# Detect shell from environment
detect_shell() {
    case "$SHELL" in
        */bash) echo "bash" ;;
        */zsh)  echo "zsh" ;;
        */fish) echo "fish" ;;
        *)      echo "bash" ;;  # default
    esac
}
```

## Prompt Log Timing Fix

### Current Flow (Buggy)

```
/cs:p on main branch
    │
    ▼
Create worktree at ${WORKTREE_PATH}
    │
    ▼
Launch agent: launch-agent.sh ${WORKTREE_PATH} --prompt "/cs:p <args>"
    │
    ▼
═══════════════════ NEW SESSION ═══════════════════
    │
    ▼
Claude receives prompt "/cs:p <args>"  ← FIRST PROMPT
    │
    ▼
Hook checks for .prompt-log-enabled → NOT FOUND
    │
    ▼
Prompt NOT captured ← BUG
    │
    ▼
Step 1 runs: creates .prompt-log-enabled
    │
    ▼
Subsequent prompts captured
```

### Fixed Flow

```
/cs:p on main branch
    │
    ▼
Create worktree at ${WORKTREE_PATH}
    │
    ▼
Create spec directory: mkdir -p ${WORKTREE_PATH}/docs/spec/active/${DATE}-${SLUG}
    │
    ▼
Create marker: touch ${WORKTREE_PATH}/docs/spec/active/${DATE}-${SLUG}/.prompt-log-enabled
    │
    ▼
Launch agent: launch-agent.sh ${WORKTREE_PATH} --prompt "/cs:p <args>"
    │
    ▼
═══════════════════ NEW SESSION ═══════════════════
    │
    ▼
Claude receives prompt "/cs:p <args>"  ← FIRST PROMPT
    │
    ▼
Hook checks for .prompt-log-enabled → FOUND ✓
    │
    ▼
Prompt CAPTURED ✓
```

### Implementation in p.md

```bash
# In mandatory_first_actions section, after worktree creation:

# Compute project slug and date
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "${PROJECT_SEED}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-30)

# Create spec directory and prompt log marker IN THE WORKTREE
SPEC_DIR="${WORKTREE_PATH}/docs/spec/active/${DATE}-${SLUG}"
mkdir -p "${SPEC_DIR}"
touch "${SPEC_DIR}/.prompt-log-enabled"

# Then launch agent
launch-agent.sh "${WORKTREE_PATH}" "" --prompt "/cs:p ${ORIGINAL_ARGS}"
```

## Testing Strategy

### Unit Testing

- Config loader function: test default fallback, user override, missing file handling
- Shell detection: test various `$SHELL` values

### Integration Testing

- End-to-end setup flow with mock AskUserQuestion responses
- Worktree creation with prompt log verification

### Manual Testing

- Fresh install: verify setup triggers
- Plugin update: verify user config persists
- Prompt log: verify first prompt captured in new worktree session

## Deployment Considerations

### Migration Path

1. Rename `config.json` → `config.template.json`
2. Update scripts to use new config loader
3. Update SKILL.md with setup instructions
4. Existing users: config stays in old location (scripts fall back to template)
5. Users run `/cs:wt:setup` to create user config

### Rollback Plan

1. Rename `config.template.json` back to `config.json`
2. Revert script changes
3. User configs at `~/.claude/` remain (harmless)

## Future Considerations

- Multi-OS templates (detect OS and suggest appropriate terminal)
- Config migration tool for existing users
- GUI config editor (if Claude Code adds UI capabilities)
