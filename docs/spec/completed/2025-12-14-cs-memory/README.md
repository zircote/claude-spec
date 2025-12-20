---
project_id: SPEC-2025-12-14-001
project_name: "Git-Native Memory System for claude-spec"
slug: cs-memory
status: completed
created: 2025-12-14T20:14:00Z
approved: 2025-12-14T21:00:00Z
started: 2025-12-14T21:30:00Z
completed: 2025-12-15T07:30:00Z
final_effort: 12 hours
outcome: success
expires: 2026-03-14T20:14:00Z
superseded_by: null
tags: [memory, git-notes, semantic-search, sqlite-vec, embeddings, proactive-recall]
stakeholders: []
worktree:
  branch: plan/git-notes-integration
  base_branch: main
---

# Git-Native Memory System for claude-spec

## Quick Links

- [Requirements](./REQUIREMENTS.md) - User stories and acceptance criteria
- [Architecture](./ARCHITECTURE.md) - System design and components
- [Implementation Plan](./IMPLEMENTATION_PLAN.md) - Phase breakdown and tasks
- [Decisions](./DECISIONS.md) - Architecture Decision Records (16 ADRs)
- [Research Notes](./RESEARCH_NOTES.md) - Technical investigation findings
- [User Guide](../../../plugins/cs/memory/USER_GUIDE.md) - End-user documentation
- [Developer Guide](../../../plugins/cs/memory/DEVELOPER_GUIDE.md) - Integration guide

## Overview

Implement a comprehensive memory system for the claude-spec framework that enables persistent, semantically-searchable context across Claude Code sessions. The system uses Git notes as the canonical storage layer (attached to commits) and SQLite with sqlite-vec for semantic retrieval via vector similarity search.

## Core Principle

> "If a memory has no commit, it had no effect."

Every memory (decision, learning, blocker, progress) must attach to a Git commit, ensuring memories are grounded in concrete project history and distributed with the repository.

## Status

- **Current Phase**: Completed
- **Status**: Success - All features implemented and working
- **Final Effort**: 12 hours (vs 40-80 hours estimated)
- **Code Quality**: 9.0/10 (post-remediation)
- **Test Coverage**: 600 tests passing (84 memory module + 516 existing)
- **ADRs Captured**: 56 from completed spec projects

## Key Features

| Feature | Description |
|---------|-------------|
| **Git Notes Storage** | Memories persist as Git notes attached to commits |
| **Semantic Search** | Natural language queries via SQLite + sqlite-vec |
| **Auto-Capture** | Decisions captured during `/cs:*` workflows |
| **Progressive Hydration** | Summary -> Full -> Files as needed |
| **Team Sharing** | Auto-configured sync via `git push/pull` |
| **Auto-Configuration** | Git notes sync set up on first capture |

## Commands

| Command | Purpose |
|---------|---------|
| `/cs:remember <type> <summary>` | Capture a memory |
| `/cs:recall <query>` | Semantic search |
| `/cs:context [spec]` | Load spec memories |
| `/cs:memory status` | View statistics |
| `/cs:memory reindex` | Rebuild index |

## Memory ID Format

Memory IDs use the format `<namespace>:<short_sha>:<timestamp_ms>`:

```
decisions:abc123d:1702560000000
```

The timestamp component (milliseconds since epoch) ensures uniqueness when multiple memories attach to the same commit (e.g., batch ADR capture during planning).

## Auto-Configuration

On first capture, the system automatically configures Git for notes sync:

- **Push refspec**: `refs/notes/cs/*:refs/notes/cs/*`
- **Fetch refspec**: `refs/notes/cs/*:refs/notes/cs/*`
- **Rewrite ref**: `refs/notes/cs/*` (preserves notes during rebase)
- **Merge strategy**: `cat_sort_uniq` (handles concurrent additions)

No manual configuration required. This is idempotent and safe to run multiple times.

## Specification Summary

| Metric | Count |
|--------|-------|
| User Stories | 19 |
| Functional Requirements | 23 |
| Non-Functional Requirements | 13 |
| Architecture Decision Records | 16 |
| Implementation Tasks | 90+ |
| Estimated Phases | 3 |

## Key Architecture Decisions

| ADR | Decision |
|-----|----------|
| ADR-001 | Git notes for canonical storage |
| ADR-002 | SQLite + sqlite-vec for index |
| ADR-003 | Local embedding (all-MiniLM-L6-v2) |
| ADR-012 | SHA + timestamp IDs for uniqueness |
| ADR-016 | Auto-configuration of git sync |

See [DECISIONS.md](./DECISIONS.md) for full rationale on all 16 ADRs.

## Key Revisions

### v1.3.0 (2025-12-15) - ID Format Update

Based on implementation learnings:

1. **Memory ID Format Changed**: Added timestamp component (`namespace:sha:timestamp_ms`) to support multiple memories per commit (ADR-012 revised)
2. **Auto-Sync Configuration**: Git notes sync auto-configures on first capture (ADR-016 added)
3. **Documentation Updated**: User guide, developer guide, and command docs aligned with implementation

### v1.2.0 (2025-12-14) - Research Review

Based on deep research analysis (10 findings, architect review 7.5/10):

1. **ADR Counter Eliminated**: SHA-based identification replaces monotonic counter (ADR-012 revised)
2. **Concurrency Safety Added**: File locking + `append` instead of `add` (FR-022, FR-023)
3. **Review Note Format Clarified**: JSON array per commit (FR-018)
4. **Error Handling Added**: Section 7 with taxonomy and graceful degradation
5. **History Rewriting Documented**: ADR-015 for orphaned notes handling

### v1.0.0 (2025-12-14) - Initial

Based on requirements elicitation, the following clarifications were incorporated:

1. **Primary Problem Reframed**: Claude's context loss after compaction (not just developer memory)
2. **Proactive Recall Added**: Session awareness + topic-based search (US-015, US-016, ADR-011)
3. **Team Scale Clarified**: ~6 concurrent developers per project
4. **Scope Confirmed**: Single-repo only, supplements CLAUDE.md

## Memory Namespaces

| Namespace | Purpose |
|-----------|---------|
| `inception` | Project ideas and scope |
| `elicitation` | Requirements clarification |
| `research` | Technical investigations |
| `decisions` | Architecture decisions |
| `progress` | Implementation milestones |
| `blockers` | Obstacles and resolutions |
| `learnings` | Technical insights |
| `reviews` | Code review findings |
| `retrospective` | Project retrospectives |
| `patterns` | Cross-project patterns |

## Implementation Statistics

- **56 ADRs captured** from completed spec projects during development
- **10 namespaces** for memory categorization
- **384-dimension** embeddings (all-MiniLM-L6-v2)
- **< 500ms** search latency (NFR target)
- **< 2s** capture latency (NFR target)

## Dependencies

- Python 3.11+
- SQLite 3.x with sqlite-vec extension
- sentence-transformers (for embeddings)
- PyYAML (for note parsing)
