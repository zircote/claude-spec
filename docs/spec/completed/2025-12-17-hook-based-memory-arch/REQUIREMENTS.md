---
document_type: requirements
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T14:00:00Z
status: draft
parent: SPEC-2025-12-14-001
---

# Hooks Based Git-Native Memory Architecture - Requirements

## Executive Summary

This specification extends the cs-memory system (completed in SPEC-2025-12-14-001) with comprehensive hook-based integration. The goal is to transform hooks from passive context loaders into active memory participants that capture learnings automatically and inject relevant context intelligently.

**Core Principle**: "Memory flows both ways - hooks capture and inject."

## Problem Statement

### The Problem

The current hook system loads static context (CLAUDE.md, git state) but does not leverage the cs-memory system. This means:

1. **No automatic learning capture**: Errors, workarounds, and discoveries from tool execution are lost when sessions end
2. **No proactive memory injection**: Relevant past decisions and blockers aren't surfaced when starting work
3. **No trigger phrase detection**: User questions like "why did we..." don't automatically retrieve relevant memories
4. **No memory persistence queue**: Learnings must be explicitly captured via `/cs:remember`

### Impact

- **Context loss**: 60-80% of technical learnings are forgotten across session boundaries
- **Repeated mistakes**: Same errors re-encountered without memory of previous resolutions
- **Manual overhead**: Users must explicitly invoke `/cs:remember` for every learning
- **Cold start problem**: New sessions lack awareness of recent project context

### Current State

| Hook | Current Behavior | Gap |
|------|-----------------|-----|
| SessionStart | Loads CLAUDE.md, git state, project structure | No memory injection |
| UserPromptSubmit | Command detection, prompt logging | No trigger phrase detection |
| PostToolUse | **Not implemented** | No automatic learning capture |
| Stop | Post-steps (archive, cleanup) | No memory queue flush |

## Goals and Success Criteria

### Primary Goal

Enable bidirectional memory flow through hooks: capture learnings automatically during tool use and inject relevant context on session start and trigger phrases.

### Success Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Automatic capture rate | >50% of learnable moments | Compare captured vs. manual captures |
| Session context relevance | >70% useful memories | User feedback on injected context |
| Capture latency | <100ms per capture | Hook execution timing |
| Memory queue reliability | 100% flush on Stop | Verify persistence after session |
| False positive rate | <20% noise captures | Review captured learnings quality |

### Non-Goals (Explicit Exclusions)

- Cross-repository memory aggregation (single repo only)
- Real-time collaboration memory sync
- ML-based learning extraction (heuristic-only for v1)
- User preference learning (focus on technical learnings)

## User Analysis

### Primary Users

- **AI-assisted developers** using Claude Code for coding tasks
- **Architecture planners** using `/cs:p` for specification work
- **Implementers** using `/cs:i` for task tracking

### User Stories

**US-001**: As a developer, I want errors and their resolutions automatically captured so I don't repeat the same debugging steps.

**US-002**: As a developer, I want to see relevant past decisions when starting a new session so I have context without reading docs.

**US-003**: As a developer, I want questions like "why did we choose X" to automatically surface the decision memory.

**US-004**: As a developer, I want workarounds and discoveries captured without explicit `/cs:remember` commands.

**US-005**: As a developer, I want memory capture to not slow down tool execution (non-blocking).

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | PostToolUse hook captures learnable moments | Core capability for automatic learning | Hook fires on Bash/Read/Write/Edit, captures errors with >0.6 score |
| FR-002 | SessionStart injects 5-10 relevant memories | Enable proactive context awareness | Memories appear in session start context output |
| FR-003 | Stop hook flushes memory queue | Ensure no learnings lost | Queue empty after Stop, memories persisted to git notes |
| FR-004 | UserPromptSubmit detects trigger phrases | Enable natural recall | Phrases like "why did we", "remind me" trigger memory injection |
| FR-005 | In-memory queue for non-blocking capture | Prevent tool execution delays | CaptureAccumulator pattern, <100ms capture time |
| FR-006 | hooks.json registration for PostToolUse | Enable hook system | PostToolUse entry with matcher for Bash|Read|Write|Edit|WebFetch |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Noise filtering for routine output | Prevent low-value captures | Routine ls, build output, file listing filtered |
| FR-102 | Content deduplication | Prevent duplicate learnings | Hash-based dedup prevents same learning twice per session |
| FR-103 | Severity classification | Prioritize important learnings | Sev-0/1/2 classification for errors |
| FR-104 | Tool-specific filtering rules | Better signal detection | Different rules for Bash vs Read vs WebFetch |
| FR-105 | Environment variable to disable | User control | CS_TOOL_CAPTURE_ENABLED=false disables |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | Workaround detection | Capture recovery patterns | Detect success-after-failure sequences |
| FR-202 | Memory aging in injection | Surface fresh memories first | Decay scoring applied to injected memories |
| FR-203 | Hydration level selection | Control context size | Allow SUMMARY vs FULL injection |
| FR-204 | Capture summary at session end | User feedback on captures | Display count and types of captured learnings |

## Non-Functional Requirements

### Performance

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | PostToolUse hook execution time | <100ms (never block tool) |
| NFR-002 | SessionStart memory query | <500ms for 10 memories |
| NFR-003 | Memory queue flush time | <2s for 20 queued memories |
| NFR-004 | Trigger phrase detection | <50ms pattern matching |

### Security

| ID | Requirement |
|----|-------------|
| NFR-005 | Captured content filtered through existing secret detection pipeline |
| NFR-006 | No sensitive data in error captures (redact file paths with secrets) |
| NFR-007 | Memory injection respects existing access controls |

### Reliability

| ID | Requirement |
|----|-------------|
| NFR-008 | Fail-open design: hook failures never block user interaction |
| NFR-009 | Queue persisted to file before Stop hook for crash recovery |
| NFR-010 | Graceful degradation if embedding service unavailable |

### Maintainability

| ID | Requirement |
|----|-------------|
| NFR-011 | Reuse existing CaptureService, RecallService APIs |
| NFR-012 | Follow existing hook patterns (hook_io, step_runner) |
| NFR-013 | Test coverage >80% for new code |

## Technical Constraints

### Existing Architecture Compliance

- **hooks.json format**: Must follow existing structure with nested hooks arrays
- **Input/output contract**: JSON stdin/stdout, exit code 0 for success
- **Module whitelist**: New steps must be added to STEP_MODULES in step_runner.py
- **Concurrency**: Use fcntl.flock for file operations per existing patterns

### Integration Points

| Component | Integration |
|-----------|-------------|
| CaptureService | Use existing capture methods (capture_learning, capture_blocker) |
| RecallService | Use search() for trigger phrase matches, context() for spec loading |
| CaptureAccumulator | Use for in-memory queue (already mutable dataclass) |
| filter_pipeline | Run captured content through secret detection |
| IndexService | Use batch operations (get_batch, not repeated get) |

## Dependencies

### Internal Dependencies

- cs-memory module (SPEC-2025-12-14-001) - completed
- hooks infrastructure (session_start.py, command_detector.py, etc.) - existing
- filters pipeline (pipeline.py, log_writer.py) - existing

### External Dependencies

- None new (uses existing sentence-transformers, sqlite-vec)

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Too many false positive captures | Medium | Low | Start conservative (error-only), tune threshold |
| Hook timeout blocking tools | Low | High | Hard 5s timeout, fail-open design |
| Queue loss on crash | Medium | Medium | Persist queue to file, not just memory |
| Context injection too large | Low | Medium | Limit to 5-10 memories, SUMMARY level |
| Embedding service slow on first call | High | Low | Lazy loading already implemented |

## Open Questions

- [x] Memory queue strategy → In-memory with Stop flush (user decision)
- [x] SessionStart context limit → 5-10 memories (user decision)
- [x] Scope → All 4 hook enhancements (user decision)
- [ ] Should PostToolUse capture Read/Write success cases? (likely no - noise)
- [ ] Persist queue to file or pure in-memory? (recommend file for reliability)

## Appendix

### Trigger Phrases for Memory Detection

```python
MEMORY_TRIGGER_PATTERNS = [
    r"why did we",
    r"what was the decision",
    r"remind me",
    r"continue (from|where)",
    r"last time",
    r"previous(ly)?",
    r"earlier",
    r"the plan",
    r"the blocker",
    r"what happened with",
]
```

### Learnable Moment Signals

```python
LEARNABLE_SIGNALS = {
    "error_exit": lambda r: r.get("exit_code", 0) != 0,
    "error_keywords": r"(error|failed|exception|fatal|permission denied|not found|timeout)",
    "workaround_keywords": r"(instead|alternatively|workaround|fallback|fixed by|resolved with)",
    "discovery_keywords": r"(found|discovered|learned|realized|turns out|note:|important:)",
}
```

### References

- [SPEC-2025-12-14-001] Git-Native Memory System (completed)
- [prompt.md] Original execution prompt
- [plan.md] Detailed implementation plan
- Research: GitHub Copilot, Cursor AI memory patterns
