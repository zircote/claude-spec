---
document_type: research
project_id: SPEC-2025-12-13-001
last_updated: 2025-12-13T00:00:00Z
---

# Pre and Post Steps - Research Notes

## Research Summary

This research analyzed Claude Code's hook system, the existing cs plugin architecture, and configuration patterns to inform the design of pre/post steps.

## Claude Code Hook System

### Available Hook Events

| Event | Timing | Can Block | Use Case |
|-------|--------|-----------|----------|
| SessionStart | Session init/resume | No | Context loading |
| SessionEnd | Session termination | No | Cleanup |
| UserPromptSubmit | User submits prompt | Yes | Command detection, validation |
| PreToolUse | Before tool execution | Yes | Tool interception |
| PostToolUse | After tool execution | Yes | Result processing |
| Stop | Agent completion | Yes | Post-steps |
| SubagentStop | Subagent completion | Yes | Subagent control |
| Notification | Notification sent | No | Custom notifications |
| PreCompact | Before context compact | No | Pre-compact setup |
| PermissionRequest | Permission dialog | Yes | Auto-approval |

### Key Findings

1. **SessionStart is ideal for context loading** - runs on init/resume, can persist env vars
2. **UserPromptSubmit can detect commands** - receives full prompt, can add context
3. **Stop hook can run post-steps** - fires when agent completes
4. **Hooks output to stdout** - for SessionStart/UserPromptSubmit, stdout is added to context

### Hook Input/Output Contract

**Input** (stdin JSON):
```json
{
  "hook_event_name": "SessionStart",
  "session_id": "string",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/working/directory",
  "permission_mode": "default"
}
```

**Output** (stdout JSON or plain text):
- Exit code 0 = success
- Exit code 2 = blocking error
- For SessionStart/UserPromptSubmit: stdout text added to context

## Codebase Analysis

### Existing Hook Pattern (prompt_capture.py)

| Pattern | Implementation |
|---------|----------------|
| Entry point | `if __name__ == "__main__": main()` |
| Input handling | `json.load(sys.stdin)` |
| Output handling | `print(json.dumps(response))` |
| Error handling | stderr for errors, fail-open |
| Conditional enable | Check marker file existence |
| Filter pipeline | Import from filters/ package |

### Command Structure

Commands use XML-like sections:
- `<mandatory_first_actions>` - Pre-flight checks (exists in p.md)
- `<execution_protocol>` - Main logic
- `<finalization_checklist>` - Post-execution (exists in p.md)

### Configuration System

Three-tier config with fallback:
```
User Config (~/.claude/worktree-manager.config.json)
    ↓ fallback
Template Config (config.template.json)
    ↓ fallback
Hardcoded Defaults
```

Key functions in `lib/config.sh`:
- `get_config(key, default)` - top-level values
- `get_config_nested(dotpath, default)` - nested values
- `has_user_config()` - check for user config
- `needs_setup()` - check if setup needed

## Bug Analysis

### Bug 1: Hook Registration Not Working

**Symptom**: prompt_capture.py not firing despite marker file present

**Root Cause**:
- `plugin.json` lacks `hooks` field
- Claude Code doesn't auto-discover hooks.json
- No hooks configured in `~/.claude/settings.json`

**Fix**: Add hooks reference to plugin.json:
```json
{
  "hooks": "./hooks/hooks.json"
}
```

### Bug 2: iTerm2-tab Duplicate Code

**Symptom**: Both `iterm2` and `iterm2-tab` cases create tabs

**Root Cause**: Copy-paste error in launch-agent.sh lines 182-206

**Fix**: Differentiate behavior:
- `iterm2`: Create new window
- `iterm2-tab`: Create new tab in current window

## Technical Research

### Best Practices

| Topic | Source | Key Insight |
|-------|--------|-------------|
| Hook design | Claude Code docs | Fail-open, use stderr for errors |
| State passing | Session hooks | Use CLAUDE_ENV_FILE or temp files |
| Config schema | worktree-manager | JSON with nested objects, dot-path access |

### Recommended Approaches

1. **For context loading**: Use SessionStart hook with stdout for context injection
2. **For command detection**: Regex patterns in UserPromptSubmit hook
3. **For post-steps**: Stop hook with state file to know which command ran
4. **For configuration**: Extend existing worktree-manager.config.json

### Anti-Patterns to Avoid

1. **Blocking hooks for non-critical errors**: Always fail-open
2. **Large context injection**: Keep context concise, Claude has limits
3. **Synchronous security scans**: Use timeout, show progress
4. **Hardcoded paths**: Use config and environment variables

## Dependency Analysis

### Required Dependencies

| Dependency | Purpose | Already Available |
|------------|---------|-------------------|
| Python 3.11+ | Hook scripts | Yes |
| jq | JSON processing in bash | Yes |
| security-auditor agent | Security review step | Yes (in ~/.claude/agents/) |

### No New External Dependencies Required

All functionality can be implemented with existing dependencies.

## Open Questions Resolved

| Question | Resolution |
|----------|------------|
| What hooks are available? | 10 hooks including SessionStart, Stop |
| Can we detect commands? | Yes, via UserPromptSubmit prompt text |
| How to pass state between hooks? | Temp file or CLAUDE_ENV_FILE |
| Should hooks block? | No, fail-open design |

## Sources

- Claude Code Hooks Documentation (via claude-code-guide agent)
- Existing plugin code analysis (hooks/prompt_capture.py)
- Config system analysis (lib/config.sh)
- Command structure analysis (commands/*.md)
