---
document_type: architecture
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T17:00:00Z
status: draft
---

# Draft PR Creation for /cs:p Workflow - Technical Architecture

## Overview

This document describes the technical architecture for integrating GitHub draft PR creation into the `/cs:p` planning workflow. The implementation follows the existing step module pattern and fail-open philosophy established in the claude-spec plugin.

## System Context

```
┌─────────────────────────────────────────────────────────────────────┐
│                          User Workflow                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   /cs:p "idea"                                                       │
│       │                                                              │
│       ▼                                                              │
│   ┌─────────────────┐     ┌──────────────────┐                      │
│   │ Create Branch   │────▶│ Create Artifacts │                      │
│   │ (worktree)      │     │ (REQUIREMENTS.md)│                      │
│   └─────────────────┘     └────────┬─────────┘                      │
│                                    │                                 │
│                                    ▼                                 │
│                           ┌──────────────────┐                      │
│                           │ PR Manager Step  │◀── NEW               │
│                           │ - Check gh auth  │                      │
│                           │ - Create draft PR│                      │
│                           │ - Store PR URL   │                      │
│                           └────────┬─────────┘                      │
│                                    │                                 │
│                                    ▼                                 │
│                           ┌──────────────────┐                      │
│                           │ Continue Planning│                      │
│                           │ (ARCH, IMPL_PLAN)│                      │
│                           └────────┬─────────┘                      │
│                                    │                                 │
│                                    ▼                                 │
│   /cs:c "project"                                                    │
│       │                                                              │
│       ▼                                                              │
│   ┌─────────────────┐                                               │
│   │ PR Ready Step   │◀── NEW                                        │
│   │ - gh pr ready   │                                               │
│   │ - Remove WIP    │                                               │
│   └─────────────────┘                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Architecture Decisions

### ADR-001: Step Module Pattern for PR Operations

**Status**: Accepted

**Context**: We need to add PR creation and management capabilities to the `/cs:p` and `/cs:c` commands. The plugin already has a well-established step execution system with pre/post steps.

**Decision**: Implement PR operations as step modules following the existing pattern in `plugins/cs/steps/`.

**Rationale**:
- Consistent with existing architecture (security_reviewer.py, retrospective_gen.py)
- Leverages existing whitelist security model
- Benefits from fail-open error handling in BaseStep
- Configurable via existing lifecycle configuration

**Consequences**:
- Must add new step to `STEP_MODULES` whitelist in `step_runner.py`
- Must add configuration entries in `worktree-manager.config.json`

### ADR-002: Graceful Degradation for gh CLI

**Status**: Accepted

**Context**: The `gh` CLI may not be installed or authenticated on all systems. We cannot make PR creation a hard requirement.

**Decision**: All PR operations will be wrapped in try/catch with graceful fallback. Planning continues normally if `gh` is unavailable.

**Rationale**:
- Aligns with plugin's fail-open philosophy
- Allows offline development scenarios
- Matches behavior of optional steps like security_reviewer

**Implementation**:
```python
def _check_gh_available(self) -> tuple[bool, str]:
    """Check if gh CLI is available and authenticated."""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return (False, "gh not authenticated")
        return (True, "")
    except FileNotFoundError:
        return (False, "gh CLI not installed")
    except subprocess.TimeoutExpired:
        return (False, "gh auth check timed out")
```

### ADR-003: PR URL Storage in README.md Frontmatter

**Status**: Accepted

**Context**: The PR URL needs to be stored persistently for traceability and for subsequent operations (e.g., `/cs:c` converting to ready).

**Decision**: Store PR URL in the spec project's README.md YAML frontmatter as `draft_pr_url`.

**Rationale**:
- README.md already contains project metadata
- YAML frontmatter is machine-parseable
- Visible to developers browsing the spec
- Consistent with existing fields like `github_issue`

**Example**:
```yaml
---
project_id: SPEC-2025-12-17-001
project_name: "Feature Name"
draft_pr_url: https://github.com/org/repo/pull/123
---
```

### ADR-004: Phase-Based Push Strategy

**Status**: Accepted

**Context**: We need to balance visibility (frequent pushes) against noise (too many commits/notifications).

**Decision**: Push changes at phase transitions: post-elicitation, post-research, post-design.

**Rationale**:
- Aligns with natural planning workflow phases
- Provides meaningful commit boundaries
- Reduces noise from work-in-progress commits

**Integration Points**: The `/cs:p` command definition in `p.md` includes clear phase markers that can trigger push operations.

## Component Design

### 1. PR Manager Step Module

**Location**: `plugins/cs/steps/pr_manager.py`

**Purpose**: Handle all GitHub PR operations (create, update, ready)

```python
class PRManagerStep(BaseStep):
    """Manages GitHub draft PR operations."""

    name = "pr-manager"

    # Operations this step can perform
    OPERATIONS = ["create", "update", "ready"]

    def validate(self) -> bool:
        """Check gh CLI availability (non-blocking)."""
        available, reason = self._check_gh_available()
        if not available:
            self._skip_reason = reason
        return True  # Always return True (fail-open)

    def execute(self) -> StepResult:
        """Execute the configured PR operation."""
        operation = self.config.get("operation", "create")

        if hasattr(self, "_skip_reason"):
            return StepResult.ok(
                f"PR {operation} skipped: {self._skip_reason}",
                skipped=True,
                reason=self._skip_reason
            ).add_warning(f"gh unavailable: {self._skip_reason}")

        if operation == "create":
            return self._create_draft_pr()
        elif operation == "update":
            return self._update_pr_body()
        elif operation == "ready":
            return self._mark_pr_ready()
        else:
            return StepResult.fail(f"Unknown operation: {operation}")
```

**Key Methods**:

| Method | Purpose | gh Command |
|--------|---------|------------|
| `_create_draft_pr()` | Create new draft PR | `gh pr create --draft` |
| `_update_pr_body()` | Update PR description | `gh pr edit --body` |
| `_mark_pr_ready()` | Convert draft to ready | `gh pr ready` |
| `_add_labels()` | Add labels to PR | `gh pr edit --add-label` |
| `_remove_labels()` | Remove labels from PR | `gh pr edit --remove-label` |
| `_store_pr_url()` | Save URL to README.md | File I/O |

### 2. Configuration Schema Extension

**File**: `~/.claude/worktree-manager.config.json`

**New Configuration Section**:
```json
{
  "lifecycle": {
    "commands": {
      "cs:p": {
        "postSteps": [
          {
            "name": "pr-manager",
            "enabled": true,
            "operation": "create",
            "labels": ["spec", "work-in-progress"],
            "title_format": "[WIP] {slug}: {project_name}",
            "base_branch": "main"
          }
        ]
      },
      "cs:c": {
        "preSteps": [
          { "name": "security-review", "enabled": true, "timeout": 120 }
        ],
        "postSteps": [
          {
            "name": "pr-manager",
            "enabled": true,
            "operation": "ready",
            "remove_labels": ["work-in-progress"]
          },
          { "name": "generate-retrospective", "enabled": true },
          { "name": "archive-logs", "enabled": true },
          { "name": "cleanup-markers", "enabled": true }
        ]
      }
    }
  }
}
```

**Configuration Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `operation` | string | "create" | PR operation: create, update, ready |
| `labels` | array | [] | Labels to add on PR creation |
| `remove_labels` | array | [] | Labels to remove (for ready operation) |
| `title_format` | string | "[WIP] {slug}: {project_name}" | PR title template |
| `base_branch` | string | "main" | Target branch for PR |
| `reviewers` | array | [] | Reviewers to request on ready |

### 3. Step Runner Whitelist Update

**File**: `plugins/cs/hooks/lib/step_runner.py`

**Change**: Add `pr-manager` to `STEP_MODULES`:
```python
STEP_MODULES = {
    "security-review": "security_reviewer",
    "context-loader": "context_loader",
    "generate-retrospective": "retrospective_gen",
    "archive-logs": "log_archiver",
    "cleanup-markers": "marker_cleaner",
    "pr-manager": "pr_manager",  # NEW
}
```

## Data Flow

### PR Creation Flow (during /cs:p)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ Artifacts   │     │ PR Manager   │     │ GitHub API  │
│ Created     │────▶│ Step         │────▶│ (via gh)    │
└─────────────┘     └──────┬───────┘     └──────┬──────┘
                          │                     │
                          ▼                     │
                   ┌──────────────┐             │
                   │ Parse spec   │             │
                   │ README.md    │             │
                   └──────┬───────┘             │
                          │                     │
                          ▼                     │
                   ┌──────────────┐             │
                   │ Build PR     │             │
                   │ title/body   │             │
                   └──────┬───────┘             │
                          │                     │
                          ▼                     │
                   ┌──────────────┐             │
                   │ gh pr create │─────────────▶
                   │ --draft      │
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Store PR URL │
                   │ in README.md │
                   └──────────────┘
```

### PR Ready Flow (during /cs:c)

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│ /cs:c       │     │ PR Manager   │     │ GitHub API  │
│ invoked     │────▶│ Step (ready) │────▶│ (via gh)    │
└─────────────┘     └──────┬───────┘     └──────┬──────┘
                          │                     │
                          ▼                     │
                   ┌──────────────┐             │
                   │ Read PR URL  │             │
                   │ from README  │             │
                   └──────┬───────┘             │
                          │                     │
                          ▼                     │
                   ┌──────────────┐             │
                   │ gh pr ready  │─────────────▶
                   └──────┬───────┘
                          │
                          ▼
                   ┌──────────────┐
                   │ Remove WIP   │─────────────▶
                   │ label        │
                   └──────────────┘
```

## Error Handling

### Error Categories (per ErrorCode enum)

| Scenario | ErrorCode | Retriable | Behavior |
|----------|-----------|-----------|----------|
| `gh` not installed | DEPENDENCY | No | Skip PR ops, continue planning |
| `gh` not authenticated | DEPENDENCY | No | Skip PR ops, warn user |
| Network timeout | TIMEOUT | Yes | Warn, continue planning |
| PR already exists | VALIDATION | No | Detect, update instead |
| Rate limit | IO | Yes | Warn, continue planning |
| Parse error | PARSE | No | Log, use defaults |

### Idempotency Considerations

1. **PR Already Exists**: Check `gh pr view` before `gh pr create`. If PR exists for branch, update instead of failing.

2. **URL Already Stored**: Before writing PR URL, check if already present. Skip write if unchanged.

3. **Labels Already Applied**: `gh pr edit --add-label` is idempotent—adding an existing label is a no-op.

## Integration Points

### 1. Command Definition Files

**File**: `plugins/cs/commands/p.md`

The PR manager step will be triggered as a post-step after artifact creation. No changes to the command file itself are needed—integration is via lifecycle configuration.

**File**: `plugins/cs/commands/c.md`

The PR ready operation will be triggered as a post-step. No changes to the command file itself are needed.

### 2. Hook System

The existing hook system (`command_detector.py`, `post_command.py`) will execute PR manager steps automatically based on lifecycle configuration. No changes to hook files are needed.

### 3. Memory System Integration

When a draft PR is created, capture a memory:
```python
# Auto-capture in pr_manager.py
if pr_created:
    # The memory system will capture this as "progress" type
    # via existing auto-capture integration
    pass
```

## Security Considerations

### 1. Credential Handling

- **No credentials stored**: The step relies entirely on `gh` CLI's credential management
- **No logging of tokens**: PR URLs are stored, but never auth tokens
- **No shell injection**: Commands are passed as lists, not shell strings

### 2. Step Whitelist

The `pr-manager` step must be added to `STEP_MODULES` in `step_runner.py` to be executable. This prevents arbitrary code execution.

### 3. PR Content

The PR body is constructed from spec documents that are already committed. No user-provided content is directly interpolated without sanitization.

## Testing Strategy

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `tests/steps/test_pr_manager.py` | Step logic, mocked subprocess |
| `tests/hooks/test_pr_lifecycle.py` | Integration with hook system |

### Test Scenarios

1. **Happy Path**: gh available, PR created successfully
2. **gh Not Installed**: Step skips gracefully
3. **gh Not Authenticated**: Step skips with warning
4. **PR Already Exists**: Detects and updates
5. **Network Timeout**: Fails gracefully, continues
6. **Offline Mode**: All PR ops skip, planning continues

### Mocking Strategy

```python
@pytest.fixture
def mock_gh_success(monkeypatch):
    """Mock successful gh commands."""
    def mock_run(*args, **kwargs):
        cmd = args[0]
        if "auth" in cmd:
            return subprocess.CompletedProcess(cmd, 0, "Logged in")
        if "pr" in cmd and "create" in cmd:
            return subprocess.CompletedProcess(
                cmd, 0, "https://github.com/org/repo/pull/123\n"
            )
        return subprocess.CompletedProcess(cmd, 0, "")
    monkeypatch.setattr(subprocess, "run", mock_run)
```

## Deployment Considerations

### Prerequisites

1. Users must have `gh` CLI installed for PR features
2. Users must run `gh auth login` before first use
3. Existing projects will not retroactively get PRs

### Migration

No migration needed—this is additive functionality. Existing projects continue to work without PR integration.

### Rollback

To disable PR features, users can set `enabled: false` in their lifecycle config:
```json
{
  "lifecycle": {
    "commands": {
      "cs:p": {
        "postSteps": [
          { "name": "pr-manager", "enabled": false }
        ]
      }
    }
  }
}
```

## Future Considerations

### Potential Extensions (Not in Scope)

1. **GitHub Projects Integration**: Auto-add PRs to project boards
2. **Issue Linking**: Automatically link PR to GitHub issue via "Closes #N"
3. **CI/CD for Specs**: Run validation on spec documents
4. **Multi-Repo Support**: Handle monorepo scenarios
5. **GitHub Enterprise**: Support GHE URLs

### Phase Push Automation

A future enhancement could automatically push and update PR body at each phase transition:
- Post-elicitation: Push REQUIREMENTS.md
- Post-research: Push RESEARCH_NOTES.md
- Post-design: Push ARCHITECTURE.md, IMPLEMENTATION_PLAN.md

This would require deeper integration with the `/cs:p` command flow.

## Appendix

### gh CLI Commands Reference

| Operation | Command | Expected Output |
|-----------|---------|-----------------|
| Check auth | `gh auth status` | Exit 0 if logged in |
| Create draft PR | `gh pr create --draft --title "..." --body "..."` | PR URL on stdout |
| View PR | `gh pr view --json url` | JSON with URL |
| Update PR body | `gh pr edit --body "..."` | Empty on success |
| Mark ready | `gh pr ready` | Empty on success |
| Add label | `gh pr edit --add-label "label"` | Empty on success |
| Remove label | `gh pr edit --remove-label "label"` | Empty on success |

### Existing Step Module Files (Reference)

| File | Purpose | Pattern to Follow |
|------|---------|-------------------|
| `base.py` | BaseStep, StepResult, ErrorCode | Class structure, error handling |
| `security_reviewer.py` | Pre-step with external tool | subprocess handling, fail-open |
| `retrospective_gen.py` | Post-step with file I/O | File manipulation pattern |
| `context_loader.py` | Context loading | Configuration reading |
