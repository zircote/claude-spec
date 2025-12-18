---
document_type: decisions
project_id: SPEC-2025-12-17-001
version: 1.0.0
last_updated: 2025-12-17T17:30:00Z
status: final
---

# Hooks Based Git-Native Memory Architecture - Decision Log

This document records key architectural and implementation decisions made during the development of the hook-based memory system.

---

## Decision 1: In-Memory Queue vs File-Based Queue

**Date:** 2025-12-17

**Context:**
PostToolUse captures need to be non-blocking (<50ms) but also reliably persisted. We considered two approaches:
1. File-based queue: Write to `.cs-capture-queue.json` immediately
2. In-memory queue: Use CaptureAccumulator, flush on Stop hook

**Decision:** Use in-memory queue with Stop hook flush

**Rationale:**
- File I/O adds 10-20ms latency per operation
- In-memory append is <1ms
- Stop hook provides reliable flush point
- Memory footprint is minimal (50 captures × ~1KB = ~50KB)
- Simpler implementation, fewer failure modes

**Trade-offs:**
- (-) Captures lost if Claude Code crashes before Stop
- (+) Faster per-capture performance
- (+) Batched writes more efficient for git operations

**Alternatives Considered:**
- Write-through cache: Too slow for target latency
- Background thread flush: Added complexity, Python GIL concerns

---

## Decision 2: Capture Threshold of 0.6

**Date:** 2025-12-17

**Context:**
Need to balance capturing valuable learnings vs. noise. Too low = spam, too high = missing useful signals.

**Decision:** Set default threshold at 0.6 (score range 0.0-1.0)

**Rationale:**
Based on analysis of common tool outputs:
- Exit code 1 + "error" keyword: ~0.7 score (captured)
- Exit code 0 + "warning": ~0.5 score (not captured)
- Exit code 0 + success message: ~0.2 score (not captured)
- Exit code 1 + generic failure: ~0.6 score (captured)

Threshold of 0.6 captures errors and significant warnings while filtering routine output.

**Trade-offs:**
- (-) May miss some useful warnings (score 0.5-0.6)
- (+) Keeps capture rate manageable (~10-20% of tool executions)
- (+) High signal-to-noise ratio in captured learnings

**Future Consideration:**
- Make threshold configurable via environment variable or config file
- Collect telemetry on capture rates to tune threshold

---

## Decision 3: 16 Trigger Phrase Patterns

**Date:** 2025-12-17

**Context:**
Need to detect when users want to recall past context without being overly sensitive to false positives.

**Decision:** Use 16 regex patterns covering common memory-related phrases

**Patterns Selected:**
1. `why did we` - Decision recall
2. `what was the decision` - Decision recall
3. `remind me` - General recall
4. `continue (from|where)` - Session continuity
5. `last time` - Temporal recall
6. `previous(ly)?` - Temporal recall
7. `the blocker` - Blocker recall
8. `what happened with` - Event recall
9. `what was the issue` - Problem recall
10. `where were we` - Progress recall
11. `pick up where` - Session continuity
12. `what did we learn` - Learning recall
13. `what went wrong` - Error recall
14. `what was blocking` - Blocker recall
15. `recall the` - Explicit recall
16. `continue where` - Session continuity

**Rationale:**
- Patterns are intuitive and natural language
- Case-insensitive for flexibility
- Word boundaries prevent false matches
- Cover the main use cases for memory retrieval

**Trade-offs:**
- (-) May miss creative phrasings
- (+) Low false positive rate (~0% in testing)
- (+) Fast pattern matching (<1ms)

---

## Decision 4: Memory Injection Limit of 10

**Date:** 2025-12-17

**Context:**
Need to inject relevant context without overwhelming Claude's context window or creating token bloat.

**Decision:** Default to 10 memories maximum, configurable via lifecycle config

**Rationale:**
- 10 memories × ~200 tokens each = ~2000 tokens
- Well under context limits while providing meaningful context
- Configurable for users who want more or fewer

**Trade-offs:**
- (-) May miss relevant memories if more than 10 exist
- (+) Keeps injection concise and focused
- (+) Respects token budget concerns

**Configuration:**
```json
{
  "lifecycle": {
    "sessionStart": {
      "memoryInjection": {
        "limit": 10
      }
    }
  }
}
```

---

## Decision 5: Graceful Degradation Pattern

**Date:** 2025-12-17

**Context:**
Hooks must never block user interaction, even if components fail.

**Decision:** All hooks use try/except with fallback to approval

**Implementation Pattern:**
```python
try:
    # Hook logic
    result = process_input(...)
except Exception as e:
    sys.stderr.write(f"Hook error: {e}\n")
    # Fall through to default

# Always approve - never block
output = {"decision": "approve"}
if result:
    output["additionalContext"] = result
write_output(output)
```

**Rationale:**
- User experience must not degrade due to hook failures
- Errors logged to stderr for debugging
- System remains functional even with partial failures

**Trade-offs:**
- (-) Errors may go unnoticed in production
- (+) System never blocks user
- (+) Partial functionality better than total failure

---

## Decision 6: Hook Ordering in UserPromptSubmit

**Date:** 2025-12-17

**Context:**
Three UserPromptSubmit hooks need to run in a specific order to avoid conflicts.

**Decision:** Order: command_detector → prompt_capture → trigger_memory

**Rationale:**
1. `command_detector` must run first to set session state
2. `prompt_capture` should capture before any modifications
3. `trigger_memory` runs last to avoid interfering with command detection

**Implementation:**
Hooks run in order listed in `hooks.json` array.

---

## Decision 7: Secret Filtering via filter_pipeline

**Date:** 2025-12-17

**Context:**
Captured tool output may contain secrets that should not be persisted.

**Decision:** Reuse existing `filter_pipeline` from prompt capture system

**Rationale:**
- Already handles 20+ secret patterns
- Pre-compiled regexes for performance
- Includes base64 decoding for encoded secrets
- Consistent filtering across all capture paths

**Secret Types Filtered:**
- AWS keys (AKIA*, ASIA*)
- GitHub tokens (ghp_*, gho_*, ghu_*, ghs_*)
- OpenAI/Anthropic keys
- Database connection strings
- Private keys, JWTs, passwords

---

## Decision 8: Namespace Icons for Memory Display

**Date:** 2025-12-17

**Context:**
Injected memories need visual distinction by type.

**Decision:** Use emoji icons per namespace

| Namespace | Icon | Rationale |
|-----------|------|-----------|
| decisions | 🎯 | Target = intentional choice |
| learnings | 💡 | Lightbulb = insight |
| blockers | 🚧 | Construction = obstacle |
| progress | 📈 | Chart = advancement |
| patterns | 🔄 | Cycle = recurring |
| reviews | 📋 | Clipboard = review |
| retrospective | 🔍 | Search = reflection |

**Rationale:**
- Visual scanning is faster than reading labels
- Icons are universally recognizable
- Consistent across session start and trigger injection

---

## Decision 9: Performance Targets

**Date:** 2025-12-17

**Context:**
Hooks must be fast enough to not impact user experience.

**Decision:** Set explicit performance targets

| Component | Target | Actual |
|-----------|--------|--------|
| LearningDetector | <5ms | <0.01ms |
| SessionDeduplicator | <1ms | <0.001ms |
| TriggerDetector | <1ms | <0.001ms |
| MemoryInjector format | <10ms | <0.02ms |
| FilterPipeline | <5ms | <0.05ms |
| PostToolUse hook | <50ms | <10ms |
| SessionStart hook | <500ms | <100ms |
| TriggerMemory hook | <200ms | <50ms |

**Rationale:**
- Sub-100ms operations are imperceptible to users
- Leaves headroom for RecallService queries (if enabled)
- Benchmarks verify targets are met

---

## Decision 10: Frozen Dataclasses for Models

**Date:** 2025-12-17

**Context:**
ToolLearning and related models need to be immutable for thread safety.

**Decision:** Use `@dataclass(frozen=True)` for all model classes

**Implementation:**
```python
@dataclass(frozen=True)
class ToolLearning:
    tool_name: str
    category: str
    severity: str
    # ... other fields
```

**Rationale:**
- Prevents accidental mutation
- Safe to pass across boundaries
- Enables hashing for deduplication
- Aligns with existing cs-memory patterns

---

## Summary

| # | Decision | Impact |
|---|----------|--------|
| 1 | In-memory queue | Performance, simplicity |
| 2 | Threshold 0.6 | Signal quality |
| 3 | 16 trigger patterns | Recall coverage |
| 4 | Limit 10 memories | Token efficiency |
| 5 | Graceful degradation | Reliability |
| 6 | Hook ordering | Correctness |
| 7 | filter_pipeline reuse | Security |
| 8 | Namespace icons | UX |
| 9 | Performance targets | Quality |
| 10 | Frozen dataclasses | Safety |

All decisions are documented with rationale and trade-offs for future reference.
