---
document_type: requirements
project_id: SPEC-2025-12-15-001
version: 1.0.0
last_updated: 2025-12-15T19:45:00Z
status: draft
---

# Memory Auto-Capture Implementation - Requirements

## Executive Summary

Implement automatic memory capture during `/cs:*` command execution to eliminate the gap between documented memory integration (extensive pseudo-code in command files) and actual implementation (manual-only via `/cs:remember`). This includes adding missing capture methods, wiring up unused configuration, and ensuring documentation accuracy.

## Problem Statement

### The Problem

The cs-memory system has a significant documentation-vs-implementation gap:
- 10 namespaces defined, only 5 have capture methods
- `AUTO_CAPTURE_NAMESPACES` constant defined but never used
- Command files contain hundreds of lines of memory integration pseudo-code that doesn't execute
- All 56 existing memories are `decisions` type (manually captured)

### Impact

- Users expect auto-capture based on documentation but must manually capture everything
- Valuable context (elicitation, research, retrospectives) is lost
- Memory system appears incomplete/broken despite functional core

### Current State

| Aspect | Documented | Implemented |
|--------|------------|-------------|
| Auto-capture | Extensive pseudo-code | None |
| Namespaces | 10 | 10 (defined only) |
| Capture methods | 10 implied | 5 exist |
| Hook integration | Mentioned | None |

## Goals and Success Criteria

### Primary Goal

Enable automatic memory capture at key points in `/cs:p`, `/cs:i`, `/cs:c`, and `/cs:review` commands.

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Namespace coverage | 10/10 have capture methods | Code inspection |
| Auto-capture points | 12+ per spec lifecycle | Count trigger points |
| Memory diversity | 5+ namespace types populated | `/cs:recall all memories` |
| Zero manual intervention | Capture without user confirmation | UX observation |

### Non-Goals

- Real-time streaming of captures (batch at phase end)
- Complex ML-based "significance" detection
- Breaking changes to existing `/cs:remember` command
- Modifying already-captured memories

## User Analysis

### Primary Users

- **Developers using cs-spec**: Run `/cs:p`, `/cs:i`, `/cs:c` commands
- **Context**: Planning, implementing, and closing spec projects
- **Need**: Automatic preservation of decisions, learnings, and context

### User Stories

1. As a developer running `/cs:p`, I want elicitation clarifications captured automatically so I can recall them during implementation
2. As a developer running `/cs:i`, I want progress and blockers captured so retrospectives have accurate data
3. As a developer running `/cs:c`, I want patterns and learnings extracted so future specs benefit
4. As a developer running `/cs:review`, I want findings persisted so I can track recurring issues

## Functional Requirements

### Must Have (P0)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-001 | Add `capture_review()` method | reviews namespace has no capture method | Method exists, accepts severity/category/file/line |
| FR-002 | Add `capture_retrospective()` method | retrospective namespace has no capture method | Method exists, accepts outcome/metrics/learnings |
| FR-003 | Add `capture_pattern()` method | patterns namespace has no capture method | Method exists, accepts pattern/applicability/examples |
| FR-004 | Wire `AUTO_CAPTURE_NAMESPACES` for validation | Currently dead code | Config used in capture validation |
| FR-005 | Auto-capture in `/cs:p` at phase transitions | Phase summaries should persist | inception/elicitation/research/decisions captured |
| FR-006 | Auto-capture in `/cs:i` for progress events | Track implementation progress | progress/blockers/learnings captured |
| FR-007 | Auto-capture in `/cs:c` at close-out | Preserve retrospective context | retrospective/patterns captured |
| FR-008 | Auto-capture in `/cs:review` for findings | Persist review findings | reviews captured per finding |
| FR-009 | Silent capture with end-of-phase summary | No interruption, visibility at end | Summary displayed, no AskUserQuestion |

### Should Have (P1)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-101 | Hook-based capture for session events | Automatic without command changes | SessionStart/Stop hooks trigger capture |
| FR-102 | Capture count in command output | User visibility | "Captured: 3 memories (1 decision, 2 learnings)" |
| FR-103 | Graceful degradation on capture failure | Don't break commands | Capture errors logged, command continues |

### Nice to Have (P2)

| ID | Requirement | Rationale | Acceptance Criteria |
|----|-------------|-----------|---------------------|
| FR-201 | Batch capture optimization | Performance | Multiple captures in single git operation |
| FR-202 | Capture preview in verbose mode | Debugging | `--verbose` shows what will be captured |

## Non-Functional Requirements

### Performance

- Capture operations < 500ms each
- Batch captures < 2s for up to 10 memories
- No blocking of command execution

### Reliability

- Capture failures must not abort commands
- Partial captures recoverable via `/cs:memory reindex`

### Maintainability

- Capture methods follow existing patterns in `capture.py`
- Hook integration follows existing patterns in `hooks/`

## Technical Constraints

- Must use existing git notes storage mechanism
- Must integrate with existing embedding/indexing pipeline
- Python 3.11+ compatibility required
- No new external dependencies

## Dependencies

### Internal

- `memory/capture.py` - Add new methods
- `memory/config.py` - Wire AUTO_CAPTURE_NAMESPACES
- `hooks/*.py` - Add capture triggers
- `commands/*.md` - Update documentation

### External

- None (uses existing git, sqlite-vec infrastructure)

## Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Capture volume overwhelms index | Low | Medium | Batch captures, compression |
| Hook failures break commands | Medium | High | Fail-open design, try/except |
| Duplicate captures | Medium | Low | Idempotent capture with ID checking |
| Performance degradation | Low | Medium | Async capture option |

## Open Questions

- [x] Trigger mechanism → Both hooks and command integration
- [x] Capture granularity → Phase summaries
- [x] Dead code handling → Keep and wire up
- [x] Specialized methods → Yes, with structured fields
- [x] Commands to integrate → All four (/cs:p, /cs:i, /cs:c, /cs:review)
- [x] Confirmation required → No, silent with summary

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Auto-capture | Memory creation without explicit `/cs:remember` invocation |
| Phase summary | Single memory capturing an entire elicitation/research phase |
| Hook-based capture | Triggered by Claude Code hook events |
| Command-integrated capture | Triggered by command execution logic |

### References

- Investigation findings from parallel agent exploration
- Existing `memory/capture.py` implementation
- `memory/config.py` namespace definitions
