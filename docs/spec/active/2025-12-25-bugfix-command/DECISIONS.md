# Architecture Decision Records

## ADR-001: Investigation-First Approach

**Status**: Accepted

**Context**: Original issue #27 proposed a `/bugfix` command that would fix bugs and create PRs. User redirected to issue reporting only.

**Decision**: Create `/report-issue` that investigates before filing, producing AI-actionable issues.

**Rationale**:
- Investigation provides rich context for faster resolution
- AI tools (Claude, Copilot) can immediately work on well-documented issues
- Lower risk than auto-fixing code
- Simpler implementation

**Consequences**:
- Issues require 30-60 seconds of investigation time
- Output quality depends on investigation depth
- No automatic fixes - requires separate resolution

---

## ADR-002: Moderate Investigation Depth

**Status**: Accepted

**Context**: Investigation could be quick (5-10s), moderate (30-60s), or deep (2-5min with agents).

**Decision**: Moderate depth - find error source, callers, related tests, brief analysis.

**Rationale**:
- Quick enough to not frustrate users
- Deep enough to provide actionable context
- Avoids over-engineering with agent orchestration

**Consequences**:
- Some complex issues may need manual investigation
- 30-60 second wait acceptable for most users

---

## ADR-003: Detect Any Unexpected Behavior

**Status**: Accepted

**Context**: Could trigger report offer only on exceptions, or on any unexpected behavior.

**Decision**: Trigger on any unexpected behavior including exceptions, failures, unexpected patterns, empty results.

**Rationale**:
- Many bugs manifest as silent failures, not exceptions
- Catches more issues that would otherwise go unreported
- User can always decline

**Consequences**:
- May trigger more frequently
- Requires good opt-out mechanism (see ADR-004)

---

## ADR-004: Low-Friction Opt-Out

**Status**: Accepted

**Context**: Proactive prompts can become annoying if too frequent.

**Decision**: Provide session and permanent opt-out options in the same prompt.

**Options**:
- "Yes, report it"
- "No, continue"
- "Don't ask again (this session)"
- "Never ask"

**Rationale**:
- Respects user preference immediately
- Single question, not a dialog
- No guilt-tripping on decline
- Permanent opt-out for users who don't want the feature

**Consequences**:
- Some users will opt out permanently
- Feature adoption is voluntary

---

## ADR-005: Repository Detection from Error Context

**Status**: Accepted

**Context**: Need to determine which repository to file the issue in.

**Decision**: Parse error traces to detect source repository, then confirm with user.

**Rationale**:
- Error traces often contain plugin paths that reveal the source
- Auto-detection reduces user effort
- Confirmation prevents filing in wrong repo

**Consequences**:
- Detection may fail for some error types
- Always falls back to asking user

---

## ADR-006: No Code Modification

**Status**: Accepted

**Context**: Original issue proposed auto-fixing bugs.

**Decision**: Command only reads code for investigation, never modifies.

**Rationale**:
- Lower risk
- Simpler implementation
- Users may not trust auto-fixes
- Issue filing is valuable on its own

**Consequences**:
- Fixes require separate action (manual or via another tool)
- Issues contain enough context for AI-assisted resolution
