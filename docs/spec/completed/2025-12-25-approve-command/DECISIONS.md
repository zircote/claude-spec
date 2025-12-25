---
document_type: decisions
project_id: SPEC-2025-12-25-001
---

# Add /approve Command - Architecture Decision Records

## ADR-001: Warn-Only Enforcement in /implement

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

When implementing an unapproved spec, should `/implement` block execution or just warn?

### Decision

Warn but allow proceeding. `/implement` will display a warning when the spec status is `draft` or `in-review`, but will not block execution.

### Consequences

**Positive:**
- Doesn't disrupt existing workflows
- Users can proceed in urgent situations
- Lower friction for adoption

**Negative:**
- Governance is advisory, not enforced
- Users can ignore warnings

**Neutral:**
- Hook-based enforcement provides stricter option if needed

### Alternatives Considered

1. **Strict enforcement**: Rejected because it could disrupt emergency workflows
2. **Configurable**: Considered for P2 but adds complexity for initial release

---

## ADR-002: Git User for Approver Identity

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

How should the approver identity be captured and recorded?

### Decision

Use `git config user.name` and `git config user.email` to construct the approver identity in format `"Name <email>"`.

### Consequences

**Positive:**
- Reliable, automated capture
- Consistent with git commit authorship
- No additional user input required

**Negative:**
- Requires git to be configured
- Can't easily override for delegated approval

**Neutral:**
- Fallback to "user" if git config empty

### Alternatives Considered

1. **Prompt for name**: Rejected - adds friction
2. **Implicit "user"**: Rejected - loses identity information

---

## ADR-003: Rejection Moves to rejected/ Folder

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

What should happen when a spec is rejected during `/approve`?

### Decision

Create a `docs/spec/rejected/` directory and move the rejected spec there, preserving all files with rejection metadata added to README.md.

### Consequences

**Positive:**
- Clean separation from active work
- Preserves work for future reference
- Clear audit trail

**Negative:**
- Creates additional directory to maintain
- Rejected specs accumulate

**Neutral:**
- Can be cleaned up periodically

### Alternatives Considered

1. **Add rejection notes, keep in active/**: Rejected - clutters active folder
2. **Delete spec**: Rejected - loses work, no audit trail

---

## ADR-004: Hook-Based Prevention for Implementation Skip

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

How do we prevent Claude from accidentally skipping the planning phase and jumping directly to implementation?

### Decision

Implement a multi-layered prevention approach:
1. PreToolUse hook that blocks Write/Edit to implementation files without approved spec
2. Explicit NEVER IMPLEMENT warnings in /plan command
3. Status gate warning in /implement
4. Workflow documentation in CLAUDE.md

### Consequences

**Positive:**
- Multiple safeguards reduce risk
- Hook provides hard enforcement when enabled
- Documentation provides human guidance
- Layered approach catches different failure modes

**Negative:**
- Hook may be overly restrictive for some workflows
- Multiple places to maintain

**Neutral:**
- Hook can be disabled if needed

### Alternatives Considered

1. **Hook only**: Insufficient - doesn't address instruction following
2. **Documentation only**: Insufficient - Claude can still skip
3. **Single point of enforcement**: Rejected - single point of failure

---

## ADR-005: Include /plan Flags in This Spec

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

Should the `/plan` workflow flexibility flags (`--no-worktree`, `--no-branch`, `--inline`) be part of this spec or a separate one?

### Decision

Include in this spec. The flags are directly related to the workflow improvements and small enough to not warrant a separate specification.

### Consequences

**Positive:**
- Single coherent workflow improvement
- Reduces spec overhead
- Delivered together for consistent experience

**Negative:**
- Slightly larger scope for this spec

**Neutral:**
- Implementation phases are still cleanly separated
