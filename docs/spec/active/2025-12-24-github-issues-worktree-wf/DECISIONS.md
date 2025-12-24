---
document_type: decisions
project_id: SPEC-2025-12-24-001
---

# GitHub Issues Worktree Workflow - Architecture Decision Records

## ADR-001: Trigger Mechanism for GitHub Issues Workflow

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

We need a way to trigger the GitHub issues workflow. Options considered:
1. New command (`/claude-spec:plan-issues`)
2. Flag on existing command (`/claude-spec:plan --from-issues`)
3. Auto-detect when no arguments provided
4. Interactive menu in plan workflow

### Decision

Auto-detect when `/claude-spec:plan` is run with no arguments.

### Consequences

**Positive:**
- No new command to learn or remember
- Natural entry point when user doesn't have a specific idea
- Preserves existing `/plan <seed>` workflow unchanged
- Progressive disclosure - feature only appears when relevant

**Negative:**
- Slightly less discoverable than explicit command
- User must know to run `/plan` without args

**Neutral:**
- Requires Step 0 argument parsing modification

### Alternatives Considered

1. **New command**: Rejected - increases command surface area, harder to discover
2. **Flag**: Rejected - requires users to remember flag syntax
3. **Interactive menu**: Rejected - adds friction to existing seed-based workflow

---

## ADR-002: GitHub Integration Approach

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: Technical analysis

### Context

Need to integrate with GitHub for issue fetching and comment posting. Options:
1. Direct GitHub API calls (requires token management)
2. Use `gh` CLI (leverages existing user authentication)
3. GitHub Actions integration (for automated workflows)

### Decision

Use `gh` CLI via subprocess calls.

### Consequences

**Positive:**
- No token management in plugin code
- Leverages user's existing authentication
- Rich feature set (filtering, pagination, JSON output)
- Consistent with user's existing GitHub workflow

**Negative:**
- Requires `gh` CLI to be installed
- Subprocess calls add slight overhead
- Dependent on `gh` CLI behavior/updates

**Neutral:**
- Output parsing required for JSON responses

### Alternatives Considered

1. **Direct API**: Rejected - requires secure token storage, additional complexity
2. **GitHub Actions**: Rejected - not applicable for interactive CLI workflow

---

## ADR-003: Branch Naming Convention

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

Need to generate branch names for issue-based worktrees. Options:
1. Simple pattern: `issue/42-title`
2. Conventional commits: `{type}/42-title` based on labels
3. User-specified per issue
4. Fixed prefix with configurable mapping

### Decision

Auto-detect branch prefix from issue labels using conventional commit types:
- `bug` label → `bug/` prefix
- `documentation`/`docs` label → `docs/` prefix
- `chore`/`maintenance` label → `chore/` prefix
- `enhancement`/`feature` (or default) → `feat/` prefix

Format: `{prefix}/{issue_number}-{slugified_title}`

### Consequences

**Positive:**
- Aligns with conventional commits workflow
- Semantic meaning in branch names
- Automated - no manual input required
- Works with most GitHub label conventions

**Negative:**
- May not match all project conventions
- Priority logic may conflict with multi-labeled issues

**Neutral:**
- Configurable mapping can be added as enhancement

### Alternatives Considered

1. **Simple pattern**: Rejected - loses semantic information
2. **User-specified**: Rejected - adds friction to parallel worktree creation
3. **Fixed prefix**: Rejected - not as flexible

---

## ADR-004: Multi-Issue Selection and Parallel Creation

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

Should users select one issue at a time or multiple? If multiple, how should worktrees be created?

Options:
1. Single issue per `/plan` invocation
2. Multi-select with sequential worktree creation
3. Multi-select with parallel worktree creation
4. Multi-select with parallel terminal launches

### Decision

Multi-select issues with parallel worktree creation AND parallel terminal launches.

### Consequences

**Positive:**
- Efficient setup for multiple tasks
- Matches "spin up worktrees" mental model
- Leverages existing parallel infrastructure

**Negative:**
- More complex implementation
- Multiple terminals may overwhelm some users
- Resource usage scales with selection count

**Neutral:**
- Port allocation must be done upfront for all worktrees

### Alternatives Considered

1. **Single only**: Rejected - too limiting for power users
2. **Sequential**: Rejected - slower, no benefit over parallel

---

## ADR-005: Issue Completeness Evaluation Method

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

How to determine if an issue has sufficient detail for planning? Options:
1. Checkbox criteria (has description, has acceptance criteria, etc.)
2. AI evaluation based on elicitation readiness
3. User self-assessment
4. Skip evaluation entirely

### Decision

AI evaluation based on whether the issue provides enough context to begin meaningful requirements elicitation with reasonable confidence.

### Consequences

**Positive:**
- Flexible - handles varied issue formats
- Context-aware - understands what's specifically missing
- Can generate targeted clarification requests

**Negative:**
- Subjective - AI judgment may differ from user judgment
- Inconsistent - may vary between evaluations

**Neutral:**
- User always has final say (can proceed anyway)

### Alternatives Considered

1. **Checkbox criteria**: Rejected - too rigid, many false negatives
2. **User self-assessment**: Rejected - adds friction without AI insight
3. **Skip**: Rejected - misses opportunity to improve workflow

---

## ADR-006: Clarification Comment Workflow

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

When posting clarification comments to GitHub, what level of user control?

Options:
1. Draft → Show → Auto-post
2. Draft → Show → Confirm → Post
3. Draft → User edits → Post
4. Copy to clipboard only

### Decision

Draft → Show to user → Confirm via AskUserQuestion → Post.

### Consequences

**Positive:**
- User reviews before public posting
- Prevents accidental posts
- Professional quality control

**Negative:**
- Extra interaction step
- User might just want to post quickly

**Neutral:**
- Could add "edit" option in confirmation

### Alternatives Considered

1. **Auto-post**: Rejected - too risky for public comments
2. **User edits**: Partially adopted - edit option available
3. **Clipboard only**: Rejected - too much friction

---

## ADR-007: Issue Context Storage

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: Technical analysis

### Context

Where to store issue context for the worktree session?

Options:
1. Pass entirely via command line prompt
2. Store in `.issue-context.json` in worktree
3. Store in global registry
4. Fetch on-demand from GitHub

### Decision

Store in `.issue-context.json` file at worktree root.

### Consequences

**Positive:**
- Available offline after initial fetch
- Can be read by subsequent tools/commands
- Survives session restarts
- Enables enrichment (user-added details)

**Negative:**
- May become stale if issue updated on GitHub
- Additional file in worktree

**Neutral:**
- Registry also updated with issue reference (for tracking)

### Alternatives Considered

1. **Command line only**: Rejected - lost on session restart
2. **Registry only**: Rejected - harder to access from worktree
3. **On-demand fetch**: Rejected - requires network, may fail

---

## ADR-008: Comment Tone and Style

**Date**: 2025-12-24
**Status**: Accepted
**Deciders**: User (via elicitation)

### Context

What tone should automatically drafted clarification comments have?

Options:
1. Professional/formal
2. Friendly/casual
3. Template-based (configurable)
4. AI-generated contextual

### Decision

Professional/formal tone.

### Consequences

**Positive:**
- Appropriate for all project contexts
- Maintains credibility
- Consistent quality

**Negative:**
- May feel impersonal
- May not match casual project cultures

**Neutral:**
- Content is still contextual (mentions specific missing items)

### Alternatives Considered

1. **Friendly**: Rejected - may be inappropriate for some contexts
2. **Template-based**: Deferred - could add as enhancement
3. **AI-contextual**: Partially adopted - content is contextual, tone is fixed
