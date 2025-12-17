---
document_type: decisions
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T17:30:00Z
status: draft
---

# Architecture Decision Records (ADRs)

This document captures the key architectural decisions made during the design of the Draft PR Creation feature.

---

## ADR-001: Step Module Pattern for PR Operations

**Date**: 2025-12-17

**Status**: Accepted

### Context

We need to add PR creation and management capabilities to the `/cs:p` and `/cs:c` commands. The claude-spec plugin already has a well-established step execution system with:
- Pre/post steps configured via lifecycle configuration
- BaseStep class with execute() and validate() methods
- StepResult for consistent error handling
- Whitelist-based security in step_runner.py

### Decision

Implement PR operations as a new step module (`pr_manager.py`) following the existing pattern in `plugins/cs/steps/`.

### Consequences

**Positive**:
- Consistent with existing architecture
- Leverages existing whitelist security model
- Benefits from fail-open error handling in BaseStep
- Configurable via existing lifecycle configuration
- No changes needed to hook infrastructure

**Negative**:
- Must add new step to STEP_MODULES whitelist
- Must maintain parity with other step patterns

**Risks**:
- None significant - this follows established patterns

---

## ADR-002: Graceful Degradation for gh CLI

**Date**: 2025-12-17

**Status**: Accepted

### Context

The `gh` CLI is an external dependency that may not be installed or authenticated on all systems. We cannot make PR creation a hard requirement without breaking existing workflows.

### Decision

All PR operations will be wrapped in try/catch with graceful fallback. If `gh` is unavailable:
1. Log a warning message
2. Return `StepResult.ok()` with `skipped=True`
3. Continue with planning workflow normally

### Consequences

**Positive**:
- Aligns with plugin's fail-open philosophy
- Allows offline development scenarios
- Matches behavior of optional steps like security_reviewer
- No breaking changes to existing workflows

**Negative**:
- PR features silently disabled if gh not configured
- Users may not realize PR wasn't created

**Mitigations**:
- Clear warning message when skipping
- Document prerequisites in README
- Add `gh auth status` check in validate()

---

## ADR-003: PR URL Storage in README.md Frontmatter

**Date**: 2025-12-17

**Status**: Accepted

### Context

The PR URL needs to be stored persistently for:
1. Traceability - linking spec to its PR
2. Subsequent operations - `/cs:c` needs URL to call `gh pr ready`
3. User visibility - developers should see the PR URL

### Options Considered

| Option | Pros | Cons |
|--------|------|------|
| README.md frontmatter | Machine-parseable, visible, existing pattern | Modifies user file |
| Separate .pr-state.json | Clean separation, no file modification | Another file to track, gitignored? |
| Git notes | Follows memory system pattern | Complex, not visible |
| Environment variable | Simple | Not persistent across sessions |

### Decision

Store PR URL in the spec project's README.md YAML frontmatter as `draft_pr_url`.

### Consequences

**Positive**:
- README.md already contains project metadata
- YAML frontmatter is machine-parseable
- Visible to developers browsing the spec
- Consistent with existing fields like `github_issue`
- Committed to git for traceability

**Negative**:
- Modifies user-visible file
- Must handle file parsing/writing carefully

**Implementation Notes**:
- Use safe YAML parser that preserves formatting
- Atomic file writes to prevent corruption
- Validate URL format before writing

---

## ADR-004: Phase-Based Push Strategy

**Date**: 2025-12-17

**Status**: Accepted

### Context

We need to balance two concerns:
1. **Visibility**: Stakeholders want to see progress
2. **Noise reduction**: Too many commits/notifications is disruptive

### Options Considered

| Option | Visibility | Noise Level |
|--------|------------|-------------|
| Push every file change | High | Very High |
| Push at phase transitions | Good | Low |
| Push only on command completion | Low | Very Low |
| Manual push (user-triggered) | Variable | None |

### Decision

Push changes at phase transitions:
- Post-elicitation: After REQUIREMENTS.md finalized
- Post-research: After RESEARCH_NOTES.md created
- Post-design: After ARCHITECTURE.md, IMPLEMENTATION_PLAN.md

### Consequences

**Positive**:
- Aligns with natural planning workflow phases
- Provides meaningful commit boundaries
- Reduces notification noise
- Each push represents a complete unit of work

**Negative**:
- Less real-time visibility
- Phase transitions must be clearly defined

**Future Consideration**:
- Phase push automation could be added as a P2 feature
- Would require deeper integration with /cs:p command flow

---

## ADR-005: Title Format Convention

**Date**: 2025-12-17

**Status**: Accepted

### Context

Draft PRs need a consistent, recognizable title format that:
1. Identifies the PR as work-in-progress
2. Shows the project slug for quick identification
3. Provides human-readable description

### Decision

Use the format: `[WIP] {slug}: {project_name}`

Example: `[WIP] pull-request-draft-start: Draft PR Creation for /cs:p Workflow`

### Consequences

**Positive**:
- `[WIP]` prefix is a common convention
- Slug provides unique identifier
- Project name provides context
- Easy to filter in PR lists

**Negative**:
- Long titles may be truncated in UI
- Must update title when converting to ready (remove [WIP])

---

## Decision Log Summary

| ADR | Decision | Impact |
|-----|----------|--------|
| ADR-001 | Step module pattern | Follow existing architecture |
| ADR-002 | Graceful degradation | Never block on gh unavailability |
| ADR-003 | URL in README frontmatter | Persistent, visible storage |
| ADR-004 | Phase-based push | Balance visibility vs. noise |
| ADR-005 | [WIP] title format | Consistent identification |
