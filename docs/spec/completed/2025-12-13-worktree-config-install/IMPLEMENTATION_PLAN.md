---
document_type: implementation_plan
project_id: SPEC-2025-12-13-001
version: 1.0.0
last_updated: 2025-12-13T14:30:00Z
status: draft
---

# Worktree Manager Configuration Installation - Implementation Plan

## Overview

This plan implements user-level configuration persistence with interactive setup for the worktree-manager skill, plus fixes prompt log timing for worktree sessions.

## Phase Summary

| Phase | Key Deliverables |
|-------|------------------|
| Phase 1: Config Foundation | Template file, config loader library |
| Phase 2: Script Migration | Update launch-agent.sh, allocate-ports.sh |
| Phase 3: Interactive Setup | SKILL.md setup flow, /cs:wt:setup command |
| Phase 4: Prompt Log Fix | Update p.md for early marker creation |
| Phase 5: Testing & Polish | Manual testing, documentation updates |

---

## Phase 1: Config Foundation

**Goal**: Establish the new configuration file structure and loader library

### Tasks

#### Task 1.1: Create config.template.json

- **Description**: Rename existing `config.json` to `config.template.json` with updated defaults
- **Files**:
  - `plugins/cs/skills/worktree-manager/config.json` → `config.template.json`
- **Acceptance Criteria**:
  - [x] `config.template.json` exists with all fields
  - [x] Default values are sensible for first-time users
  - [x] `config.json` removed (to prevent confusion)

#### Task 1.2: Create config loader library

- **Description**: Create `lib/config.sh` with functions for loading config with fallback
- **Files**:
  - Create `plugins/cs/skills/worktree-manager/scripts/lib/config.sh`
- **Acceptance Criteria**:
  - [x] `get_config()` function returns user config value or template default
  - [x] `load_config()` function sets up config context
  - [x] `ensure_config()` function checks if user config exists
  - [x] Handles missing user config gracefully
  - [x] Handles missing jq gracefully

**Implementation Notes**:
```bash
#!/bin/bash
# lib/config.sh - Configuration loader with user config + template fallback

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USER_CONFIG="${HOME}/.claude/worktree-manager.config.json"
TEMPLATE_CONFIG="${SCRIPT_DIR}/../../config.template.json"

# Check if user config exists
has_user_config() {
    [ -f "$USER_CONFIG" ]
}

# Get config value with fallback chain: user config → template → default
get_config() {
    local key="$1"
    local default="$2"

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

# Get nested config value (e.g., portPool.start)
get_config_nested() {
    local key="$1"
    local default="$2"

    if ! command -v jq &> /dev/null; then
        echo "$default"
        return
    fi

    local value=""

    if [ -f "$USER_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$USER_CONFIG" 2>/dev/null)
    fi

    if [ -z "$value" ] && [ -f "$TEMPLATE_CONFIG" ]; then
        value=$(jq -r ".$key // empty" "$TEMPLATE_CONFIG" 2>/dev/null)
    fi

    if [ -z "$value" ]; then
        echo "$default"
    else
        echo "$value"
    fi
}
```

### Phase 1 Deliverables

- [x] `config.template.json` with sensible defaults
- [x] `lib/config.sh` with loader functions
- [x] Old `config.json` removed

---

## Phase 2: Script Migration

**Goal**: Update consumer scripts to use the new config loader

### Tasks

#### Task 2.1: Update launch-agent.sh

- **Description**: Replace inline config loading with lib/config.sh
- **Files**:
  - `plugins/cs/skills/worktree-manager/scripts/launch-agent.sh`
- **Acceptance Criteria**:
  - [x] Sources `lib/config.sh`
  - [x] Uses `get_config()` for terminal, shell, claudeCommand
  - [x] Works with user config, template fallback, or no config
  - [x] Existing functionality preserved

**Implementation Notes**:
```bash
# Replace this:
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/../config.json"
if [ -f "$CONFIG_FILE" ] && command -v jq &> /dev/null; then
    TERMINAL=$(jq -r '.terminal // "ghostty"' "$CONFIG_FILE")
    ...
fi

# With this:
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/config.sh"
TERMINAL=$(get_config "terminal" "ghostty")
SHELL_CMD=$(get_config "shell" "bash")
CLAUDE_CMD=$(get_config "claudeCommand" "claude --dangerously-skip-permissions")
```

#### Task 2.2: Update allocate-ports.sh

- **Description**: Replace inline config loading with lib/config.sh
- **Files**:
  - `plugins/cs/skills/worktree-manager/scripts/allocate-ports.sh`
- **Acceptance Criteria**:
  - [x] Sources `lib/config.sh`
  - [x] Uses `get_config_nested()` for portPool.start/end
  - [x] Works with user config, template fallback, or no config
  - [x] Existing functionality preserved

### Phase 2 Deliverables

- [x] `launch-agent.sh` using config loader
- [x] `allocate-ports.sh` using config loader
- [x] Both scripts work with user config OR template fallback

---

## Phase 3: Interactive Setup

**Goal**: Implement user-friendly first-time configuration

### Tasks

#### Task 3.1: Update SKILL.md with setup instructions

- **Description**: Add setup flow to SKILL.md that triggers on missing config
- **Files**:
  - `plugins/cs/skills/worktree-manager/SKILL.md`
- **Acceptance Criteria**:
  - [x] SKILL.md includes "## First-Time Setup" section
  - [x] Instructions to detect missing user config
  - [x] AskUserQuestion flow for terminal, shell, claudeCommand, worktreeBase
  - [x] Instructions to write config file after answers

**Implementation Notes** (SKILL.md addition):
```markdown
## First-Time Setup

When this skill is first used, check if `~/.claude/worktree-manager.config.json` exists.

If NOT exists, run interactive setup:

1. **Detect shell**: Run `echo $SHELL` and extract shell name
2. **Ask questions** using AskUserQuestion tool:

\`\`\`
Question 1 - Terminal:
  header: "Terminal"
  question: "Which terminal do you use for development?"
  options:
    - label: "iTerm2 (Recommended)"
      description: "macOS terminal with tab support"
    - label: "Ghostty"
      description: "Fast, GPU-accelerated terminal"
    - label: "tmux"
      description: "Terminal multiplexer (creates sessions)"
    - label: "Other"
      description: "WezTerm, Kitty, or Alacritty"

Question 2 - Shell:
  header: "Shell"
  question: "What shell do you use? (detected: [DETECTED_SHELL])"
  options:
    - label: "[DETECTED_SHELL] (Recommended)"
      description: "Your current shell"
    - label: "bash"
      description: "Bourne Again Shell"
    - label: "zsh"
      description: "Z Shell"
    - label: "fish"
      description: "Friendly Interactive Shell"

Question 3 - Claude Command:
  header: "Claude"
  question: "How do you launch Claude Code?"
  options:
    - label: "claude --dangerously-skip-permissions (Recommended)"
      description: "Default with auto-approve for worktrees"
    - label: "cc"
      description: "Common alias"
    - label: "claude"
      description: "Default without auto-approve"

Question 4 - Worktree Base:
  header: "Location"
  question: "Where should worktrees be created?"
  options:
    - label: "~/Projects/worktrees (Recommended)"
      description: "Separate from source repos"
    - label: "~/worktrees"
      description: "Home directory"
\`\`\`

3. **Write config file**:
\`\`\`bash
mkdir -p ~/.claude
cat > ~/.claude/worktree-manager.config.json << EOF
{
  "terminal": "[ANSWER_1]",
  "shell": "[ANSWER_2]",
  "claudeCommand": "[ANSWER_3]",
  "worktreeBase": "[ANSWER_4]",
  "portPool": { "start": 8100, "end": 8199 },
  "portsPerWorktree": 2,
  "registryPath": "~/.claude/worktree-registry.json",
  "defaultCopyDirs": [".agents", ".env.example", ".env"],
  "healthCheckTimeout": 30,
  "healthCheckRetries": 6
}
EOF
\`\`\`
```

#### Task 3.2: Create /cs:wt:setup command

- **Description**: Add explicit setup command for reconfiguration
- **Files**:
  - Create `plugins/cs/commands/wt/setup.md`
- **Acceptance Criteria**:
  - [x] Command triggers interactive setup flow
  - [x] Shows current config values (if exists) before asking
  - [x] Overwrites existing config with new values
  - [x] Confirms successful write

**Implementation Notes**:
```markdown
# /cs:wt:setup - Configure Worktree Manager

Run the interactive setup flow to configure worktree-manager preferences.

## Steps

1. Check if config exists at `~/.claude/worktree-manager.config.json`
2. If exists, display current values
3. Run AskUserQuestion flow (same as SKILL.md first-time setup)
4. Write new config file
5. Confirm: "Configuration saved to ~/.claude/worktree-manager.config.json"
```

### Phase 3 Deliverables

- [x] SKILL.md with first-time setup instructions
- [x] `/cs:wt:setup` command file
- [x] Interactive setup flow works end-to-end

---

## Phase 4: Prompt Log Fix

**Goal**: Ensure first prompt is captured in worktree sessions

### Tasks

#### Task 4.1: Update p.md mandatory_first_actions

- **Description**: Create spec directory and prompt log marker in worktree BEFORE launching agent
- **Files**:
  - `plugins/cs/commands/p.md`
- **Acceptance Criteria**:
  - [x] After worktree creation, compute slug and date
  - [x] Create prompt log marker at worktree root (updated: project root, not spec dir)
  - [x] Agent launch comes AFTER marker creation
  - [x] First prompt in new session is captured

**Implementation Notes**:

In the `mandatory_first_actions` section of p.md, after Step 3b (worktree creation) and before Step 4 (launch agent):

```bash
### Step 3c: Enable prompt logging in worktree (NEW)

# Compute project identifiers
DATE=$(date +%Y-%m-%d)
SLUG=$(echo "${PROJECT_SEED}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | cut -c1-30)

# Create spec directory and prompt log marker IN THE WORKTREE
SPEC_DIR="${WORKTREE_PATH}/docs/spec/active/${DATE}-${SLUG}"
mkdir -p "${SPEC_DIR}"
touch "${SPEC_DIR}/.prompt-log-enabled"

echo "Prompt logging enabled at: ${SPEC_DIR}/.prompt-log-enabled"
```

The `PROJECT_SEED` should be extracted from the original arguments passed to `/cs:p`.

### Phase 4 Deliverables

- [x] p.md creates prompt log marker before agent launch (at worktree root)
- [x] First prompt in worktree session is captured

---

## Phase 5: Testing & Polish

**Goal**: Ensure everything works correctly and documentation is updated

### Tasks

#### Task 5.1: Manual testing - fresh install

- **Description**: Test first-time setup flow from scratch
- **Acceptance Criteria**:
  - [x] Remove `~/.claude/worktree-manager.config.json`
  - [x] Run a worktree command
  - [x] Setup questions appear
  - [x] Config file created with answers
  - [x] Subsequent commands use new config

#### Task 5.2: Manual testing - plugin update simulation

- **Description**: Verify user config persists across simulated update
- **Acceptance Criteria**:
  - [x] User config exists
  - [x] "Update" plugin (reinstall or modify template)
  - [x] User config unchanged
  - [x] Commands still use user config values

#### Task 5.3: Manual testing - prompt log timing

- **Description**: Verify first prompt is captured in worktree session
- **Acceptance Criteria**:
  - [x] Run `/cs:p` on main branch (triggers worktree creation)
  - [x] Switch to new terminal
  - [x] Execute the pre-filled `/cs:p` command
  - [x] Check `.prompt-log.json` - first prompt should be captured

#### Task 5.4: Update documentation

- **Description**: Update SKILL.md, README.md with new config location
- **Files**:
  - `plugins/cs/skills/worktree-manager/SKILL.md`
  - `plugins/cs/README.md` (if references config)
- **Acceptance Criteria**:
  - [x] Config location documented as `~/.claude/worktree-manager.config.json`
  - [x] Setup process documented
  - [x] `/cs:wt:setup` command documented

### Phase 5 Deliverables

- [x] All manual tests pass
- [x] Documentation updated
- [x] CHANGELOG.md updated

---

## Dependency Graph

```
Phase 1: Foundation
  Task 1.1 (template) ──────┐
                            ├──► Phase 2: Script Migration
  Task 1.2 (lib/config.sh) ─┘
                                    │
                                    ▼
                            Phase 3: Interactive Setup
                            Task 3.1 (SKILL.md) ────┐
                            Task 3.2 (/cs:wt:setup)─┤
                                                    │
                                                    ▼
                            Phase 4: Prompt Log Fix
                            Task 4.1 (p.md) ────────┤
                                                    │
                                                    ▼
                            Phase 5: Testing & Polish
                            Tasks 5.1-5.4 ──────────┘
```

## Risk Mitigation Tasks

| Risk | Mitigation Task | Phase |
|------|-----------------|-------|
| Script changes break workflows | Preserve fallback to template defaults | Phase 2 |
| Config file corruption | Atomic writes in setup flow | Phase 3 |
| First prompt still missed | Verify marker creation timing | Phase 4 |

## Testing Checklist

- [x] Config loader works with: user config only, template only, both, neither
- [x] launch-agent.sh respects user config terminal preference
- [x] allocate-ports.sh respects user config port range
- [x] First-time setup creates valid config file
- [x] /cs:wt:setup allows reconfiguration
- [x] Prompt log captures first prompt in worktree session

## Documentation Tasks

- [x] Update SKILL.md with config location and setup flow
- [x] Update README.md if it references config
- [x] Add /cs:wt:setup to command documentation

## Launch Checklist

- [x] All manual tests passing
- [x] Documentation updated
- [x] CHANGELOG.md updated
- [ ] PR created and reviewed

## Post-Launch

- [ ] Monitor for user issues with setup flow
- [ ] Gather feedback on question clarity
- [ ] Consider adding config migration for future updates
