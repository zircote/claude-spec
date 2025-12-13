---
document_type: decisions
project_id: SPEC-2025-12-13-001
---

# Pre and Post Steps - Architecture Decision Records

## ADR-001: Use Claude Code Native Hook System

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User, Claude

### Context

We need a mechanism to execute pre and post steps around `/cs:*` commands. Options include:
1. Claude Code's native hook system (SessionStart, Stop, UserPromptSubmit)
2. Command wrapper scripts
3. Embedded logic in command .md files

### Decision

Use Claude Code's native hook system with three hooks:
- SessionStart for context loading
- UserPromptSubmit for command detection and pre-steps
- Stop for post-steps

### Consequences

**Positive:**
- Leverages battle-tested Claude Code infrastructure
- Hooks are declarative and configurable
- Clean separation between command logic and lifecycle steps

**Negative:**
- Depends on Claude Code hook support (must verify availability)
- State passing between hooks requires workaround (temp files)

**Neutral:**
- Existing prompt_capture hook already uses this pattern

### Alternatives Considered

1. **Command wrapper scripts**: Would require modifying every command file. Rejected for maintenance burden.
2. **Embedded logic**: Already exists in p.md's `<mandatory_first_actions>`. Rejected because it's not configurable and duplicates across commands.

---

## ADR-002: SessionStart for Context Loading (Not Per-Command)

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User

### Context

Context loading (CLAUDE.md, git state, project structure) could happen:
1. Once on session start (SessionStart hook)
2. Before each /cs:* command (UserPromptSubmit hook)

### Decision

Load context once on session start via SessionStart hook.

### Consequences

**Positive:**
- Context loaded immediately, no waiting when first command runs
- Works even if user doesn't run /cs:* commands first
- Lower latency for command execution

**Negative:**
- Context may become stale during long sessions
- Context loaded even if user won't use cs commands

**Neutral:**
- Can add refresh mechanism later if needed

---

## ADR-003: Security Review as Pre-Step for /cs:c

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User

### Context

Security review could be:
1. A pre-step before /cs:c (audit before close-out)
2. A post-step after /cs:p (audit the plan)
3. A post-step after /cs:c (audit after close-out)
4. Applied to all commands

### Decision

Security review is a pre-step for `/cs:c` only.

### Consequences

**Positive:**
- Catches vulnerabilities before project is marked complete
- User can address findings before close-out
- Focused scope (only when closing projects)

**Negative:**
- Security issues found during planning not caught early
- User must wait for security review before close-out

**Neutral:**
- Can extend to other commands later based on feedback

---

## ADR-004: Configuration via worktree-manager.config.json

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User

### Context

Configuration for pre/post steps could be stored in:
1. Existing worktree-manager.config.json
2. New dedicated lifecycle.json file
3. Per-project .cs-config.json files

### Decision

Extend worktree-manager.config.json with a `lifecycle` section.

### Consequences

**Positive:**
- Single config file to manage
- Reuses existing config loading infrastructure
- Users already familiar with this file

**Negative:**
- Config file grows larger
- Per-project config not supported initially

**Neutral:**
- Can add per-project config support later

---

## ADR-005: Fail-Open Design for All Hooks

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User, Claude

### Context

When hooks encounter errors, they could:
1. Fail-open (log error, continue with command)
2. Fail-closed (block command execution)
3. Prompt user to decide

### Decision

All hooks follow fail-open design - errors are logged to stderr but never block command execution.

### Consequences

**Positive:**
- User workflow never blocked by hook failures
- Aligns with existing prompt_capture.py pattern
- Graceful degradation

**Negative:**
- User might miss important errors
- Silent failures possible

**Neutral:**
- Errors logged to stderr for debugging

---

## ADR-006: Temp File for Hook State Passing

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: Claude

### Context

Hooks are stateless processes. To pass command context from UserPromptSubmit to Stop hook, options include:
1. CLAUDE_ENV_FILE environment variable
2. Temporary state file (.cs-session-state.json)
3. Reading from transcript file

### Decision

Use temporary state file `.cs-session-state.json` in project directory.

### Consequences

**Positive:**
- Simple and debuggable
- Can be inspected during development
- Cleaned up by post-step

**Negative:**
- Creates temporary file
- Requires file system access

**Neutral:**
- CLAUDE_ENV_FILE could be added as alternative later

### Alternatives Considered

1. **CLAUDE_ENV_FILE**: More elegant but less debuggable. Could be added as enhancement.
2. **Transcript file**: Complex to parse, may change format.

---

## ADR-007: Strict Phase Separation - /cs:p NEVER Implements

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User

### Context

During specification work, Claude incorrectly proceeded to implementation after the user said "approve work", interpreting approval of the spec as authorization to implement. This highlighted a critical gap: no explicit boundary between planning and implementation phases.

Options:
1. Trust Claude to interpret user intent correctly (status quo)
2. Add explicit guards in command files to enforce phase boundaries
3. Require separate confirmation before implementation

### Decision

Enforce strict phase separation through command file modifications:
- `/cs:p` includes `<post_approval_halt>` section that HALTS after spec approval
- `/cs:i` is the ONLY authorized entry point for implementation
- Plan approval explicitly does NOT authorize implementation

### Consequences

**Positive:**
- Eliminates ambiguity between plan approval and implementation authorization
- Prevents unauthorized implementation
- User maintains explicit control over when implementation begins
- Clear audit trail (user must explicitly run /cs:i)

**Negative:**
- Extra step required to start implementation
- User cannot say "approve and implement" in one command

**Neutral:**
- Aligns with separation of concerns principle
- Similar to how code review approval doesn't auto-merge

### Implementation

**p.md modifications:**
```markdown
<post_approval_halt>
When user approves specification:
1. DO NOT call ExitPlanMode with intent to implement
2. DO NOT start implementation tasks
3. HALT and display: "Run /cs:i to implement"
</post_approval_halt>
```

**i.md modifications:**
```markdown
<implementation_gate>
This is the ONLY authorized implementation entry point.
Require explicit user confirmation before proceeding.
</implementation_gate>
```
