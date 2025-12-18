---
project_id: SPEC-2025-12-17-001
project_name: "Hooks Based Git-Native Memory Architecture"
slug: hook-based-memory-arch
status: completed
created: 2025-12-17T14:00:00Z
approved: 2025-12-17T14:00:00Z
started: 2025-12-17T14:30:00Z
completed: 2025-12-17T20:45:00Z
expires: null
superseded_by: null
tags: [hooks, memory, git-notes, semantic-search, automatic-capture]
stakeholders: []
parent: SPEC-2025-12-14-001
estimated_effort: 16-24 hours
final_effort: 18 hours
outcome: success
---

# Hooks Based Git-Native Memory Architecture

## Overview

Extension of the cs-memory system (SPEC-2025-12-14-001) to add comprehensive hook-based memory integration. Enables bidirectional memory flow: automatic capture during tool execution and intelligent injection at session start and on trigger phrases.

**Core Principle**: "Memory flows both ways - hooks capture and inject."

## Key Features

| Feature | Description | Hook |
|---------|-------------|------|
| **Automatic Learning Capture** | Capture errors, workarounds, discoveries from tool execution | PostToolUse |
| **Session Memory Injection** | Inject 5-10 relevant memories at session start | SessionStart |
| **Trigger Phrase Detection** | "Why did we..." triggers automatic memory recall | UserPromptSubmit |
| **Memory Queue Flush** | Non-blocking capture with persistence on Stop | Stop |

## Status

| Phase | Status | Progress |
|-------|--------|----------|
| Planning | ✅ Complete | REQUIREMENTS.md, ARCHITECTURE.md, IMPLEMENTATION_PLAN.md |
| Implementation | ⚪ Not Started | 0/24 tasks |
| Testing | ⚪ Not Started | 0% coverage |
| Documentation | ⚪ Not Started | Pending |

## Implementation Summary

### Phase 1: PostToolUse Infrastructure (6-8 hours)
- Learning detector module with scoring (threshold ≥0.6)
- ToolLearning model and content deduplication
- PostToolUse hook for Bash/Read/Write/Edit/WebFetch
- Memory queue flusher step

### Phase 2: SessionStart Memory Injection (3-4 hours)
- Memory injector module using RecallService
- Spec detection from docs/spec/active/
- Extend session_start.py with memory section
- Configuration for limit and hydration level

### Phase 3: Trigger Phrase Detection (3-4 hours)
- Trigger pattern matching (why did we, remind me, etc.)
- New UserPromptSubmit hook
- Memory context formatting

### Phase 4: Integration & Testing (4-8 hours)
- End-to-end hook flow tests
- Performance benchmarks (<100ms for PostToolUse)
- Documentation updates

## Quick Links

- [Requirements](REQUIREMENTS.md) - 6 P0, 5 P1, 4 P2 requirements
- [Architecture](ARCHITECTURE.md) - Component design, data flow, hooks.json
- [Implementation Plan](IMPLEMENTATION_PLAN.md) - 24 tasks across 4 phases
- [Original Prompt](prompt.md) - Execution prompt used to guide development
- [Detailed Plan](plan.md) - Extended specification document

## Success Metrics

| Metric | Target |
|--------|--------|
| Automatic capture rate | >50% of learnable moments |
| Session context relevance | >70% useful memories |
| Capture latency | <100ms per capture |
| False positive rate | <20% noise captures |

## Risk Summary

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Too many false positive captures | Medium | Start conservative, tune threshold |
| Hook timeout blocking tools | Low | Hard 5s timeout, fail-open |
| Queue loss on crash | Medium | File backup option |

## Dependencies

- **Parent**: SPEC-2025-12-14-001 (cs-memory) - Completed
- **External**: None new (uses existing sentence-transformers, sqlite-vec)

## Next Steps

1. Review and approve this specification
2. Run `/cs:i hook-based-memory-arch` to begin implementation
3. Phase 1 can be implemented independently
