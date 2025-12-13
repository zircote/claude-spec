---
document_type: architecture
project_id: SPEC-2025-12-13-001
version: 1.0.0
last_updated: 2025-12-13T00:00:00Z
status: draft
---

# Pre and Post Steps for cs:* Commands - Technical Architecture

## System Overview

This architecture extends the claude-spec plugin with a hook-based pre/post step system that leverages Claude Code's native hook events (SessionStart, Stop, UserPromptSubmit) to automate context loading, security review, and cleanup tasks.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Claude Code Session                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │ SessionStart │───▶│ User Prompt  │───▶│    Stop      │               │
│  │    Hook      │    │  Processing  │    │    Hook      │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│         ▼                   ▼                   ▼                        │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │  Pre-Steps   │    │UserPromptSub │    │  Post-Steps  │               │
│  │  Executor    │    │    Hook      │    │  Executor    │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
└─────────┼───────────────────┼───────────────────┼────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         cs Plugin Components                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  hooks/                      filters/              config/                │
│  ├── session_start.py        ├── pipeline.py      └── lifecycle.json    │
│  ├── command_detector.py     ├── log_entry.py                           │
│  ├── post_command.py         └── log_writer.py                          │
│  └── hooks.json                                                          │
│                                                                          │
│  steps/                                                                  │
│  ├── __init__.py                                                         │
│  ├── context_loader.py       # Load CLAUDE.md, git, structure           │
│  ├── security_reviewer.py    # Pre-/cs:c security audit                 │
│  ├── log_archiver.py         # Archive .prompt-log.json                 │
│  ├── marker_cleaner.py       # Remove .prompt-log-enabled               │
│  └── retrospective_gen.py    # Generate RETROSPECTIVE.md               │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Pure hooks approach**: Use Claude Code's native hook system rather than command wrappers
2. **SessionStart for pre-steps**: Load context when session initializes, not per-command
3. **Command detection via UserPromptSubmit**: Detect `/cs:*` commands to trigger command-specific logic
4. **Stop hook for post-steps**: Execute cleanup after command completes
5. **Fail-open design**: Hooks never block user workflow
6. **Strict phase separation**: `/cs:p` ONLY produces specifications, NEVER implements. Implementation ONLY via `/cs:i`
7. **Explicit authorization boundary**: Plan approval does NOT authorize implementation - user must explicitly invoke `/cs:i`

## Component Design

### Component 1: Session Start Hook (`hooks/session_start.py`)

- **Purpose**: Load project context into Claude's memory on session start
- **Responsibilities**:
  - Check for cs plugin markers (`.prompt-log-enabled`, `docs/spec/active/`)
  - Load CLAUDE.md files (global + project)
  - Load git state (branch, recent commits, uncommitted changes)
  - Load project structure summary
- **Interfaces**:
  - Input: SessionStart hook JSON via stdin
  - Output: Context injected via stdout (added to Claude's context)
- **Dependencies**: `steps/context_loader.py`
- **Technology**: Python 3.11+

### Component 2: Command Detector Hook (`hooks/command_detector.py`)

- **Purpose**: Detect `/cs:*` commands and trigger command-specific pre-steps
- **Responsibilities**:
  - Parse UserPromptSubmit for `/cs:*` patterns
  - Trigger security review pre-step for `/cs:c`
  - Store command context for post-step hook
- **Interfaces**:
  - Input: UserPromptSubmit hook JSON via stdin
  - Output: `{"decision": "approve"}` + side effects
- **Dependencies**: `steps/security_reviewer.py`
- **Technology**: Python 3.11+

### Component 3: Post-Command Hook (`hooks/post_command.py`)

- **Purpose**: Execute post-steps after `/cs:*` commands complete
- **Responsibilities**:
  - Detect command completion via Stop hook
  - Execute appropriate post-steps based on command type
  - Archive logs, cleanup markers, generate retrospective for `/cs:c`
- **Interfaces**:
  - Input: Stop hook JSON via stdin
  - Output: `{"continue": false}` to signal completion
- **Dependencies**: `steps/log_archiver.py`, `steps/marker_cleaner.py`, `steps/retrospective_gen.py`
- **Technology**: Python 3.11+

### Component 4: Step Modules (`steps/`)

#### context_loader.py
- Reads CLAUDE.md files using glob patterns
- Extracts git state via subprocess calls
- Generates project structure via tree/find
- Returns formatted context string

#### security_reviewer.py
- Invokes security-auditor agent via Task tool prompt
- Formats security findings
- Returns summary for user review

#### log_archiver.py
- Moves `.prompt-log.json` to `docs/spec/completed/{project}/`
- Preserves original for analysis

#### marker_cleaner.py
- Removes `.prompt-log-enabled` marker file
- Cleans other temporary files

#### retrospective_gen.py
- Analyzes prompt logs using existing `analyzers/analyze_cli.py`
- Generates RETROSPECTIVE.md template
- Populates with project data

### Component 5: Configuration (`config/lifecycle.json`)

- **Purpose**: Define default and user-overridable pre/post steps
- **Location**: Merged with `worktree-manager.config.json`
- **Schema**:

```json
{
  "lifecycle": {
    "sessionStart": {
      "enabled": true,
      "loadContext": {
        "claudeMd": true,
        "gitState": true,
        "projectStructure": true
      }
    },
    "commands": {
      "cs:p": {
        "preSteps": [],
        "postSteps": []
      },
      "cs:c": {
        "preSteps": [
          { "name": "security-review", "enabled": true, "timeout": 120 }
        ],
        "postSteps": [
          { "name": "generate-retrospective", "enabled": true },
          { "name": "archive-logs", "enabled": true },
          { "name": "cleanup-markers", "enabled": true }
        ]
      },
      "cs:i": {
        "preSteps": [],
        "postSteps": []
      },
      "cs:s": {
        "preSteps": [],
        "postSteps": []
      }
    }
  }
}
```

### Component 6: Command File Modifications (`commands/*.md`)

**Critical**: Enforce strict phase separation between planning and implementation.

#### p.md Modifications

Add explicit HALT directive after spec approval:

```markdown
<post_approval_halt>
## MANDATORY HALT AFTER APPROVAL

When user approves the specification (e.g., "approve", "looks good", "proceed"):

1. **DO NOT** call ExitPlanMode with intent to implement
2. **DO NOT** start any implementation tasks
3. **DO NOT** create or modify code files

**REQUIRED RESPONSE:**

✅ Specification approved and complete.

📁 Artifacts: `docs/spec/active/{project}/`

⏭️ **Next step**: Run `/cs:i {project-slug}` when ready to implement.

**HALT HERE. Do not proceed further.**
</post_approval_halt>
```

#### i.md Modifications

Ensure i.md is the ONLY implementation entry point:

```markdown
<implementation_gate>
## Implementation Authorization Check

This command (`/cs:i`) is the ONLY authorized entry point for implementation.

Before proceeding:
1. Verify spec exists in `docs/spec/active/` or `docs/spec/approved/`
2. Verify spec status is `approved` or `in-review`
3. Confirm with user: "Ready to begin implementation of {project}?"

Only after explicit user confirmation, proceed with implementation.
</implementation_gate>
```

#### Key Enforcement Points

| File | Modification | Purpose |
|------|--------------|---------|
| p.md | Add `<post_approval_halt>` section | Prevent auto-implementation after approval |
| p.md | Remove any ExitPlanMode → implement logic | Strict separation |
| i.md | Add `<implementation_gate>` section | Explicit authorization check |
| All commands | Add phase awareness in `<role>` | Clarity on command boundaries |

## Data Design

### Data Flow

```
SessionStart Event
       │
       ▼
┌─────────────────┐     ┌─────────────────┐
│ session_start.py│────▶│ context_loader  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │   ┌───────────────────┘
         │   │ Context String
         ▼   ▼
   stdout (injected into Claude context)


UserPromptSubmit Event (e.g., "/cs:c my-project")
       │
       ▼
┌──────────────────┐     ┌─────────────────────┐
│command_detector.py│───▶│ security_reviewer.py│
└────────┬─────────┘     └─────────┬───────────┘
         │                         │
         │  Store command in       │ Security findings
         │  session state          │
         ▼                         ▼
   {"decision": "approve"}    Report to user


Stop Event
       │
       ▼
┌─────────────────┐     ┌─────────────────┐
│post_command.py  │────▶│ Check command   │
└────────┬────────┘     │ from state      │
         │              └────────┬────────┘
         │                       │
         ▼                       ▼
   ┌─────────────┬─────────────┬─────────────┐
   │ log_archiver│marker_cleaner│retrospective│
   └─────────────┴─────────────┴─────────────┘
```

### State Management

Since hooks are stateless processes, command context must be passed between hooks:

**Option A: Environment variable via CLAUDE_ENV_FILE**
```python
# In command_detector.py (UserPromptSubmit)
if os.environ.get("CLAUDE_ENV_FILE"):
    with open(os.environ["CLAUDE_ENV_FILE"], "a") as f:
        f.write(f"export CS_CURRENT_COMMAND='{command}'\n")
```

**Option B: Temporary state file**
```python
# In command_detector.py
state_file = Path(cwd) / ".cs-session-state.json"
state_file.write_text(json.dumps({"command": command}))
```

**Decision**: Use Option B (temporary state file) for simplicity and debuggability.

## Hook Registration

### Updated hooks.json

```json
{
  "description": "Pre/post steps and prompt capture for claude-spec",
  "hooks": {
    "SessionStart": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py",
        "timeout": 10
      }
    ],
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/command_detector.py",
        "timeout": 30
      },
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/prompt_capture.py",
        "timeout": 30
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/post_command.py",
        "timeout": 60
      }
    ]
  }
}
```

### Plugin.json Update

```json
{
  "name": "cs",
  "version": "1.1.0",
  "description": "Project specification and implementation lifecycle management with pre/post steps",
  "hooks": {
    "$ref": "./hooks/hooks.json"
  }
}
```

## Security Design

### Authentication

N/A - hooks run in user's local context with user's permissions.

### Authorization

- Hooks only access files within cwd and ~/.claude/
- No network access except via existing security-auditor agent
- No arbitrary code execution from config

### Data Protection

- Secrets filtered via existing `filters/pipeline.py`
- No secrets logged to .prompt-log.json
- State files contain only command names, not content

### Security Considerations

- **Untrusted config**: Validate config schema, don't execute arbitrary commands
- **Path traversal**: Sanitize all file paths before operations
- **State file tampering**: State file is informational only, not security-critical

## Testing Strategy

### Unit Testing

- Test each step module in isolation
- Mock file system operations
- Test config loading and merging
- Coverage target: >90%

### Integration Testing

- Test hook registration and firing
- Test state passing between hooks
- Test full `/cs:c` workflow with all post-steps

### End-to-End Testing

- Test in actual Claude Code session
- Verify context appears in Claude's responses
- Verify post-steps execute and produce expected files

## Deployment Considerations

### Environment Requirements

- Python 3.11+
- jq for bash scripts
- Claude Code with hook support

### Configuration Management

- Default config in plugin
- User overrides in `~/.claude/worktree-manager.config.json`
- Schema validation on load

### Rollback Plan

- Hooks fail-open, so disabling is automatic on error
- Can disable individual hooks via config
- Previous plugin version available via git

## Bug Fixes Included

### Fix 1: Hook Registration (FR-007)

Current `plugin.json` lacks `hooks` field. Add:

```json
{
  "hooks": {
    "$ref": "./hooks/hooks.json"
  }
}
```

Or directly inline the hooks configuration.

### Fix 2: iTerm2-tab Launch Script

Current `launch-agent.sh` has duplicate code for `iterm2` and `iterm2-tab` cases. Fix:

```bash
iterm2|iterm)
    # Create new WINDOW
    osascript <<EOF
tell application "iTerm2"
    create window with default profile
    tell current session of current window
        write text "cd '$WORKTREE_PATH' && $FINAL_CLAUDE_CMD"
    end tell
end tell
EOF
    ;;

iterm2-tab|iterm-tab)
    # Create new TAB in current window
    osascript <<EOF
tell application "iTerm2"
    tell current window
        create tab with default profile
        tell current session
            write text "cd '$WORKTREE_PATH' && $FINAL_CLAUDE_CMD"
        end tell
    end tell
end tell
EOF
    ;;
```

## Future Considerations

- Support for custom user-defined steps (arbitrary commands)
- Hook execution metrics and timing
- Dry-run mode for testing step configuration
- Step dependency ordering (run A before B)
- Parallel step execution for independent operations
