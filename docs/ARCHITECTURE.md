# claude-spec Technical Architecture

This document describes the internal architecture of the claude-spec plugin.

## Overview

claude-spec is a Claude Code plugin that provides structured project specification and implementation lifecycle management. It consists of three major subsystems:

1. **Command System** — Slash commands for user interaction
2. **Filter Pipeline** — Content processing and secret detection
3. **Worktree Manager** — Git worktree automation

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Claude Code CLI                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
            ┌───────────────┐                   ┌───────────────┐
            │   Commands    │                   │    Skills     │
            │   (/*)        │                   │  (worktree)   │
            └───────────────┘                   └───────────────┘
                    │                                   │
                    ▼                                   ▼
            ┌─────────────────────────────────────────────────────┐
            │                   File System                        │
            │       docs/spec/       │       worktree-registry    │
            └─────────────────────────────────────────────────────┘
```

## Component Details

### 1. Plugin Metadata

**Location:** `.claude-plugin/plugin.json`

```json
{
  "name": "claude-spec",
  "version": "2.0.0",
  "description": "Project specification and lifecycle management"
}
```

### 2. Command System

Commands are Markdown files with YAML frontmatter. Claude Code parses these and exposes them as slash commands.

**Command Resolution:**
```
/plan → commands/plan.md
/implement → commands/implement.md
/worktree-create → commands/worktree-create.md
```

**Frontmatter Schema:**
```yaml
---
argument-hint: <arg> [optional]    # Shown in autocomplete
description: Brief description      # Shown in /help
model: claude-opus-4-5-20251101    # Optional model override
allowed-tools: Read, Write, Bash   # Tool restrictions
---
```

**Command Architecture Pattern:**

```markdown
<role>
You are a [Role Name]. Your job is to [responsibility].
</role>

<command_argument>
$ARGUMENTS
</command_argument>

<protocol>
## Step 1: [Name]
[Clear instructions]

## Step 2: [Name]
[More instructions]
</protocol>

<edge_cases>
### [Case Name]
[How to handle]
</edge_cases>
```

### 3. Filter Pipeline

**Location:** `filters/`

**Module Structure:**
```
filters/
├── __init__.py      # Package exports
├── pipeline.py      # Main filter orchestration
├── log_entry.py     # Log entry data structure
└── log_writer.py    # Atomic file operations
```

**Pipeline Flow:**

```
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ Raw Content   │───▶│ Secret Filter │───▶│  Truncation   │
└───────────────┘    └───────────────┘    └───────────────┘
                                                   │
                                                   ▼
┌───────────────────────────────────────────────────────────┐
│ FilteredContent                                           │
│ {                                                         │
│   "filtered_content": "...[SECRET:aws_access_key]...",   │
│   "original_length": 1234,                               │
│   "was_truncated": false,                                │
│   "secrets_found": ["aws_access_key"],                   │
│   "filter_timestamp": "2025-12-12T..."                   │
│ }                                                         │
└───────────────────────────────────────────────────────────┘
```

**Secret Patterns:**

| Pattern Name | Regex | Replacement |
|-------------|-------|-------------|
| AWS Access Key | `A3T[A-Z0-9]\|AKIA\|ASIA...` | `[SECRET:aws_access_key]` |
| AWS Secret Key | `[A-Za-z0-9/+=]{40}` | `[SECRET:aws_secret_key]` |
| GitHub PAT | `ghp_[A-Za-z0-9_]{36,}` | `[SECRET:github_token]` |
| OpenAI Key | `sk-..T3BlbkFJ...` | `[SECRET:openai_key]` |
| Anthropic Key | `sk-ant-api...` | `[SECRET:anthropic_key]` |
| JWT | `ey...\.ey...` | `[SECRET:jwt]` |
| Database URI | `postgres(ql)?://...` | `[SECRET:database_url]` |

### 4. Log Writer

**Atomic Write Pattern:**

```python
def append_entry(self, entry: LogEntry) -> None:
    with open(self.log_path, "a", encoding="utf-8") as f:
        # Acquire exclusive lock
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        try:
            f.write(entry.to_json() + "\n")
            f.flush()
            os.fsync(f.fileno())  # Ensure write to disk
        finally:
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
```

This ensures:
- No partial writes from concurrent access
- Data is persisted before lock release
- NDJSON format (one JSON object per line)

### 5. Worktree Manager

**Location:** `skills/worktree-manager/`

**Components:**
```
worktree-manager/
├── SKILL.md          # Skill documentation & trigger phrases
├── config.json       # Configuration
└── scripts/
    ├── allocate-ports.sh   # Port allocation
    ├── register.sh         # Registry management
    ├── release-ports.sh    # Port release
    ├── launch-agent.sh     # Terminal launching
    ├── status.sh           # Status reporting
    └── cleanup.sh          # Cleanup operations
```

**Global Registry:**

Location: `~/.claude/worktree-registry.json`

```json
{
  "worktrees": [
    {
      "id": "uuid",
      "project": "my-project",
      "branch": "feature/auth",
      "branchSlug": "feature-auth",
      "worktreePath": "/Users/.../worktrees/my-project/feature-auth",
      "repoPath": "/Users/.../my-project",
      "ports": [8100, 8101],
      "createdAt": "2025-12-12T10:00:00Z",
      "status": "active"
    }
  ],
  "portPool": {
    "start": 8100,
    "end": 8199,
    "allocated": [8100, 8101]
  }
}
```

**Port Allocation Algorithm:**

```bash
# Find first available port in range
for ((port=PORT_START; port<=PORT_END; port++)); do
    # Check registry
    if ! echo "$ALLOCATED_PORTS" | grep -q "^${port}$"; then
        # Check system
        if ! lsof -i :"$port" &>/dev/null; then
            # Port available
            FOUND_PORTS+=("$port")
        fi
    fi
done
```

**Multi-Terminal Support:**

```bash
case "$TERMINAL" in
    ghostty)
        open -na "Ghostty.app" --args -e "$SHELL_CMD" -c "$INNER_CMD"
        ;;
    iterm2|iterm)
        osascript <<EOF
tell application "iTerm2"
    create window with default profile
    tell current session of current window
        write text "cd '$WORKTREE_PATH' && $CLAUDE_CMD"
    end tell
end tell
EOF
        ;;
    tmux)
        tmux new-session -d -s "$SESSION_NAME" -c "$WORKTREE_PATH" ...
        ;;
    # ... wezterm, kitty, alacritty
esac
```

## Data Flow Diagrams

### Planning Flow (/plan)

```
┌─────────────────────────────────────────────────────────────────┐
│ User: /plan "implement user authentication"                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 0: Worktree Check                                         │
│ IF on protected branch (main, master, develop):                 │
│   → Recommend /worktree-create                                  │
│   → STOP (user restarts in worktree)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 1: Socratic Elicitation                                   │
│ - Ask 3-4 questions per round                                   │
│ - Continue until 7 clarity checkpoints met                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phase 2: Parallel Research                                      │
│ PARALLEL:                                                       │
│   Task subagent 1: External research                           │
│   Task subagent 2: Codebase analysis                           │
│   Task subagent 3: Security assessment                         │
│   Task subagent 4: Technical feasibility                       │
│ WAIT FOR ALL → Synthesize                                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Phases 3-6: Documentation Generation                            │
│ 3: REQUIREMENTS.md (from elicitation)                          │
│ 4: ARCHITECTURE.md (from research synthesis)                   │
│ 5: IMPLEMENTATION_PLAN.md (phased tasks)                       │
│ 6: Cross-reference check & user approval                       │
└─────────────────────────────────────────────────────────────────┘
```

### Document Sync Flow (/implement)

```
┌─────────────────────────────────────────────────────────────────┐
│ Task status changes: pending → in-progress → done               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Update PROGRESS.md (source of truth)                         │
│    - Task row: status, started, completed timestamps            │
│    - Recalculate phase progress %                               │
│    - Recalculate overall progress %                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Sync IMPLEMENTATION_PLAN.md                                  │
│    - Find matching task checkbox                                │
│    - Update: [ ] → [x] or vice versa                           │
│    - Update status emoji: ⬜ → ✅                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Update README.md frontmatter                                 │
│    - Update status field if phase changes                       │
│    - Update progress percentage                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Add CHANGELOG.md entry (if significant)                      │
│    - Record what changed                                        │
│    - Include timestamp                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling

### File Operation Errors

```python
class LogWriter:
    def append_entry(self, entry: LogEntry) -> None:
        try:
            # ... atomic write
        except IOError as e:
            # Log but don't raise
            print(f"Log write failed: {e}", file=sys.stderr)
```

### Worktree Script Errors

```bash
# Always verify prerequisites
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required" >&2
    exit 1
fi

# Verify paths exist
if [ ! -d "$WORKTREE_PATH" ]; then
    echo "Error: Worktree not found: $WORKTREE_PATH" >&2
    exit 1
fi
```

## Security Considerations

### 1. Secret Filtering

Content passes through the filter pipeline before any logging. Secrets are detected using regex patterns and replaced with type markers.

**Limitations:**
- Pattern-based detection may miss custom secret formats
- Very long secrets may not be fully matched
- Context around secrets is preserved

### 2. File Permissions

- Log files created with default umask
- Registry file at `~/.claude/` inherits directory permissions
- No explicit permission hardening

### 3. Code Injection Prevention

- Template variables use simple string substitution
- Shell scripts quote all variables
- No dynamic code execution or string-to-code conversion

## Extensibility

### Adding New Commands

1. Create `commands/newcmd.md`
2. Add YAML frontmatter
3. Define role, protocol, edge cases
4. Register in `.claude-plugin/plugin.json`

### Adding Secret Patterns

Edit `filters/pipeline.py`:

```python
SECRET_PATTERNS = [
    # Existing patterns...
    (r'new_pattern_regex', 'new_secret_type'),
]
```

### Adding Terminal Support

Edit `skills/worktree-manager/scripts/launch-agent.sh`:

```bash
case "$TERMINAL" in
    # Existing terminals...
    new-terminal)
        new-terminal-command --working-dir "$WORKTREE_PATH" ...
        ;;
esac
```

## Future Considerations

1. **Metrics Aggregation** — Cross-project analytics from retrospectives
2. **Remote Registry** — Sync worktree registry across machines
3. **Custom Templates** — User-defined project templates
4. **Webhook Integration** — Post events to external systems
