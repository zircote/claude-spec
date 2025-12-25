---
document_type: decisions
project_id: SPEC-2025-12-25-001
---

# Implement Command UX Improvements - Architecture Decision Records

## ADR-001: Immediate Checkbox Sync vs Batched

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User

### Context

When tasks are marked complete in PROGRESS.md, we need to update corresponding checkboxes in IMPLEMENTATION_PLAN.md. Options:
1. Immediate sync on each task update
2. Batch sync at end of phase
3. Manual trigger command

### Decision

Implement **immediate sync** on each task status change.

### Consequences

**Positive:**
- Documents never drift out of sync
- User sees immediate feedback
- No separate command to remember

**Negative:**
- More file I/O (read/write per task)
- Slightly more complex implementation

**Neutral:**
- Atomic write pattern handles safety

---

## ADR-002: Extended YAML Object for Argument Hints

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User

### Context

Current `argument-hint` is a single string. Options for enhancement:
1. Extended YAML object in frontmatter
2. Separate JSON Schema file
3. Inline annotations (e.g., `<path:dir>`)
4. Keep simple, enhance only --help

### Decision

Use **extended YAML object** in command frontmatter.

### Consequences

**Positive:**
- Single source of truth (colocated with command)
- Native YAML - no additional parsing
- Rich metadata (types, examples, patterns)

**Negative:**
- Larger frontmatter section
- More complex schema to maintain

**Neutral:**
- Backward compatible with simple string format

### Alternatives Considered

1. **JSON Schema file**: Too much indirection, separate file to maintain
2. **Inline annotations**: Less readable, limited expressiveness
3. **Enhanced --help only**: Loses programmatic access to arg metadata

---

## ADR-003: Error + Suggestion Pattern for Validation

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: User

### Context

How to handle invalid arguments:
1. Error + full --help output
2. Error + "Did you mean..." suggestion
3. Interactive prompt via AskUserQuestion
4. Combination based on context

### Decision

Use **Error + Suggestion** pattern (Levenshtein-based).

### Consequences

**Positive:**
- Matches familiar CLI patterns (git, npm)
- Fast feedback without overwhelming output
- Actionable - user knows exact fix

**Negative:**
- Need to implement Levenshtein distance
- May miss suggestions for distant typos

**Neutral:**
- Can add --help hint in error message

---

## ADR-004: PROGRESS.md as Source of Truth

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: Technical team (implied from existing implementation)

### Context

Multiple documents track task status:
- PROGRESS.md (explicit status tracking)
- IMPLEMENTATION_PLAN.md (acceptance criteria checkboxes)
- README.md (status field)

Which is authoritative?

### Decision

**PROGRESS.md is the source of truth** for task status. Other documents are updated FROM it.

### Consequences

**Positive:**
- Clear ownership of status
- Sync direction is unambiguous
- Simpler conflict resolution

**Negative:**
- One-way sync only (for now)
- Manual edits to IMPLEMENTATION_PLAN.md checkboxes may be overwritten

**Neutral:**
- Future: Could add bidirectional sync (P2)

---

## ADR-005: Atomic File Writes with Backup

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: Technical team

### Context

Checkbox sync modifies IMPLEMENTATION_PLAN.md. File corruption risks:
- Partial writes if interrupted
- Lost data on failure
- Concurrent access issues

### Decision

Use **atomic write protocol**: backup → write to temp → rename → delete backup.

### Consequences

**Positive:**
- No partial file states possible
- Rollback available on any failure
- Race condition safe (rename is atomic on POSIX)

**Negative:**
- More I/O operations (2x writes per sync)
- Temporary disk space usage

**Neutral:**
- Standard pattern in file systems

---

## ADR-006: Backward Compatibility for Simple Argument Hints

**Date**: 2025-12-25
**Status**: Accepted
**Deciders**: Technical team

### Context

Existing commands use `argument-hint: <string>` format. Migration options:
1. Force all commands to new schema
2. Support both formats indefinitely
3. Deprecation period then remove old

### Decision

**Support both formats** - detect string vs object and handle appropriately.

### Consequences

**Positive:**
- No breaking changes
- Gradual migration possible
- Third-party commands unaffected

**Negative:**
- Two code paths to maintain
- Slightly more complex parsing

**Neutral:**
- Can deprecate old format in future version
